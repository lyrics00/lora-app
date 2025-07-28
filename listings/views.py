from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Listing, Comment
from .forms import ListingForm, CommentForm
from django.core.exceptions import PermissionDenied

def listing_list(request):
    listings = Listing.objects.all()
    return render(request, "listing_list.html", {"listings": listings})

@login_required
def listing_create(request):
    if request.method == "POST":
        form = ListingForm(request.POST, request.FILES)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.librarian = request.user  # track creator info here
            listing.save()
            return redirect("listing_list")
    else:
        form = ListingForm()
    return render(request, "listing_create.html", {"form": form})

def listing_detail(request, pk):
    listing = get_object_or_404(Listing, pk=pk)
    comments = listing.comments.all().order_by('-created_at')
    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect("account_login")
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.listing = listing
            new_comment.user = request.user
            new_comment.save()
            return redirect("listing_detail", pk=listing.pk)
    else:
        comment_form = CommentForm()

    context = {
        "listing": listing,
        "comments": comments,
        "comment_form": comment_form,
    }
    return render(request, "listing_detail.html", context)

@login_required
def my_listings(request):
    if request.user.role != "librarian":
        return redirect("listing_list")
    listings = Listing.objects.filter(librarian=request.user)
    return render(request, "my_listings.html", {"listings": listings})

@login_required
def listing_delete(request, pk):
    listing = get_object_or_404(Listing, pk=pk, librarian=request.user)
    if request.method == "POST":
        listing.delete()
        return redirect("my_listings")
    return render(request, "listing_confirm_delete.html", {"listing": listing})

@login_required
def comment_delete(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    # Only allow deletion if the logged in user is the owner of the comment.
    if comment.user != request.user:
        raise PermissionDenied("You are not allowed to delete this comment.")
    listing_pk = comment.listing.pk  # store listing pk to redirect after deletion
    comment.delete()
    return redirect("listing_detail", pk=listing_pk)