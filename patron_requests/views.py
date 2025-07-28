from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from notifications.signals import notify

from accounts.models import CustomUser
from listings.models import LoRA, Model
from patron_requests.forms import BorrowLoRAForm
from patron_requests.models import BorrowRequest

from .forms import BorrowLoRAForm
from .models import BorrowedLoRA, BorrowRequest, ModelAccessRequest


@login_required
def request_model_access(request, pk):
    # TODO: Implement a more robust request system. Should notify the librarians about the request in some way and allow them
    # to approve or deny the request.
    """Request access to a private model."""
    # Ensure the model exists.
    model = get_object_or_404(Model, pk=pk)
    # If the model is public or user already has access, redirect.
    if (
        not model.is_private
        or request.user == model.creator
        or request.user in model.allowed_users.all()
    ):
        messages.info(request, "You already have access to this model.")
        return redirect("model_detail", pk=model.pk)

    if request.method == "POST":
        # Check if the user has already requested access.
        if ModelAccessRequest.objects.filter(
            model=model, patron=request.user, archived=False
        ).exists():
            messages.info(request, "You have already requested access to this model.")
            return redirect("model_list")
        # Check if the user is a librarian.
        if request.user.role.strip().lower() == "librarian":
            messages.info(request, "Librarians cannot request access to models.")
            return redirect("model_list")
        # create new model_access_request

        access_request = ModelAccessRequest.objects.create(
            model=model, patron=request.user
        )
        access_request.save()
        messages.success(
            request, f'Your request for access to model "{model.title}" has been sent.'
        )
        send_mail(
            "New Model Access Request",
            f"User {request.user.username} has requested access to model '{model.title}'. Please review the request.",
            settings.DEFAULT_FROM_EMAIL,
            [model.creator.email],
            fail_silently=False,  # set to False to display errors
        )
        # Send an in-app notification to the librarian
        notify.send(
            request.user,
            recipient=model.creator,
            verb="has requested access to",
            target=model,
            description=f"User {request.user.username} requested access to model '{model.title}'.",
        )
        return redirect("model_list")

    return render(request, "request_model_access.html", {"model": model})


@login_required
def view_active_model_requests(request):
    # Only librarians can view active model access requests.
    if request.user.role.strip().lower() != "librarian":
        return HttpResponseForbidden("You do not have permission to view this page.")

    active_model_requests = ModelAccessRequest.objects.filter(
        approved=False, archived=False
    )

    context = {
        "active_model_requests": active_model_requests,
    }
    return render(request, "active_model_requests.html", context)


"""


@login_required
def view_active_borrow_requests(request):
    # Only librarians can view active borrowing requests.
    if request.user.role.strip().lower() != "librarian":
        return HttpResponseForbidden("You do not have permission to view this page.")
    
    # Assuming you have a BorrowRequest model in a borrowing app
    try:
        from borrowing.models import BorrowRequest
from django.core.mail import send_mail
        active_borrow_requests = BorrowRequest.objects.filter(status="pending")
    except ImportError:
        active_borrow_requests = []  # Placeholder if the BorrowRequest model is not available.
    
    context = {
        "active_borrow_requests": active_borrow_requests,
    }
    return render(request, "librarian_requests/active_borrow_requests.html", context)'
"""


@login_required
def approve_model_request(request, request_id):
    # Only librarians can approve requests.
    if request.user.role.strip().lower() != "librarian":
        return HttpResponseForbidden(
            "You do not have permission to perform this action."
        )

    access_request = get_object_or_404(ModelAccessRequest, id=request_id)
    # Mark the request as approved.
    access_request.approved = True
    access_request.archived = True
    access_request.save()
    # Add the patron to the model's allowed_users.
    access_request.model.allowed_users.add(access_request.patron)
    messages.success(
        request,
        f"Access for {access_request.patron.username} to '{access_request.model.title}' approved.",
    )
    # Send an email to the patron informing them of the approval.
    send_mail(
        "Access Request Approved",
        f"Your request for access to model '{access_request.model.title}' has been approved.",
        settings.DEFAULT_FROM_EMAIL,
        [access_request.patron.email],
        fail_silently=False,  # set to False to display errors
    )
    # Send an in-app notification to the patron.
    notify.send(
        request.user,
        recipient=access_request.patron,
        verb="has approved your access to",
        target=access_request.model,
        description=f"Your access request for model '{access_request.model.title}' was approved.",
    )

    return redirect("view_active_model_requests")


