import requests
import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from notifications.signals import notify
from django.views.decorators.csrf import csrf_exempt
from .forms import CommentForm, LoRAForm, LoRAStatusForm, ModelForm
from .models import *
import re
import json as pyjson
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import html
def error_view(request, error_message):
    return render(request, "error.html", {"error_message": error_message})


def filter_private_loras(queryset=None):
    """
    Returns LoRAs that are NOT in any model with model_type==PRIVATE.
    """
    if queryset is None:
        queryset = LoRA.objects.all()
    return queryset.exclude(models__model_type=Model.PRIVATE).distinct()


def filter_public_loras(queryset=None):
    """
    Returns LoRAs that are NOT in any model with model_type==PUBLIC.
    """
    if queryset is None:
        queryset = LoRA.objects.all()
    return queryset.exclude(models__model_type=Model.PUBLIC).distinct()


def model_list(request):
    query = request.GET.get("q", "")
    sort_by = request.GET.get("sort", "")
    models = Model.objects.all().annotate(num_loras=Count("loras"))

    # For non-authenticated users, only show public models.
    if not request.user.is_authenticated:
        models = models.filter(model_type="public")
    # Authenticated users see all models (public, and private titles)

    if query:
        models = models.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )

    if sort_by == "loras":
        models = models.order_by("-num_loras")
    elif sort_by == "views":
        models = models.order_by("-views")
    # Additional sorting logic can remain here.

    context = {
        "models": models,
    }
    return render(request, "model_list.html", context)


def listing_detail(request, pk):
    # Use LoRA instead of Item
    lora = get_object_or_404(LoRA, pk=pk)
    # Increment view count safely.
    lora.views += 1
    lora.save()
    comments = lora.comments.all().order_by("-created_at")

    if request.method == "POST":
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            # Associate the comment with the lora.
            comment.lora = lora
            comment.user = request.user
            comment.save()
            return redirect("listing_detail", pk=lora.pk)
    else:
        comment_form = CommentForm()

    context = {
        "listing": lora,  # kept as "listing" for template compatibility.
        "comments": comments,
        "comment_form": comment_form,
    }
    return render(request, "listing_detail.html", context)


@login_required
def like_listing(request, pk):
    # Update using LoRA
    lora = get_object_or_404(LoRA, pk=pk)
    if request.user in lora.liked_by.all():
        lora.liked_by.remove(request.user)
        liked = False
    else:
        lora.liked_by.add(request.user)
        liked = True

    data = {"like_count": lora.like_count(), "liked": liked}
    return JsonResponse(data)


# in listings/views.py

from django.core.files.base import ContentFile

@login_required
def listing_create(request):
    if request.method == "POST":
        form = LoRAForm(request.POST, request.FILES)
        uploaded_files = request.FILES.getlist("images")
        autofill_json = request.POST.get("autofill_images", "")

        if form.is_valid():
            lora = form.save(commit=False)
            lora.librarian = request.user
            lora.status = LoRA.CHECKED_IN
            lora.save()

            # 1) Save manually uploaded images
            for img in uploaded_files:
                LoRAImage.objects.create(lora=lora, image=img)

            # 2) Save autofill images
            if autofill_json:
                try:
                    urls = pyjson.loads(autofill_json)
                except Exception:
                    urls = []
                for idx, url in enumerate(urls[:5]):
                    try:
                        resp = requests.get(url, timeout=10)
                        if resp.status_code == 200:
                            ext = url.split("?")[0].rsplit(".", 1)[-1]
                            fname = f"autofill_{lora.pk}_{idx}.{ext}"
                            content = ContentFile(resp.content, name=fname)
                            LoRAImage.objects.create(lora=lora, image=content)
                    except Exception:
                        continue

            # 3) If still no images, attach default
            if not LoRAImage.objects.filter(lora=lora).exists():
                LoRAImage.objects.create(
                    lora=lora
                )

            messages.success(request, "LoRA created successfully!")
            return redirect("listing_detail", pk=lora.pk)
    else:
        form = LoRAForm()

    return render(request, "lora_create.html", {"form": form})

