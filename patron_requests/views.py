from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from listings.models import Collection
from .models import CollectionAccessRequest
from django.http import HttpResponseForbidden
from django.core.mail import send_mail
from notifications.signals import notify
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
        if CollectionAccessRequest.objects.filter(collection=collection, patron=request.user).exists():
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
            "lora-app@gmail.com",
            [collection.creator.email],
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
    
    active_collection_requests = CollectionAccessRequest.objects.filter(approved=False)
    
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
    access_request.save()
    # Add the patron to the collection's allowed_users.
    access_request.collection.allowed_users.add(access_request.patron)
    messages.success(request, f"Access for {access_request.patron.username} to '{access_request.collection.title}' approved.")
    #Send an email to the patron informing them of the approval.
    send_mail(
        "Access Request Approved",
        f"Your request for access to collection '{access_request.collection.title}' has been approved.",
        "lora-app@gmail.com",
        [access_request.patron.email],
        fail_silently=True,
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
    # Delete the request.
    access_request.delete()
    return redirect("view_active_collection_requests")