@login_required
def deny_model_request(request, request_id):
    # Only librarians can deny requests.
    if request.user.role.strip().lower() != "librarian":
        return HttpResponseForbidden(
            "You do not have permission to perform this action."
        )

    access_request = get_object_or_404(ModelAccessRequest, id=request_id)
    messages.info(
        request,
        f"Access for {access_request.patron.username} to '{access_request.model.title}' denied.",
    )

    access_request.archived = True
    access_request.save()
    return redirect("view_active_model_requests")


@login_required
def borrow_lora_page(request, pk):
    lora = get_object_or_404(LoRA, pk=pk)
    if lora.status != LoRA.CHECKED_IN:
        messages.error(request, "This LoRA is not available for borrowing.")
        return redirect("listing_detail", pk=lora.pk)

    if request.method == "POST":
        form = BorrowLoRAForm(request.POST)
        if form.is_valid():
            due_date = form.cleaned_data["due_date"]
            now = timezone.now()
            if due_date <= now:
                form.add_error("due_date", "Due date must be in the future.")
                return render(
                    request, "borrow_lora_page.html", {"form": form, "lora": lora}
                )
            # Compute an exact duration as a timedelta
            duration = due_date - now

            # Check if a pending borrow request already exists for this lora and user.
            pending_request = BorrowRequest.objects.filter(
                lora=lora, patron=request.user, status=BorrowRequest.PENDING
            ).first()

            if pending_request:
                pending_request.duration = (
                    duration  # Update with new duration (timedelta)
                )
                pending_request.save()
                messages.success(
                    request, "Your existing borrow request has been updated."
                )
            else:
                BorrowRequest.objects.create(
                    lora=lora,
                    patron=request.user,
                    duration=duration,
                    status=BorrowRequest.PENDING,
                )
                messages.success(
                    request,
                    "Your borrow request has been sent to the librarian for approval.",
                )

            
            return redirect("listing_detail", pk=lora.pk)
        else:
            return render(
                request, "borrow_lora_page.html", {"form": form, "lora": lora}
            )
    else:
        form = BorrowLoRAForm()

    context = {"form": form, "lora": lora}
    return render(request, "borrow_lora_page.html", context)


@login_required
def view_active_borrow_requests(request):
    # Only librarians can view active borrow requests.
    if request.user.role.strip().lower() != "librarian":
        return HttpResponseForbidden("You do not have permission to view this page.")

    active_borrow_requests = BorrowRequest.objects.filter(
        status=BorrowRequest.PENDING
    ).order_by("created_at")
    context = {
        "active_borrow_requests": active_borrow_requests,
    }
    return render(request, "active_borrow_requests.html", context)


@login_required
def approve_borrow_request(request, request_id):
    borrow_request = get_object_or_404(BorrowRequest, id=request_id)
    # Now allow any librarian to approve
    if request.user.role.strip().lower() != "librarian":
        return HttpResponseForbidden("Only librarians can approve borrow requests.")
    borrow_request.status = BorrowRequest.APPROVED
    borrow_request.save()

    lora = borrow_request.lora
    lora.status = LoRA.IN_CIRCULATION
    lora.save()

    # Create a BorrowedLoRA record (if one doesn't already exist)
    try:
        from patron_requests.models import BorrowedLoRA
    except ImportError:
        BorrowedLoRA = None

    if BorrowedLoRA is not None and not hasattr(borrow_request, "borrowed_lora"):
        BorrowedLoRA.objects.create(
            borrow_request=borrow_request,
            lora=lora,
            patron=borrow_request.patron,
            duration=borrow_request.duration,  # This is now a timedelta
        )

    messages.success(request, f"Borrow request for '{lora.title}' approved.")

    send_mail(
        "Borrow Request Approved",
        f"Your request to borrow '{lora.title}' for {borrow_request.duration} has been approved.",
        settings.DEFAULT_FROM_EMAIL,
        [borrow_request.patron.email],
        fail_silently=False,
    )

    notify.send(
        request.user,
        recipient=borrow_request.patron,
        verb="approved your borrow request for",
        target=lora,
        description=f"Your request to borrow '{lora.title}' for {borrow_request.duration} was approved.",
    )

    return redirect("view_active_borrow_requests")


