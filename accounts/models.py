import os
from io import BytesIO
from django.core.files.base import ContentFile
from django.utils.text import slugify
from django.contrib.auth.models import AbstractUser
from django.db import models
from PIL import Image, ImageOps
from django.utils import timezone
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator

def profile_image_upload(instance, filename):
    ext = os.path.splitext(filename)[1]
    username_slug = slugify(instance.username)
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    filename = f"{username_slug}_profile_{timestamp}{ext}"
    return os.path.join("profile_pics", filename)

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    
    ROLE_CHOICES = (
        ("patron", "Patron"),
        ("librarian", "Librarian"),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="patron")
    image = models.ImageField(
        upload_to=profile_image_upload,
        default="profile_pics/default_profile.jpg",
        blank=True,
        null=True
    )
    
    def save(self, *args, **kwargs):
        # If updating an existing user, delete the old image from S3
        # only if the new image is being set and the old image is not the default.
        if self.pk:
            try:
                old_user = CustomUser.objects.get(pk=self.pk)
            except CustomUser.DoesNotExist:
                old_user = None
            if old_user and old_user.image and self.image:
                # Compare file names; delete old file only if different and not default.
                if (old_user.image.name != self.image.name and 
                    "default_profile.jpg" not in os.path.basename(old_user.image.name)):
                    old_user.image.delete(save=False)
        
        # If a new image is uploaded, crop it to a centered square.
        if self.image:
            try:
                self.image.open()
                img = Image.open(self.image)
                # Convert to RGB if necessary.
                if img.mode != "RGB":
                    img = img.convert("RGB")
                # Crop the image if it's not already square.
                if img.width != img.height:
                    min_dim = min(img.width, img.height)
                    img = ImageOps.fit(img, (min_dim, min_dim), method=Image.LANCZOS, centering=(0.5, 0.5))
                    buffer = BytesIO()
                    img.save(buffer, format="JPEG")
                    filebuffer = ContentFile(buffer.getvalue())
                    # Overwrite the current image with the cropped version.
                    self.image.save(self.image.name, filebuffer, save=False)
            except Exception as e:
                # Optionally log the error.
                pass
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.username

class UserRating(models.Model):
    rater = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="given_user_ratings"
    )
    ratee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_user_ratings"
    )
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("rater", "ratee")
        ordering = ["-created_at"]

class UserComment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    profile = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments")
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    liked_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="liked_user_comments",
        blank=True
    )

    @property
    def like_count(self):
        # return the current number of likes for this comment
        return self.liked_by.count()

    def __str__(self):
        return f"Comment by {self.user}"
