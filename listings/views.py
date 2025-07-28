from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import *
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from .forms import ItemForm, CollectionForm, CommentForm, ItemStatusForm
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.contrib.auth import get_user_model
from django.contrib import messages

def error_view(request, error_message):
    return render(request, "error.html", {"error_message": error_message})

def filter_private_items(queryset=None):
    """
    Returns a queryset excluding items that are already part of any private collection.
    """
    if queryset is None:
        queryset = Item.objects.all()
    # Get primary keys of items that belong to any private collection.
    private_item_ids = Collection.objects.filter(
        collection_type=Collection.PRIVATE
    ).values_list('items__pk', flat=True)
    # Exclude those items from the queryset.
    return queryset.exclude(pk__in=private_item_ids).distinct()

def collection_list(request):
    query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', '')
    collections = Collection.objects.all().annotate(num_items=Count('items'))
    
    # For non-authenticated users, only show public collections.
    if not request.user.is_authenticated:
        collections = collections.filter(collection_type='public')
    # Authenticated users see all collections (public, and private titles)
    
    if query:
        collections = collections.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )
    
    if sort_by == 'items':
        collections = collections.order_by('-num_items')
    elif sort_by == 'views':
        collections = collections.order_by('-views')
    # Additional sorting logic can remain here.
    
    context = {
        'collections': collections,
    }
    return render(request, "collection_list.html", context)

def listing_detail(request, pk):
    # Use Item instead of Listing.
    item = get_object_or_404(Item, pk=pk)
    # Increment view count safely.
    item.views += 1
    item.save()
    comments = item.comments.all().order_by('-created_at')
    
    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            # Associate the comment with the item.
            comment.item = item
            comment.user = request.user
            comment.save()
            return redirect('listing_detail', pk=item.pk)
    else:
        comment_form = CommentForm()
    
    context = {
        'listing': item,  # kept as "listing" for template compatibility.
        'comments': comments,
        'comment_form': comment_form,
    }
    return render(request, 'listing_detail.html', context)

@login_required
def like_listing(request, pk):
    # Update using Item.
    item = get_object_or_404(Item, pk=pk)
    if request.user in item.liked_by.all():
        item.liked_by.remove(request.user)
        liked = False
    else:
        item.liked_by.add(request.user)
        liked = True

    data = {
        "like_count": item.like_count(),
        "liked": liked
    }
    return JsonResponse(data)

@login_required
def listing_create(request):
    # Only librarians can create items. If the user is a patron, display an error in the UI.
    if getattr(request.user, 'role', '').strip().lower() == 'patron':
        error_message = "Patrons are not allowed to access the Create Listing page."
        return error_view(request, error_message)
    
    if request.method == "POST":
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.librarian = request.user  # Set the creator/librarian.
            item.status = Item.CHECKED_IN  # Default status.
            item.save()
            return redirect("home")
    else:
        form = ItemForm()
    return render(request, "listing_create.html", {"form": form})

@login_required
def collection_create(request):
    if request.method == "POST":
        form = CollectionForm(request.POST, request.FILES, request=request)
        if form.is_valid():
            collection_type = form.cleaned_data.get('collection_type')
            # If the user is a patron and they chose a private collection, show error
            if getattr(request.user, 'role', '').strip().lower() == 'patron' and collection_type.lower() == 'private':
                error_message = "Patrons are not allowed to create private collections."
                return error_view(request, error_message)
            collection = form.save(commit=False)
            collection.creator = request.user
            collection.save()
            form.save_m2m()
            return redirect("collection_list")
    else:
        form = CollectionForm(request=request)
    return render(request, "collection_create.html", {"form": form})
@login_required
def my_listings(request):
    if request.user.role != "librarian":
        return redirect("listing_list")
    items = Item.objects.filter(librarian=request.user)
    # Pass context as "listings" to maintain compatibility with templates.
    return render(request, "my_listings.html", {"listings": items})

@login_required
def listing_delete(request, pk):
    item = get_object_or_404(Item, pk=pk, librarian=request.user)
    if request.method == "POST":
        item.delete()
        return redirect("my_listings")
    return render(request, "listing_confirm_delete.html", {"listing": item})