@login_required
def deny_borrow_request(request, request_id):
    borrow_request = get_object_or_404(BorrowRequest, id=request_id)
    # Now allow any librarian to deny
    if request.user.role.strip().lower() != "librarian":
        return HttpResponseForbidden("Only librarians can deny borrow requests.")
    borrow_request.status = BorrowRequest.DENIED
    borrow_request.save()

    messages.info(request, f"Borrow request for '{borrow_request.lora.title}' denied.")

    # Notify the patron via email.
    send_mail(
        "Borrow Request Denied",
        f"Your request to borrow '{borrow_request.lora.title}' has been denied.",
        settings.DEFAULT_FROM_EMAIL,
        [borrow_request.patron.email],
        fail_silently=False,
    )
    # Send an in-app notification.
    notify.send(
        request.user,
        recipient=borrow_request.patron,
        verb="denied your borrow request for",
        target=borrow_request.lora,
        description=f"Your request to borrow '{borrow_request.lora.title}' was denied.",
    )

    return redirect("view_active_borrow_requests")


@login_required
def view_active_borrowed_loras(request):
    borrowed_loras = BorrowedLoRA.objects.filter(returned_at__isnull=True)
    context = {
        "borrowed_loras": borrowed_loras,
    }
    return render(request, "active_borrowed_loras.html", context)


@login_required
def view_borrowed_loras(request):
    # Librarians see all borrowed loras; patrons see only their borrowed loras.
    if request.user.role.strip().lower() == "librarian":
        borrowed_loras = BorrowedLoRA.objects.all().order_by("-start_date")
    else:
        borrowed_loras = BorrowedLoRA.objects.filter(patron=request.user).order_by(
            "-start_date"
        )
    # Only get borrowed loras that haven't been marked as returned
    borrowed_loras = BorrowedLoRA.objects.filter(returned_at__isnull=True)
    context = {"borrowed_loras": borrowed_loras}
    return render(request, "borrowed_loras_page.html", context)


@login_required
def return_borrowed_lora(request, pk):
    borrowed_lora = get_object_or_404(BorrowedLoRA, pk=pk)

    # Only allow the patron who borrowed, or a librarian.
    if (
        request.user != borrowed_lora.patron
        and request.user.role.strip().lower() != "librarian"
    ):
        messages.error(request, "You do not have permission to return this LoRA.")
        return redirect("view_active_borrowed_loras")

    # Check if the lora is already returned.
    if borrowed_lora.returned_at is not None:
        messages.info(request, "This LoRA has already been returned.")
        return redirect("view_active_borrowed_loras")

    # Mark the lora as returned (since returned_at is currently None)
    borrowed_lora.returned_at = timezone.now()
    borrowed_lora.save()

    # Optionally update the associated lora's status and send a notification
    lora = borrowed_lora.lora
    lora.status = LoRA.CHECKED_IN  # Adjust if your model differs.
    lora.save()

    send_mail(
        "LoRA Returned",
        f"Your borrowed LoRA '{lora.title}' has been returned successfully and is now available.",
        settings.DEFAULT_FROM_EMAIL,
        [borrowed_lora.patron.email],
        fail_silently=False,
    )

    messages.success(request, f"'{lora.title}' has been returned successfully.")
    return redirect("view_active_borrowed_loras")


@login_required
def promote_patron(request):
    if request.user.role.lower() != "librarian":
        messages.error(request, "You are not authorized to perform this action.")
        return redirect("home")

    search_query = request.GET.get("q", "")
    patrons = []
    if search_query:
        patrons = CustomUser.objects.filter(
            Q(username__icontains=search_query) | Q(email__icontains=search_query),
            role__iexact="patron",
        )

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        patron = get_object_or_404(CustomUser, pk=user_id, role__iexact="patron")
        patron.role = "librarian"
        patron.save()
        messages.success(
            request, f"User {patron.username} has been promoted to librarian."
        )
        # Notify the user about their new role
        send_mail(
            "Role Promotion",
            "Congratulations! You have been promoted to librarian.",
            settings.DEFAULT_FROM_EMAIL,
            [patron.email],
            fail_silently=False,
        )
        # Send an in-app notification to the user
        notify.send(
            request.user,
            recipient=patron,
            verb="has promoted you to",
            target=patron,
            description="You have been promoted to librarian.",
        )
        return redirect("promote_patron")

    context = {
        "patrons": patrons,
        "search_query": search_query,
    }
    return render(request, "promote_patron.html", context)

