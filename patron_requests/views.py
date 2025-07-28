from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import BorrowItemForm
from listings.models import Item
from listings.models import Collection
from .models import CollectionAccessRequest, BorrowRequest
from django.http import HttpResponseForbidden
from django.core.mail import send_mail
from notifications.signals import notify
from django.conf import settings
@login_required

def request_collection_access(request, pk):
    #TODO: Implement a more robust request system. Should notify the librarians about the request in some way and allow them
    # to approve or deny the request.
    """Request access to a private collection."""
    # Ensure the collection exists.
    collection = get_object_or_404(Collection, pk=pk)
    # If the collection is public or user already has access, redirect.
    if not collection.is_private or request.user == collection.creator or request.user in collection.allowed_users.all():
        messages.info(request, "You already have access to this collection.")
        return redirect("collection_detail", pk=collection.pk)
    
    if request.method == "POST":
        # Check if the user has already requested access.
        if CollectionAccessRequest.objects.filter(collection=collection, patron=request.user, archived=False).exists():
            messages.info(request, "You have already requested access to this collection.")
            return redirect("collection_list")
        # Check if the user is a librarian.
        if request.user.role.strip().lower() == "librarian":
            messages.info(request, "Librarians cannot request access to collections.")
            return redirect("collection_list")
        # create new collection_access_request

        access_request = CollectionAccessRequest.objects.create(
            collection=collection,
            patron=request.user
        )
        access_request.save()
        messages.success(request, f"Your request for access to collection \"{collection.title}\" has been sent.")
        send_mail(
            "New Collection Access Request",
            f"User {request.user.username} has requested access to collection '{collection.title}'. Please review the request.",
            settings.DEFAULT_FROM_EMAIL,
            [collection.creator.email],
            fail_silently=False,  # set to False to display errors
        )
        # Send an in-app notification to the librarian
        notify.send(
            request.user,
            recipient=collection.creator,
            verb="has requested access to",
            target=collection,
            description=f"User {request.user.username} requested access to collection '{collection.title}'."
        )
        return redirect("collection_list")
    
    return render(request, "request_collection_access.html", {"collection": collection})

@login_required
def view_active_collection_requests(request):
    # Only librarians can view active collection access requests.
    if request.user.role.strip().lower() != "librarian":
        return HttpResponseForbidden("You do not have permission to view this page.")
    
    active_collection_requests = CollectionAccessRequest.objects.filter(approved=False, archived=False)
    
    context = {
        "active_collection_requests": active_collection_requests,
    }
    return render(request, "active_collection_requests.html", context)

'''


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
'''


@login_required
def approve_collection_request(request, request_id):
    # Only librarians can approve requests.
    if request.user.role.strip().lower() != "librarian":
        return HttpResponseForbidden("You do not have permission to perform this action.")
    
    access_request = get_object_or_404(CollectionAccessRequest, id=request_id)
    # Mark the request as approved.
    access_request.approved = True
    access_request.archived = True
    access_request.save()
    # Add the patron to the collection's allowed_users.
    access_request.collection.allowed_users.add(access_request.patron)
    messages.success(request, f"Access for {access_request.patron.username} to '{access_request.collection.title}' approved.")
    #Send an email to the patron informing them of the approval.
    send_mail(
    "Access Request Approved",
    f"Your request for access to collection '{access_request.collection.title}' has been approved.",
    settings.DEFAULT_FROM_EMAIL,
    [access_request.patron.email],
    fail_silently=False,  # set to False to display errors
    )
    # Send an in-app notification to the patron.
    notify.send(
        request.user,
        recipient=access_request.patron,
        verb="has approved your access to",
        target=access_request.collection,
        description=f"Your access request for collection '{access_request.collection.title}' was approved."
    )
        
    return redirect("view_active_collection_requests")

@login_required
def deny_collection_request(request, request_id):
    # Only librarians can deny requests.
    if request.user.role.strip().lower() != "librarian":
        return HttpResponseForbidden("You do not have permission to perform this action.")
    
    access_request = get_object_or_404(CollectionAccessRequest, id=request_id)
    messages.info(request, f"Access for {access_request.patron.username} to '{access_request.collection.title}' denied.")

    access_request.archived = True
    access_request.save()
    return redirect("view_active_collection_requests")