@login_required
def comment_delete(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if comment.user != request.user:
        raise PermissionDenied("You are not allowed to delete this comment.")
    item_pk = comment.item.pk
    comment.delete()
    return redirect("listing_detail", pk=item_pk)

@login_required
def like_comment(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if request.user in comment.liked_by.all():
        comment.liked_by.remove(request.user)
        liked = False
    else:
        comment.liked_by.add(request.user)
        liked = True

    data = {
        "like_count": comment.like_count(),
        "liked": liked,
    }
    return JsonResponse(data)

def collection_detail(request, pk):
    #Check if user has access to collection
    if request.user.is_authenticated and not request.user.is_superuser:
        collection = get_object_or_404(Collection, pk=pk)
        if collection.is_private and request.user not in collection.allowed_users.all():
            return redirect("request_collection_access", pk=collection.pk)
    collection = get_object_or_404(Collection, pk=pk)
    items = collection.items.all()
    q = request.GET.get('q', '')
    if q:
        items = items.filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        )
    # Retrieve comments associated with the collection.
    comments = collection.comments.all().order_by('-created_at')
    collection.views += 1
    collection.save()
    
    if request.method == 'POST':
        # Only authenticated users can comment.
        if not request.user.is_authenticated:
            return redirect("account_login")
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            # Associate the comment with the collection.
            comment.collection = collection   # Ensure your Comment model has a "collection" field.
            comment.user = request.user
            comment.save()
            return redirect("collection_detail", pk=collection.pk)
    else:
        comment_form = CommentForm() if request.user.is_authenticated else None

    context = {
        'collection': collection,
        'items': items,
        'comments': comments,
        'comment_form': comment_form,
    }
    return render(request, 'collection_detail.html', context)
@login_required
def collection_create(request):
    if request.method == "POST":
        form = CollectionForm(request.POST, request.FILES, request=request)
        if form.is_valid():
            collection = form.save(commit=False)
            collection.creator = request.user
            collection.save()
            form.save_m2m()
            return redirect("collection_list")
    else:
        form = CollectionForm(request=request)
    return render(request, "collection_create.html", {"form": form})

@login_required
def like_collection(request, pk):
    collection = get_object_or_404(Collection, pk=pk)
    if request.user in collection.liked_by.all():
        collection.liked_by.remove(request.user)
        liked = False
    else:
        collection.liked_by.add(request.user)
        liked = True

    data = {
        "like_count": collection.like_count(),
        "liked": liked
    }
    return JsonResponse(data)

@login_required
def collection_delete(request, pk):
    collection = get_object_or_404(Collection, pk=pk)
    # Only the creator can delete the collection.
    if request.user != collection.creator:
        raise PermissionDenied("You are not allowed to delete this collection.")
    if request.method == "POST":
        collection.delete()
        return redirect("collection_list")
    return render(request, "collection_confirm_delete.html", {"collection": collection})

@login_required
def collection_add_item(request, pk):
    collection = get_object_or_404(Collection, pk=pk)
    # Only the creator can add items.
    if request.user != collection.creator:
        raise PermissionDenied("You are not allowed to add items to this collection.")
    if request.method == "POST":
        item_id = request.POST.get("item_id")
        item = get_object_or_404(Item, pk=item_id)
        # Directly add the item to the collection.
        collection.items.add(item)
        return redirect("collection_detail", pk=collection.pk)
    else:
        # For GET, list available items that are not already in the collection.
        available_items = Item.objects.exclude(pk__in=collection.items.values_list('pk', flat=True))
        return render(request, "collection_add_item.html", {"collection": collection, "available_items": available_items})

@login_required
def collection_remove_item(request, pk):
    collection = get_object_or_404(Collection, pk=pk)
    # Only the creator can remove items.
    if request.user != collection.creator:
        raise PermissionDenied("You are not allowed to remove items from this collection.")
    if request.method == "POST":
        item_id = request.POST.get("item_id")
        item = get_object_or_404(Item, pk=item_id)
        # Directly remove the item from the collection.
        collection.items.remove(item)
        return redirect("collection_detail", pk=collection.pk)
    else:
        # For GET, list items currently in the collection.
        items = collection.items.all()
        return render(request, "collection_remove_item.html", {"collection": collection, "items": items})

def collection_items(request, pk):
    collection = get_object_or_404(Collection, pk=pk)
    items = collection.items.all().order_by('-created_at')
    return render(request, "collection_items.html", {"collection": collection, "items": items})

@login_required
def collection_search_items(request, pk):
    collection = get_object_or_404(Collection, pk=pk)
    query = request.GET.get('q')
    items = Item.objects.all()
    
    if query:
        items = items.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        )
    # Exclude items already added to the current collection.
    items = items.exclude(pk__in=collection.items.values_list('pk', flat=True))
    
    items = filter_private_items(items)
    
    items = items.order_by('-created_at')
    
    context = {
        "collection": collection,
        "items": items,
        "query": query,
    }
    return render(request, "collection_item_search.html", context)

@login_required
def collection_create_item(request, pk):
    collection = get_object_or_404(Collection, pk=pk)
    if request.user != collection.creator:
        raise PermissionDenied("You are not allowed to add items to this collection.")
    if request.method == "POST":
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.librarian = request.user
            item.status = Item.CHECKED_IN
            item.save()
            # Associate new item with the collection
            collection.items.add(item)
            return redirect("collection_detail", pk=collection.pk)
    else:
        form = ItemForm()
    context = {
        "form": form,
        "collection": collection,
    }
    return render(request, "collection_create_item.html", context)