@login_required
def comment_delete(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if comment.user != request.user and request.user.role != "librarian":
        raise PermissionDenied("You are not allowed to delete this comment.")

    if comment.lora:
        redirect_url = "listing_detail"
        redirect_pk = comment.lora.pk
    elif comment.model:
        redirect_url = "model_detail"
        redirect_pk = comment.model.pk
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
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse(data)
    else:
        # Fallback: redirect back to the page where the comment is
        return redirect(request.META.get("HTTP_REFERER", "home"))


@login_required
def select_allowed_users(request, pk):
    model = get_object_or_404(Model, pk=pk)
    if request.user != model.creator:
        raise PermissionDenied("You cannot update allowed users for this model.")
    search_query = request.GET.get("q", "")
    users = User.objects.all()
    if search_query:
        users = users.filter(username__icontains=search_query)
    if request.method == "POST":
        # Get list of selected user IDs from checkboxes.
        selected_user_ids = request.POST.getlist("selected_users")
        # Get current allowed user IDs as integers.
        current_user_ids = set(model.allowed_users.values_list("id", flat=True))
        # Convert submitted ids to a set of ints.
        new_user_ids = set(int(i) for i in selected_user_ids)
        # Determine which users were added or removed.
        added_ids = new_user_ids - current_user_ids
        removed_ids = current_user_ids - new_user_ids
        # Update the model's allowed_users field.
        model.allowed_users.set(selected_user_ids)

        # Send notifications and email for added users.
        for user in User.objects.filter(id__in=added_ids):
            print(user.email)
            notify.send(
                request.user,
                recipient=user,
                verb="granted access to",
                target=model,
                description=f"You have been granted access to model '{model.title}'.",
            )
            send_mail(
                f"Access Granted: {model.title}",
                f"Hello {user.username},\n\nYou have been granted access to the model '{model.title}'.",
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
                target=model,
                description=f"Your access to model '{model.title}' has been revoked.",
            )
            send_mail(
                f"Access Revoked: {model.title}",
                f"Hello {user.username},\n\nYour access to the model '{model.title}' has been revoked.",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )

        messages.success(request, "Allowed users updated successfully.")
        return redirect("model_detail", pk=model.pk)
    context = {
        "model": model,
        "users": users,
        "search_query": search_query,
    }
    return render(request, "select_allowed_users.html", context)


@login_required
def my_loras(request):
    if request.user.role != "librarian":
        return redirect("model_list")
    loras = LoRA.objects.filter(librarian=request.user)
    # Pass context as "listings" to maintain compatibility with templates.
    return render(request, "my_listings.html", {"listings": loras})


@login_required
def lora_delete(request, pk):
    lora = get_object_or_404(LoRA, pk=pk)
    # Only allow the librarian/owner to delete the lora.
    if request.user != lora.librarian:
        messages.error(request, "You are not authorized to delete this LoRA.")
        return redirect("listing_detail", pk=lora.pk)

    if request.method == "POST":
        # Remove the lora from all models.
        lora.models.clear()
        # Explicitly delete all associated images so that their file deletion logic in delete() is invoked.
        for image in lora.images.all():
            image.delete()
        # Delete the lora.
        lora.delete()
        messages.success(request, "LoRA and associated images deleted successfully.")
        # Redirect to a suitable page (e.g., dashboard or listings list)
        return redirect("dashboard")

    # Optionally show a confirmation page.
    return render(request, "lora_confirm_delete.html", {"lora": lora})


def model_detail(request, pk):
    # Check if user has access to model
    if request.user.is_authenticated and not request.user.is_superuser:
        model = get_object_or_404(Model, pk=pk)
        if (
            model.is_private
            and request.user not in model.allowed_users.all()
            and request.user != model.creator
            and request.user.role != "librarian"
        ):
            return redirect("request_model_access", pk=model.pk)
    model = get_object_or_404(Model, pk=pk)
    loras = model.loras.all()
    q = request.GET.get("q", "")
    if q:
        loras = loras.filter(Q(title__icontains=q) | Q(description__icontains=q))
    # Retrieve comments associated with the model.
    comments = model.model_comments.all().order_by("-created_at")

    model.views += 1
    model.save()

    if request.method == "POST":
        # Only authenticated users can comment.
        if not request.user.is_authenticated:
            return redirect("account_login")
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            # Associate the comment with the model.
            comment.model = model
            comment.user = request.user
            comment.save()
            return redirect("model_detail", pk=model.pk)
    else:
        comment_form = CommentForm() if request.user.is_authenticated else None

    context = {
        "model": model,
        "loras": loras,
        "comments": comments,
        "comment_form": comment_form,
    }
    return render(request, "model_detail.html", context)


@login_required
def model_create(request):
    if request.method == "POST":
        form = ModelForm(request.POST, request.FILES, request=request)
        if form.is_valid():
            model_type = form.cleaned_data.get("model_type")
            # If the user is a patron and they chose a private model, show error
            if (
                getattr(request.user, "role", "").strip().lower() == "patron"
                and model_type
                and model_type.lower() == "private"
            ):
                error_message = "Patrons are not allowed to create private models."
                return error_view(request, error_message)
            model = form.save(commit=False)
            model.creator = request.user
            model.save()
            form.save_m2m()
            return redirect("model_list")
    else:
        form = ModelForm(request=request)
    return render(request, "model_create.html", {"form": form})


@login_required
def model_delete(request, pk):
    model = get_object_or_404(Model, pk=pk)
    # Only the creator can delete the model.
    if request.user != model.creator and request.user.role != "librarian":
        raise PermissionDenied("You are not allowed to delete this model.")
    if request.method == "POST":
        model.delete()
        return redirect("model_list")
    return render(request, "model_confirm_delete.html", {"model": model})


@login_required
def model_edit(request, pk):
    model = get_object_or_404(Model, pk=pk)
    if request.user != model.creator and request.user.role != "librarian":
        raise PermissionDenied("You are not allowed to edit this model.")
    if request.method == "POST":
        form = ModelForm(request.POST, request.FILES, instance=model, request=request)
        if form.is_valid():
            form.save()
            return redirect("model_detail", pk=model.pk)
    else:
        form = ModelForm(instance=model, request=request)
    return render(request, "model_edit.html", {"form": form, "model": model})


@login_required
def model_add_lora(request, model_pk, lora_pk):
    model = get_object_or_404(Model, pk=model_pk)
    if request.user != model.creator and request.user.role != "librarian":
        raise PermissionDenied("You are not allowed to add LoRAs to this model.")
    lora = get_object_or_404(LoRA, pk=lora_pk)
    model.loras.add(lora)
    messages.success(request, "LoRA added successfully!")
    return redirect("model_detail", pk=model.pk)


@login_required
def model_remove_lora(request, model_pk, lora_pk):
    model = get_object_or_404(Model, pk=model_pk)
    if request.user != model.creator and request.user.role != "librarian":
        raise PermissionDenied("You are not allowed to remove LoRAs from this model.")
    lora = get_object_or_404(LoRA, pk=lora_pk)
    model.loras.remove(lora)
    return redirect("model_detail", pk=model.pk)


def model_loras(request, pk):
    model = get_object_or_404(Model, pk=pk)
    loras = model.loras.all().order_by("-created_at")
    return render(request, "model_loras.html", {"model": model, "loras": loras})


@login_required
def like_model(request, pk):
    model = get_object_or_404(Model, pk=pk)
    if request.user in model.liked_by.all():
        model.liked_by.remove(request.user)
        liked = False
    else:
        model.liked_by.add(request.user)
        liked = True

    data = {"like_count": model.like_count(), "liked": liked}
    return JsonResponse(data)


@login_required
def model_search_loras(request, pk):
    model = get_object_or_404(Model, pk=pk)
    query = request.GET.get("q")
    loras = LoRA.objects.all()
    if model.model_type == Model.PUBLIC:
        if query:
            loras = loras.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            )
        # Exclude loras already added to the current model.
        loras = loras.exclude(pk__in=model.loras.values_list("pk", flat=True))

        loras = filter_private_loras(loras)

        loras = loras.order_by("-created_at")
    elif model.model_type == Model.PRIVATE:
        if query:
            loras = loras.filter(
                Q(title__icontains=query) | Q(description__icontain=query)
            )
        # Exclude loras already added to the current model.
        loras = loras.exclude(pk__in=model.loras.values_list("pk", flat=True))
        loras = filter_private_loras(loras)
        loras = filter_public_loras(loras)
        loras = loras.order_by("-created_at")
    context = {
        "model": model,
        "loras": loras,
        "query": query,
    }
    return render(request, "model_item_search.html", context)


