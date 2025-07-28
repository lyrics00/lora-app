import os
from django.utils.text import slugify
from django.contrib.auth.models import AbstractUser
from django.db import models


def profile_image_upload(instance, filename):
    ext = os.path.splitext(filename)[1]
    username_slug = slugify(instance.username)
    # Optionally add a timestamp for uniqueness
    from django.utils import timezone
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f"{username_slug}_profile_{timestamp}{ext}"
    return os.path.join("profile_pics", filename) 
class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ("patron", "Patron"),
        ("librarian", "Librarian"),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="patron")
    image = models.ImageField(upload_to=profile_image_upload, default="profile_pics/default_profile.jpg", blank=True, null=True)
    def __str__(self):
        return self.username