@login_required
def collection_edit(request, pk):
    collection = get_object_or_404(Collection, pk=pk)
    if request.method == "POST":
        form = CollectionForm(request.POST, request.FILES, instance=collection, request=request)
        if form.is_valid():
            form.save()
            return redirect("collection_detail", pk=collection.pk)
    else:
        form = CollectionForm(instance=collection, request=request)
    return render(request, "collection_edit.html", {"form": form, "collection": collection})
    

@login_required
def select_allowed_users(request, pk):
    collection = get_object_or_404(Collection, pk=pk)
    if request.user != collection.creator:
        raise PermissionDenied("You cannot update allowed users for this collection.")
    search_query = request.GET.get('q', '')
    users = User.objects.all()
    if search_query:
        users = users.filter(username__icontains=search_query)
    if request.method == "POST":
        # Get list of selected user IDs from checkboxes
        selected_user_ids = request.POST.getlist("selected_users")
        # Update the collection’s allowed_users field
        collection.allowed_users.set(selected_user_ids)
        return redirect("collection_edit", pk=collection.pk)
    context = {
        "collection": collection,
        "users": users,
        "search_query": search_query,
    }
    return render(request, "select_allowed_users.html", context)

def item_search(request):
    q = request.GET.get('q', '').strip()

    if request.user.is_authenticated:
        role = getattr(request.user, 'role', '').strip().lower()
        if role == 'librarian':
            # Librarians can see all items.
            items = Item.objects.all()
        else:
            # Patrons: allow items that are either not in any collection, or in public collections,
            # or in a private collection where they are explicitly allowed.
            items = Item.objects.filter(
                Q(collections__isnull=True) |
                Q(collections__collection_type=Collection.PUBLIC) |
                Q(collections__collection_type=Collection.PRIVATE, collections__allowed_users=request.user)
            ).distinct()
    else:
        # Guests (not logged in): show only items not in any collection or in public collections.
        items = Item.objects.filter(
            Q(collections__isnull=True) |
            Q(collections__collection_type=Collection.PUBLIC)
        ).distinct()

    if q:
        # Filter items by title or description containing the search query.
        items = items.filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        )

    context = {
        'items': items,
        'search_query': q,
    }
    return render(request, "item_search.html", context)

@login_required
def borrow_item(request, pk):
    item = get_object_or_404(Item, pk=pk)
    # Only allow borrow if item is currently checked in.
    if item.status != 'checked_in':
        messages.error(request, "This item is not available for borrowing.")
        return redirect("listing_detail", pk=pk)
    
    # Notify the librarian. You can use email (if configured) or any other notification logic.
    librarian = item.librarian
    subject = f'Borrow Request for Item: {item.title}'
    message_body = (
        f'User {request.user.username} has requested to borrow the item "{item.title}".\n'
        f'Please review the request and update the item status if necessary.'
    )
    # Uncomment the following send_mail() call after configuring your email settings.
    # send_mail(subject, message_body, 'from@example.com', [librarian.email])
    
    # Show a message to the borrower.
    messages.success(request, "Your borrow request has been sent to the librarian.")
    
    return redirect("listing_detail", pk=pk)
@login_required
def item_edit(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if request.user != item.librarian:
        raise PermissionDenied("You are not allowed to edit this item.")
    if request.method == "POST":
        form = ItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            return redirect("listing_detail", pk=item.pk)
    else:
        form = ItemForm(instance=item)
    return render(request, "item_edit.html", {"form": form, "item": item})

@login_required
def item_edit_status(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if request.user != item.librarian:
        raise PermissionDenied("You are not allowed to edit this item.")
    if request.method == "POST":
        form = ItemStatusForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, "Item status updated successfully.")
            return redirect("listing_detail", pk=item.pk)
    else:
        form = ItemStatusForm(instance=item)
    return render(request, "item_status_edit.html", {"form": form, "item": item})

@login_required
def request_collection_access(request, pk):
    collection = get_object_or_404(Collection, pk=pk)
    # If the collection is public, or the user already has access, redirect to details.
    if not collection.is_private or request.user == collection.creator or request.user in collection.allowed_users.all():
        messages.info(request, "You already have access to this collection.")
        return redirect("collection_detail", pk=collection.pk)
    
    if request.method == "POST":
        # For example purposes, automatically grant access.
        collection.allowed_users.add(request.user)
        messages.success(request, "Your request has been approved. You now have access to this collection.")
        return redirect("collection_detail", pk=collection.pk)
    
    return render(request, "request_collection_access.html", {"collection": collection})