@login_required
def model_create_lora(request, pk):
    model = get_object_or_404(Model, pk=pk)
    if request.user != model.creator and request.user.role != "librarian":
        raise PermissionDenied("You are not allowed to add LoRAs to this model.")
    if request.method == "POST":
        form = LoRAForm(request.POST,    request.FILES)
        images = request.FILES.getlist("images")
        if form.is_valid():
            lora = form.save(commit=False)
            lora.librarian = request.user
            lora.status = LoRA.CHECKED_IN
            lora.save()
            # Associate new lora with the model.
            model.loras.add(lora)
            # Process uploaded images.
            if images:
                for image in images:
                    LoRAImage.objects.create(lora=lora, image=image)
            else:
                default_image_url = "https://cs3240loraapp.s3.amazonaws.com/items/default_item_image.png"

                try:
                    response = requests.get(default_image_url)
                    if response.status_code == 200:
                        default_content = ContentFile(
                            response.content, name="default_item_image.png"
                        )
                        lora_image = LoRAImage(lora=lora)
                        lora_image.image.save("default_item_image.png", default_content)
                    else:
                        print(
                            f"Error: Could not retrieve default image from S3. Status code: {response.status_code}"
                        )
                except Exception as e:
                    print(f"Error retrieving default image from S3: {e}")
                    # Fallback to regular creation if S3 fetch fails
                    LoRAImage.objects.create(lora=lora)
            messages.success(request, "LoRA created and images uploaded successfully!")
            return redirect("model_detail", pk=model.pk)
    else:
        form = LoRAForm()
    context = {
        "form": form,
        "model": model,
    }
    return render(request, "model_create_lora.html", context)


