from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import *
from patron_requests.models import BorrowRequest
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from .forms import ItemForm, CollectionForm, CommentForm, ItemStatusForm, BorrowItemForm
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q, Avg
from django.contrib.auth import get_user_model
from django.contrib import messages
from notifications.signals import notify
from django.core.mail import send_mail
import requests
from django.core.files.base import ContentFile

def error_view(request, error_message):
    return render(request, "error.html", {"error_message": error_message})

def filter_private_items(queryset=None):
    """
    Returns items that are NOT in any collection with collection_type==PRIVATE.
    """
    if queryset is None:
        queryset = Item.objects.all()
    return queryset.exclude(collections__collection_type=Collection.PRIVATE).distinct()


def filter_public_items(queryset=None):
    """
    Returns items that are NOT in any collection with collection_type==PUBLIC.
    """
    if queryset is None:
        queryset = Item.objects.all()
    return queryset.exclude(collections__collection_type=Collection.PUBLIC).distinct()

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
            Q(title__icontains=query) | Q(description__icontains(query))
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
        'lora_model': item.lora_model,  # Add LoRA model to context
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
    if getattr(request.user, 'role', '').strip().lower() == 'patron':
        messages.error(request, "Patrons are not allowed to create listings.")
        return redirect("home")
    
    if request.method == "POST":
        form = ItemForm(request.POST, request.FILES)
        images = request.FILES.getlist('images')
        loRA_model = request.FILES.get('lora_model')  # This handles LoRA model file upload
        if form.is_valid():
            item = form.save(commit=False)
            item.librarian = request.user
            item.status = Item.CHECKED_IN
            item.save()

            # Handle LoRA model if provided
            if loRA_model:
                import torch
                from diffusers import StableDiffusionPipeline

                # Assuming the LoRA model is a checkpoint file compatible with HuggingFace Diffusers
                try:
                    lora_path = 'path_to_lora_storage'  # You can store the LoRA model on a server or cloud storage
                    with open(lora_path, 'wb') as f:
                        for chunk in loRA_model.chunks():
                            f.write(chunk)

                    # Load the LoRA model using Hugging Face's diffusers
                    pipeline = StableDiffusionPipeline.from_pretrained('CompVis/stable-diffusion-v-1-4-original', use_auth_token=True)
                    # Apply LoRA (example: you would apply LoRA to the pipeline)
                    lora = torch.load(lora_path)
                    pipeline.unet.load_state_dict(lora['state_dict'])

                    # Apply LoRA model logic (e.g., generate an image using the model)
                    # Example: Generate image (this part will depend on your exact usage)
                    prompt = "A futuristic city"
                    generated_image = pipeline(prompt).images[0]
                    generated_image_path = 'generated_images/generated_image.png'
                    generated_image.save(generated_image_path)

                    # Save generated image to the Item or related model
                    ItemImage.objects.create(item=item, image=generated_image_path)

                except Exception as e:
                    messages.error(request, f"Error applying LoRA model: {e}")

            if not images:
                import requests
                from django.core.files.base import ContentFile
                
                # Replace with your actual default image URL on S3
                default_image_url = "https://cs3240loraapp.s3.amazonaws.com/items/default_item_image.png"
                
                try:
                    response = requests.get(default_image_url)
                    if response.status_code == 200:
                        default_content = ContentFile(response.content, name="default_item_image.png")
                        item_image = ItemImage(item=item)
                        item_image.image.save("default_item_image.png", default_content)
                    else:
                        print(f"Error: Could not retrieve default image from S3. Status code: {response.status_code}")
                except Exception as e:
                    print(f"Error retrieving default image from S3: {e}")
            else:
                for image in images:
                    ItemImage.objects.create(item=item, image=image)

            messages.success(request, "Item created successfully!")
            return redirect("listing_detail", pk=item.pk)
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
def item_delete(request, pk):
    item = get_object_or_404(Item, pk=pk)
    # Only allow the librarian/owner to delete the item.
    if request.user != item.librarian:
        messages.error(request, "You are not authorized to delete this item.")
        return redirect('listing_detail', pk=item.pk)
        
    if request.method == "POST":
        # Remove the item from all collections.
        item.collections.clear()
        # Explicitly delete all associated images so that their file deletion logic in delete() is invoked.
        for image in item.images.all():
            image.delete()
        # Delete the item.
        item.delete()
        messages.success(request, "Item and associated images deleted successfully.")
        # Redirect to a suitable page (e.g., dashboard or listings list)
        return redirect('dashboard')
    
    # Optionally show a confirmation page.
    return render(request, 'confirm_delete.html', {'item': item})

