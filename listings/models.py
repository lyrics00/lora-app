import os
from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from django.conf import settings

import os
from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from django.conf import settings

def listing_image_upload(instance, filename):
    ext = os.path.splitext(filename)[1]
    title_slug = slugify(instance.title)
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    return os.path.join("listings", f"{title_slug}_{timestamp}{ext}")

class Listing(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    image = models.ImageField(upload_to=listing_image_upload)
    created_at = models.DateTimeField(auto_now_add=True)
    # Link the listing to the librarian (CustomUser)
    # After change in your Listing model
    librarian = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listings",
        null=True  # allow null for existing rows
    )

    def __str__(self):
        return self.title

class Comment(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.username} on {self.listing.title}"