def lora_search(request):
    q = request.GET.get("q", "").strip()
    search_type = request.GET.get("search_type", "name")
    status_filter = request.GET.get("status", "").strip()
    sort = request.GET.get("sort", "")

    loras = LoRA.objects.all()

    if q:
        if search_type == "location":
            loras = loras.filter(location__icontains=q)
        else:
            loras = loras.filter(
                Q(title__icontains=q)
                | Q(description__icontains=q)
                | Q(identifier__icontains=q)
            )
    if status_filter:
        loras = loras.filter(status=status_filter)

    loras = loras.annotate(num_likes=Count("liked_by"))

    if sort == "likes":
        loras = loras.order_by("-num_likes")
    elif sort == "views":
        loras = loras.order_by("-views")
    else:
        loras = loras.order_by("-created_at")

    context = {
        "loras": loras,
        "status_choices": LoRA.STATUS_CHOICES,
        "sort_options": [("", "Newest"), ("likes", "Likes"), ("views", "Views")],
    }
    return render(request, "lora_search.html", context)


@login_required
def lora_edit(request, pk):
    lora = get_object_or_404(LoRA, pk=pk)
    if request.user != lora.librarian and request.user.role != "librarian":
        raise PermissionDenied("You are not allowed to edit this LoRA.")
    if request.method == "POST":
        form = LoRAForm(request.POST, request.FILES, instance=lora)
        new_images = request.FILES.getlist("images")
        if form.is_valid():
            form.save()
            for image in new_images:
                LoRAImage.objects.create(lora=lora, image=image)
            if request.user.role.strip().lower() == "librarian" and request.user != lora.librarian:
                notify.send(
                    request.user,
                    recipient=lora.librarian,
                    verb="edited your LoRA",
                    target=lora,
                    description=f"A librarian has edited your LoRA \"{lora.title}\"."
                )
            messages.success(request, "LoRA updated successfully!")
            return redirect("listing_detail", pk=lora.pk)
    else:
        form = LoRAForm(instance=lora)
    return render(request, "lora_edit.html", {"form": form, "lora": lora})


@login_required
def lora_edit_status(request, pk):
    lora = get_object_or_404(LoRA, pk=pk)
    if request.user != lora.librarian and request.user.role != "librarian":
        raise PermissionDenied("You are not allowed to edit this LoRA.")
    if request.method == "POST":
        form = LoRAStatusForm(request.POST, instance=lora)
        if form.is_valid():
            form.save()
            messages.success(request, "LoRA status updated successfully.")
            if lora.status == LoRA.CHECKED_OUT:
                # Notify the librarian about the status change.
                notify.send(
                    request.user,
                    recipient=lora.librarian,
                    verb="changed the status of",
                    target=lora,
                    description=f"The status of '{lora.title}' has been changed to '{lora.get_status_display()}'.",
                )
            messages.success(request, "LoRA status updated successfully.")
            return redirect("listing_detail", pk=lora.pk)
    else:
        form = LoRAStatusForm(instance=lora)
    return render(request, "lora_status_edit.html", {"form": form, "lora": lora})