@login_required
def comment_delete(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if comment.user != request.user:
        raise PermissionDenied("You are not allowed to delete this comment.")
    
    if comment.item:
        redirect_url = "listing_detail"
        redirect_pk = comment.item.pk
    elif comment.collection:
        redirect_url = "collection_detail"
        redirect_pk = comment.collection.pk
    else:
        # Fallback in case neither field is set.
        redirect_url = "home"
        redirect_pk = None
    
    comment.delete()
    if redirect_pk:
        return redirect(redirect_url, pk=redirect_pk)
    return redirect(redirect_url)

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
    # Use request.headers instead of deprecated request.is_ajax()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse(data)
    else:
        # Fallback: redirect back to the page where the comment is
        return redirect(request.META.get('HTTP_REFERER', 'home'))

def collection_detail(request, pk):
    #Check if user has access to collection
    if request.user.is_authenticated and not request.user.is_superuser:
        collection = get_object_or_404(Collection, pk=pk)
        if collection.is_private and request.user not in collection.allowed_users.all() and request.user != collection.creator:
            return redirect("request_collection_access", pk=collection.pk)
    collection = get_object_or_404(Collection, pk=pk)
    items = collection.items.all()
    q = request.GET.get('q', '')
    if q:
        items = items.filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        )
    # Retrieve comments associated with the collection.
    comments = collection.collection_comments.all().order_by('-created_at')

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
            # Remove the following line as it's not required:
            # collection.comments.add(comment)
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
def collection_add_item(request, collection_pk, item_pk):
    collection = get_object_or_404(Collection, pk=collection_pk)
    if request.user != collection.creator:
        raise PermissionDenied("You are not allowed to add items to this collection.")
    item = get_object_or_404(Item, pk=item_pk)
    collection.items.add(item)
    messages.success(request, "Item added successfully!")
    return redirect("collection_detail", pk=collection.pk)

@login_required
def collection_remove_item(request, collection_pk, item_pk):
    collection = get_object_or_404(Collection, pk=collection_pk)
    if request.user != collection.creator:
        raise PermissionDenied("You are not allowed to remove items from this collection.")
    if request.method == "POST":
        item = get_object_or_404(Item, pk=item_pk)
        collection.items.remove(item)
        return redirect("collection_detail", pk=collection.pk)
    # For GET, you might list items currently in the collection or show a confirmation.
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
    if collection.collection_type == Collection.PUBLIC:
        if query:
            items = items.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query)
            )
        # Exclude items already added to the current collection.
        items = items.exclude(pk__in=collection.items.values_list('pk', flat=True))
        
        items = filter_private_items(items)
        
        items = items.order_by('-created_at')
    elif collection.collection_type == Collection.PRIVATE:
        if query:
            items = items.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query)
            )
        # Exclude items already added to the current collection.
        items = items.exclude(pk__in=collection.items.values_list('pk', flat=True))
        items = filter_private_items(items)
        items = filter_public_items(items)
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
        images = request.FILES.getlist('images')
        if form.is_valid():
            item = form.save(commit=False)
            item.librarian = request.user
            item.status = Item.CHECKED_IN
            item.save()
            # Associate new item with the collection.
            collection.items.add(item)
            # Process uploaded images.
            if images:
                for image in images:
                    ItemImage.objects.create(item=item, image=image)
            else:
                # No custom images uploaded – create a default image record.
                ItemImage.objects.create(item=item)
            messages.success(request, "Item created and images uploaded successfully!")
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
        # Get list of selected user IDs from checkboxes.
        selected_user_ids = request.POST.getlist("selected_users")
        # Get current allowed user IDs as integers.
        current_user_ids = set(collection.allowed_users.values_list('id', flat=True))
        # Convert submitted ids to a set of ints.
        new_user_ids = set(int(i) for i in selected_user_ids)
        # Determine which users were added or removed.
        added_ids = new_user_ids - current_user_ids
        removed_ids = current_user_ids - new_user_ids
        # Update the collection’s allowed_users field.
        collection.allowed_users.set(selected_user_ids)

        # Send notifications and email for added users.
        for user in User.objects.filter(id__in=added_ids):
            print(user.email)
            notify.send(
                request.user,
                recipient=user,
                verb="granted access to",
                target=collection,
                description=f"You have been granted access to collection '{collection.title}'."
            )
            send_mail(
                f"Access Granted: {collection.title}",
                f"Hello {user.username},\n\nYou have been granted access to the collection '{collection.title}'.",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )

        # Send notifications and email for removed users.
        for user in User.objects.filter(id__in=removed_ids):
            print(user.email)
            notify.send(
                request.user,
                recipient=user,
                verb="revoked access from",
                target=collection,
                description=f"Your access to collection '{collection.title}' has been revoked."
            )
            send_mail(
                f"Access Revoked: {collection.title}",
                f"Hello {user.username},\n\nYour access to the collection '{collection.title}' has been revoked.",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )

        messages.success(request, "Allowed users updated successfully.")
        return redirect("collection_detail", pk=collection.pk)
    context = {
        "collection": collection,
        "users": users,
        "search_query": search_query,
    }
    return render(request, "select_allowed_users.html", context)

