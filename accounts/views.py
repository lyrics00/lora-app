from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .forms import ProfileEditForm
from django.conf import settings  # if needed for the default image
from django.contrib import messages
from django.db.models import Avg, Q
from listings.models import LoRA, Model
from .forms import UserRatingForm, UserProfileCommentForm
from .models import UserRating
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from .models import UserComment
from django.http import JsonResponse
from django.db.models import Count
import notifications as notify
from .models import UserComment
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.core.exceptions import PermissionDenied

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

@login_required
def profile_edit(request):
    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            profile = form.save(commit=False)
            # Check for the "clear" action or empty file
            if 'image-clear' in request.POST:
                profile.image = 'profile_pics/default_profile.jpg'
            profile.save()
            return redirect('profile', request.user)  # Adjust redirect as needed
    else:
        form = ProfileEditForm(instance=request.user)
    return render(request, 'profile_edit.html', {'form': form})

def profile(request, username):
    User = get_user_model()
    profile_user = get_object_or_404(User, username=username)
    lora_no_models = filter_private_loras(LoRA.objects.filter(librarian=profile_user))
    lora_no_models = lora_no_models.annotate(model_count=Count('models')).filter(model_count=0)
    # 1) Accessible LoRAs based on role:
    loras = LoRA.objects.filter(librarian=profile_user)
    if request.user.role != "librarian":
        if request.user.is_authenticated:
            # patrons see LoRAs that are checked in,
            # in public models, in models they can access, or have no models
            loras = loras.filter(
                Q(models__model_type=Model.PUBLIC) |
                Q(models__allowed_users=request.user) |
                Q(status=LoRA.CHECKED_IN) |
                Q(pk__in=lora_no_models.values_list('pk', flat=True))
            ).distinct()
        else:
            # anonymous sees only checked‑in LoRAs or those with no models
            public = loras.filter(models__model_type=Model.PUBLIC)
            loras = (public | lora_no_models).distinct()

    # 2) Accessible Models based on role:
    models = Model.objects.filter(creator=profile_user)
    if request.user.role != "librarian":
        if request.user.is_authenticated:
            models = models.filter(
                Q(model_type=Model.PUBLIC) |
                Q(allowed_users=request.user)
            ).distinct()
        else:
            models = models.filter(model_type=Model.PUBLIC)

    ratings_qs = UserRating.objects.filter(ratee=profile_user)
    avg_rating = ratings_qs.aggregate(avg=Avg("rating"))["avg"] or 0

    if request.method == "POST" and "rating" in request.POST:
        form = UserRatingForm(request.POST)
        if form.is_valid():
            UserRating.objects.update_or_create(
                rater=request.user,
                ratee=profile_user,
                defaults={"rating": form.cleaned_data["rating"]}
            )
            # Recalculate after saving
            avg_rating = UserRating.objects.filter(ratee=profile_user).aggregate(avg=Avg("rating"))["avg"] or 0
            messages.success(request, "Your rating has been submitted.")
            return redirect("profile", username=profile_user.username)
    else:
        form = UserRatingForm()

    # Handle comment POST (if you want comments on profiles)
    comment_form = UserProfileCommentForm()
    if request.method == "POST" and "comment" in request.POST:
        comment_form = UserProfileCommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.user = request.user
            comment.profile = profile_user  # Add a ForeignKey to profile in your Comment model if needed
            comment.save()
            messages.success(request, "Comment added.")
            return redirect("profile", username=profile_user.username)

    comments = UserComment.objects.filter(profile=profile_user).order_by("-created_at")  # if you add profile FK

    return render(request, "profile.html", {
        "profile_user": profile_user,
        "loras": loras,
        "models": models,
        "avg_rating": avg_rating,
        "form": form,
        "comment_form": comment_form,
        "comments": comments,
    })

@login_required
def user_comment_delete(request, pk):
    comment = get_object_or_404(UserComment, pk=pk)
    if comment.user != request.user or request.user.role != "librarian":
        raise PermissionDenied("You are not allowed to delete this comment.")
    profile_username = comment.profile.username
    comment.delete()
    if request.user.role == "librarian":
        notify.send(
            request.user,
            recipient=comment.user,
            verb="Your comment was deleted by a librarian in the profile of",
            target=comment,
        )
    messages.success(request, "Comment deleted.")
    return redirect("profile", username=profile_username)

@login_required
def user_like_comment(request, pk):
    """
    Toggle a like on a UserComment via AJAX.
    Returns JSON: { like_count: int, liked: bool }
    """
    comment = get_object_or_404(UserComment, pk=pk)
    user = request.user

    if user in comment.liked_by.all():
        comment.liked_by.remove(user)
        liked = False
    else:
        comment.liked_by.add(user)
        liked = True

    return JsonResponse({
        "like_count": comment.liked_by.count(),
        "liked": liked
    })