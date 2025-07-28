import math
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from listings.models import Item
from patron_requests.models import BorrowRequest
from patron_requests.forms import BorrowItemForm
from django.conf import settings
from .forms import BorrowItemForm
from listings.models import Item
from listings.models import Collection
from .models import CollectionAccessRequest, BorrowRequest, BorrowedItem
from django.http import HttpResponseForbidden
from notifications.signals import notify
from django.conf import settings
from accounts.models import CustomUser
from django.db.models import Q

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
            due_date = form.cleaned_data["due_date"]
            now = timezone.now()
            if due_date <= now:
                form.add_error("due_date", "Due date must be in the future.")
                return render(request, "borrow_item_page.html", {"form": form, "item": item})
            # Compute an exact duration as a timedelta
            duration = due_date - now
            
            # Check if a pending borrow request already exists for this item and user.
            pending_request = BorrowRequest.objects.filter(
                item=item, 
                patron=request.user, 
                status=BorrowRequest.PENDING
            ).first()
            
            if pending_request:
                pending_request.duration = duration  # Update with new duration (timedelta)
                pending_request.save()
                messages.success(request, "Your existing borrow request has been updated.")
            else:
                BorrowRequest.objects.create(
                    item=item,
                    patron=request.user,
                    duration=duration,
                    status=BorrowRequest.PENDING
                )
                messages.success(request, "Your borrow request has been sent to the librarian for approval.")
            
            send_mail(
                "New/Updated Borrow Request",
                f"User {request.user.username} has requested to borrow item '{item.title}' for {duration}. Please review the request.",
                settings.DEFAULT_FROM_EMAIL,
                [item.librarian.email],
                fail_silently=False,
            )
            return redirect("listing_detail", pk=item.pk)
        else:
            return render(request, "borrow_item_page.html", {"form": form, "item": item})
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
    if request.user.role.strip().lower() != "librarian":
        return HttpResponseForbidden("You do not have permission to perform this action.")
    
    borrow_request = get_object_or_404(BorrowRequest, id=request_id)
    borrow_request.status = BorrowRequest.APPROVED
    borrow_request.save()
    
    item = borrow_request.item
    item.status = Item.IN_CIRCULATION
    item.save()
    
    # Create a BorrowedItem record (if one doesn't already exist)
    try:
        from patron_requests.models import BorrowedItem
    except ImportError:
        BorrowedItem = None

    if BorrowedItem is not None and not hasattr(borrow_request, 'borrowed_item'):
        BorrowedItem.objects.create(
            borrow_request=borrow_request,
            item=item,
            patron=borrow_request.patron,
            duration=borrow_request.duration  # This is now a timedelta
        )

    messages.success(request, f"Borrow request for '{item.title}' approved.")
    
    send_mail(
        "Borrow Request Approved",
        f"Your request to borrow '{item.title}' for {borrow_request.duration} has been approved.",
        settings.DEFAULT_FROM_EMAIL,
        [borrow_request.patron.email],
        fail_silently=False,
    )
    
    notify.send(
        request.user,
        recipient=borrow_request.patron,
        verb="approved your borrow request for",
        target=item,
        description=f"Your request to borrow '{item.title}' for {borrow_request.duration} was approved."
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

@login_required
def view_active_borrowed_items(request):
    borrowed_items = BorrowedItem.objects.filter(returned_at__isnull=True)
    context = {
        "borrowed_items": borrowed_items,
    }
    return render(request, "active_borrowed_items.html", context)

@login_required
def view_borrowed_items(request):
    # Librarians see all borrowed items; patrons see only their borrowed items.
    if request.user.role.strip().lower() == "librarian":
        borrowed_items = BorrowedItem.objects.all().order_by("-start_date")
    else:
        borrowed_items = BorrowedItem.objects.filter(patron=request.user).order_by("-start_date")
    # Only get borrowed items that haven't been marked as returned
    borrowed_items = BorrowedItem.objects.filter(returned_at__isnull=True)
    context = {"borrowed_items": borrowed_items}
    return render(request, "borrowed_items_page.html", context)

@login_required
def return_borrowed_item(request, pk):
    borrowed_item = get_object_or_404(BorrowedItem, pk=pk)
    
    # Only allow the patron who borrowed, or a librarian.
    if request.user != borrowed_item.patron and request.user.role.strip().lower() != "librarian":
        messages.error(request, "You do not have permission to return this item.")
        return redirect('view_active_borrowed_items')
    
    # Check if the item is already returned.
    if borrowed_item.returned_at is not None:
        messages.info(request, "This item has already been returned.")
        return redirect('view_active_borrowed_items')
    
    # Mark the item as returned (since returned_at is currently None)
    borrowed_item.returned_at = timezone.now()
    borrowed_item.save()
    
    # Optionally update the associated item's status and send a notification
    item = borrowed_item.item
    item.status = Item.CHECKED_IN  # Adjust if your model differs.
    item.save()
    
    send_mail(
        "Item Returned",
        f"Your borrowed item '{item.title}' has been returned successfully and is now available.",
        settings.DEFAULT_FROM_EMAIL,
        [borrowed_item.patron.email],
        fail_silently=False,
    )
    
    messages.success(request, f"'{item.title}' has been returned successfully.")
    return redirect('view_active_borrowed_items')




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
            role__iexact="patron"
        )
    
    if request.method == "POST":
        user_id = request.POST.get("user_id")
        patron = get_object_or_404(CustomUser, pk=user_id, role__iexact="patron")
        patron.role = "librarian"
        patron.save()
        messages.success(request, f"User {patron.username} has been promoted to librarian.")
        # Notify the user about their new role
        send_mail(
            "Role Promotion",
            f"Congratulations! You have been promoted to librarian.",
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
            description="You have been promoted to librarian."
        )
        return redirect("promote_patron")
    
    context = {
        "patrons": patrons,
        "search_query": search_query,
    }
    return render(request, "promote_patron.html", context)