@login_required
def delete_lora_image(request, pk):
    image = get_object_or_404(LoRAImage, pk=pk)
    # Only allow the lora's librarian to delete its image.
    if request.user != image.lora.librarian and request.user.role != "librarian":
        raise PermissionDenied("You are not authorized to delete this image.")

    lora_obj = image.lora

    if request.method == "POST":
        image.delete()  # This will remove the file (if not default) and delete the record.

        messages.success(request, "Image deleted successfully.")

        # After deletion, if there are no custom images _and_ no default image record,
        # then create a default image record.
        if not lora_obj.images.exclude(
            image__icontains="default_item_image.png"
        ).exists():
            if not lora_obj.images.filter(
                image__icontains="default_item_image.png"
            ).exists():
                LoRAImage.objects.create(
                    lora=lora_obj, image="items/default_item_image.png"
                )
                messages.info(request, "No custom images left. Default image added.")

        return redirect("lora_edit", pk=lora_obj.pk)

    return render(request, "confirm_delete.html", {"image": image})


@login_required
def rate_lora(request, pk):
    lora = get_object_or_404(LoRA, pk=pk)
    if request.method == "POST":
        try:
            rating_value = int(request.POST.get("rating"))
            if rating_value < 1 or rating_value > 5:
                raise ValueError("Invalid rating range.")
        except (ValueError, TypeError):
            messages.error(request, "Invalid rating submitted.")
            return redirect("listing_detail", pk=lora.pk)

        # Create or update the rating by the current user
        LoRARating.objects.update_or_create(
            lora=lora, user=request.user, defaults={"rating": rating_value}
        )

        # Calculate the new average rating.
        agg = lora.ratings.aggregate(avg=Avg("rating"))
        lora.rating = agg["avg"] if agg["avg"] is not None else 0.0
        lora.save()

        messages.success(request, "Your rating has been submitted.")
    return redirect("listing_detail", pk=lora.pk)