@login_required
def borrow_item_page(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if item.status != Item.CHECKED_IN:
        messages.error(request, "This item is not available for borrowing.")
        return redirect("listing_detail", pk=item.pk)
        
    if request.method == "POST":
        form = BorrowItemForm(request.POST)
        if form.is_valid():
            duration = form.cleaned_data["borrow_duration"]
            # Check if there's already a pending borrow request for this item.
            borrow_request = BorrowRequest.objects.filter(
                item=item, 
                patron=request.user,
                status=BorrowRequest.PENDING
            ).first()
            
            if borrow_request:
                # Update existing borrow request.
                borrow_request.duration = duration
                borrow_request.save()
                messages.success(request, "Your borrow request has been updated with the new duration.")
            else:
                # Create a new borrow request.
                BorrowRequest.objects.create(
                    item=item,
                    patron=request.user,
                    duration=duration,
                    status=BorrowRequest.PENDING
                )
                messages.success(request, "Your borrow request has been sent to the librarian for approval.")
            
            notify.send(
                request.user,
                recipient=item.librarian,
                verb="requested to borrow",
                target=item,
                description=f"User {request.user.username} requested to borrow item '{item.title}'."
            )
            send_mail(
                "New Borrow Request",
                f"User {request.user.username} has requested to borrow item '{item.title}' for {duration} days. Please review the request.",
                settings.DEFAULT_FROM_EMAIL,
                [item.librarian.email],
                fail_silently=False,
            )
            return redirect("listing_detail", pk=item.pk)
    else:
        form = BorrowItemForm()
        
    context = {"form": form, "item": item}
    return render(request, "borrow_item_page.html", context)

@login_required
def view_active_borrow_requests(request):
    # Only librarians can view active borrow requests.
    if request.user.role.strip().lower() != "librarian":
        return HttpResponseForbidden("You do not have permission to view this page.")
    
    active_borrow_requests = BorrowRequest.objects.filter(status=BorrowRequest.PENDING).order_by('created_at')
    context = {
        "active_borrow_requests": active_borrow_requests,
    }
    return render(request, "active_borrow_requests.html", context)

@login_required
def approve_borrow_request(request, request_id):
    # Only librarians can approve borrow requests.
    if request.user.role.strip().lower() != "librarian":
        return HttpResponseForbidden("You do not have permission to perform this action.")
    
    borrow_request = get_object_or_404(BorrowRequest, id=request_id)
    borrow_request.status = BorrowRequest.APPROVED
    borrow_request.save()
    
    # Optionally update the item status if needed.
    item = borrow_request.item
    item.status = Item.IN_CIRCULATION
    item.save()
    
    messages.success(request, f"Borrow request for '{item.title}' approved.")
    
    send_mail(
        "Borrow Request Approved",
        f"Your request to borrow '{item.title}' for {borrow_request.duration} days has been approved.",
        settings.DEFAULT_FROM_EMAIL,
        [borrow_request.patron.email],
        fail_silently=False,
    )
    
    notify.send(
        request.user,
        recipient=borrow_request.patron,
        verb="approved your borrow request for",
        target=item,
        description=f"Your request to borrow '{item.title}' for {borrow_request.duration} days was approved."
    )
    
    return redirect("view_active_borrow_requests")

@login_required
def deny_borrow_request(request, request_id):
    # Only librarians can deny borrow requests.
    if request.user.role.strip().lower() != "librarian":
        return HttpResponseForbidden("You do not have permission to perform this action.")
    
    borrow_request = get_object_or_404(BorrowRequest, id=request_id)
    borrow_request.status = BorrowRequest.DENIED
    borrow_request.save()
    
    messages.info(request, f"Borrow request for '{borrow_request.item.title}' denied.")
    
    # Notify the patron via email.
    send_mail(
        "Borrow Request Denied",
        f"Your request to borrow '{borrow_request.item.title}' has been denied.",
        settings.DEFAULT_FROM_EMAIL,
        [borrow_request.patron.email],
        fail_silently=False,
    )
    # Send an in-app notification.
    notify.send(
        request.user,
        recipient=borrow_request.patron,
        verb="denied your borrow request for",
        target=borrow_request.item,
        description=f"Your request to borrow '{borrow_request.item.title}' was denied."
    )
    
    return redirect("view_active_borrow_requests")