def item_search(request):
    q = request.GET.get('q', '').strip()
    search_type = request.GET.get('search_type', 'name')
    status_filter = request.GET.get('status', '').strip()
    sort = request.GET.get('sort', '')
    
    items = Item.objects.all()
    
    if q:
        if search_type == "location":
            items = items.filter(location__icontains=q)
        else:
            items = items.filter(
                Q(title__icontains=q) |
                Q(description__icontains=q) |
                Q(identifier__icontains=q)
            )
    if status_filter:
        items = items.filter(status=status_filter)
    
    items = items.annotate(num_likes=Count('liked_by'))
    
    if sort == "likes":
        items = items.order_by('-num_likes')
    elif sort == "views":
        items = items.order_by('-views')
    else:
        items = items.order_by('-created_at')
    
    context = {
        "items": items,
        "status_choices": Item.STATUS_CHOICES,
        "sort_options": [("", "Newest"), ("likes", "Likes"), ("views", "Views")],
    }
    return render(request, "item_search.html", context)

@login_required
def item_edit(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if request.user != item.librarian:
        raise PermissionDenied("You are not allowed to edit this item.")
    if request.method == "POST":
        form = ItemForm(request.POST, request.FILES, instance=item)
        new_images = request.FILES.getlist('images')
        if form.is_valid():
            form.save()
            for image in new_images:
                ItemImage.objects.create(item=item, image=image)
            messages.success(request, "Item updated successfully!")
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
def delete_item_image(request, pk):
    image = get_object_or_404(ItemImage, pk=pk)
    # Only allow the item's librarian to delete its image.
    if request.user != image.item.librarian:
        raise PermissionDenied("You are not authorized to delete this image.")
    
    item_obj = image.item
    
    if request.method == "POST":
        image.delete()  # This will remove the file (if not default) and delete the record.

        messages.success(request, "Image deleted successfully.")
        
        # After deletion, if there are no custom images _and_ no default image record,
        # then create a default image record.
        if not item_obj.images.exclude(image__icontains="default_item_image.png").exists():
            if not item_obj.images.filter(image__icontains="default_item_image.png").exists():
                ItemImage.objects.create(item=item_obj, image="items/default_item_image.png")
                messages.info(request, "No custom images left. Default image added.")
                
        return redirect('item_edit', pk=item_obj.pk)
    
    return render(request, 'confirm_delete.html', {'image': image})

@login_required
def rate_item(request, pk):
    item = get_object_or_404(Item, pk=pk)
    if request.method == "POST":
        try:
            rating_value = int(request.POST.get("rating"))
            if rating_value < 1 or rating_value > 5:
                raise ValueError("Invalid rating range.")
        except (ValueError, TypeError):
            messages.error(request, "Invalid rating submitted.")
            return redirect("listing_detail", pk=item.pk)
        
        # Create or update the rating by the current user
        ItemRating.objects.update_or_create(
            item=item, user=request.user,
            defaults={"rating": rating_value}
        )
        
        # Calculate the new average rating.
        agg = item.ratings.aggregate(avg=Avg("rating"))
        item.rating = agg["avg"] if agg["avg"] is not None else 0.0
        item.save()
        
        messages.success(request, "Your rating has been submitted.")
    return redirect("listing_detail", pk=item.pk)