def extract_hf_metadata(html_text, source_url):
    """
    Parse the HF JSON and append author credit into the description.
    """
    soup = BeautifulSoup(html_text, "html.parser")
    div = soup.find(
        "div",
        class_="SVELTE_HYDRATER contents",
        attrs={"data-target": "ModelHeader"},
    )
    if not div or not div.has_attr("data-props"):
        return {"error": "Could not find model header JSON."}

    raw = html.unescape(div["data-props"])
    props = pyjson.loads(raw)

    mdl = props.get("model", {})
    card = mdl.get("cardData", {})

    # pull a description if available, else try meta tag or first <p>
    desc = mdl.get("description") or card.get("description", "")
    if not desc:
        # try the <meta name="description">
        meta = soup.find("meta", {"name": "description"})
        if (meta and meta.get("content")):
            desc = meta["content"]
        else:
            # fallback: first paragraph text
            p = soup.find("p")
            desc = p.get_text(strip=True) if p else ""

    author = props.get("author", {}).get("name", "")
    if author:
        desc = f"{desc}\n\nCredit: {author}"

    # try widget‐based image URLs first
    raw_urls = [w.get("output", {}).get("url") for w in card.get("widget", [])]
    images = []
    for src in raw_urls:
        if isinstance(src, str) and src.strip():
            images.append(src)
    # fallback: scan <img> tags if none found
    if not images:
        parsed = urlparse(source_url)
        model_base = parsed.path.rstrip("/")   # e.g. "/user/ModelName"
        for img in soup.find_all("img"):
            src = img.get("src", "").strip()
            # only include images under the model's directory and with valid extension
            if not src or model_base not in src or 'resolve' not in src:
                continue
            if not any(src.lower().endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif")):
                continue
            # build absolute URL
            full = urljoin(source_url, src)
            images.append(full)
    

    images = images[:5]

    # build result dict
    result = {
        "title": mdl.get("id", ""),
        "description": desc,
        "author": author,
        "tags": card.get("tags", []),
        "location": source_url,
    }
    # only include images if any were found
    if images:
        result["image_urls"] = images
    return result



def extract_pixai_metadata(html_text, source_url):
    soup = BeautifulSoup(html_text, "html.parser")
    image_urls = []

    # Select all <img> elements with the 'object-contain' class (per your JS path)
    for img in soup.select("img.object-contain"):
        # Get either src or lazy-loaded data-src
        src = img.get("data-src") or img.get("src") or ""
        src = src.strip()
        if not src:
            continue

        # Only include PixAI original images
        if src.startswith("https://images-ng.pixai.art/images/orig/") or src.startswith("https://rapi.pixai.art/img/"):
            if src not in image_urls:
                image_urls.append(src)
        # Stop after collecting 5 images
        if len(image_urls) >= 5:
            break

    return {
        "title": soup.title.string.strip() if soup.title else "",
        "description": (soup.find("meta", {"name": "description"}) or {}).get("content", ""),
        "image_urls": image_urls,
        "location": source_url,
        "tags": [],
        "author": "",
    }

def parse_lora_from_hf(url, gemini_api_key):
    resp = requests.get(url, timeout=15)
    if resp.status_code != 200:
        return {"error": "Could not fetch Hugging Face page."}

    # extract image URLs via metadata parser
    meta = extract_hf_metadata(resp.text, url)
    images = meta.get("image_urls", [])

    # raw HTML snippet for LLM context
    prompt_html = resp.text[:12000]

    prompt = (
        "You are a JSON extraction assistant. Given a Hugging Face LoRA model page URL "
        "and its HTML snippet, extract these fields and respond with pure JSON only:\n"
        "- title: concise model title\n"
        "- description: a really powerful description that captivates the reader, leaves them in awe, crediting the author\n"
        "- tags: array of relevant keywords\n"
        "- author: creator’s name\n"
        "- location: the original page URL\n\n"
        "Do NOT extract image URLs—those will be appended automatically.\n\n"
        "Output exactly in this format:\n"
        "{\n"
        '  "title": "...",\n'
        '  "description": "...",\n'
        '  "tags": ["tag1","tag2",...],\n'
        '  "author": "...",\n'
        '  "location": "..."\n'
        "}\n\n"
        f"URL: {url}\nHTML:\n{prompt_html}"
    )

    llm_payload = {"contents": [{"parts": [{"text": prompt}]}]}
    llm_resp = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
        headers={"Content-Type": "application/json"},
        params={"key": gemini_api_key},
        json=llm_payload,
        timeout=30,
    )
    reply = llm_resp.json() \
        .get("candidates", [{}])[0] \
        .get("content", {}) \
        .get("parts", [{}])[0] \
        .get("text", "") \
        .strip()
    try:
        data = pyjson.loads(reply)
    except Exception:
        # regex fallback…
        m = re.search(r"\{.*\}", reply, re.DOTALL)
        if m:
            try:
                data = pyjson.loads(m.group(0))
            except Exception:
                data = {"error": "Failed to parse LLM JSON.", "raw": reply}
        else:
            data = {"error": "Failed to parse LLM JSON.", "raw": reply}

    if images:
        data["image_urls"] = images
    
    data["location"] = url

    return data

@csrf_exempt
def autofill_lora_from_link(request):
    logger = logging.getLogger(__name__)
    if request.method == "POST":
        data = pyjson.loads(request.body)
        lora_url = data.get("url", "").strip()
        parsed = urlparse(lora_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return JsonResponse({"error": "Invalid URL"}, status=400)

        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        if not gemini_api_key:
            return JsonResponse({"error": "Missing API key."}, status=400)

        try:
            resp = requests.get(lora_url, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            return JsonResponse({"error": f"Failed to fetch URL: {e}"}, status=400)

        # Always call Gemini/HF parser first for title/desc/tags
        info = parse_lora_from_hf(lora_url, gemini_api_key)

        # If PixAI domain, override or append images with PixAI-specific URLs
        if "pixai.art" in parsed.netloc:
            pix_meta = extract_pixai_metadata(resp.text, lora_url)
            if pix_meta.get("image_urls"):
                info["image_urls"] = pix_meta["image_urls"]

        return JsonResponse(info)

    return JsonResponse({"error": "Invalid request."}, status=400)
