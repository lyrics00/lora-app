import os
from django.db import models
from django.utils.text import slugify
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
import uuid
from django.contrib.auth import get_user_model
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
User = get_user_model()



def item_image_upload(instance, filename):
    ext = os.path.splitext(filename)[1]
    base = os.path.splitext(filename)[0]
    title_slug = slugify(instance.item.title)
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    # Append a slugified version of the original base name along with timestamp.
    return os.path.join("items", f"{title_slug}_{timestamp}_{slugify(base)}{ext}")

def collection_image_upload(instance, filename):
    ext = os.path.splitext(filename)[1]
    title_slug = slugify(instance.title)
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    return os.path.join("collections", f"{title_slug}_{timestamp}{ext}")

def generate_identifier():
    # Generate an 8-character identifier based on UUID
    return str(uuid.uuid4())[:8]

class Item(models.Model):
    # Define status constants
    CHECKED_IN = 'checked_in'
    IN_CIRCULATION = 'in_circulation'
    BEING_REPAIRED = 'being_repaired'

    STATUS_CHOICES = [
        (CHECKED_IN, 'Checked In'),
        (IN_CIRCULATION, 'In Circulation'),
        (BEING_REPAIRED, 'Being Repaired'),
    ]

    title = models.CharField(max_length=255)
    identifier = models.CharField(max_length=100, unique=True, default=generate_identifier, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=CHECKED_IN)
    location = models.CharField(max_length=255, help_text="e.g., home library, work library")
    description = models.TextField()
    # Removed: image field is no longer necessary
    # image = models.ImageField(upload_to='items/', blank=True, null=True, default="items/default_item_image.png")
    created_at = models.DateTimeField(default=timezone.now)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    # Remove any ForeignKey reference for image as well
    # itemimage = models.ForeignKey('ItemImage', on_delete=models.CASCADE, blank=True, null=True, related_name="item_image")
    librarian = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="items"
    )
    liked_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        blank=True, 
        related_name="liked_items"
    )
    views = models.PositiveIntegerField(default=0)

    def like_count(self):
        return self.liked_by.count()
 # Add a foreign key to LoRAModel
    lora_model = models.ForeignKey(LoRAModel, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.title

class ItemImage(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=item_image_upload, default="items/default_item_image.png")
    
    def delete(self, *args, **kwargs):
        # Delete file from storage unless it is the default.
        if self.image and "default_item_image.png" not in os.path.basename(self.image.name).lower():
            self.image.delete(save=False)
        super().delete(*args, **kwargs)
    
    def save(self, *args, **kwargs):
        # Save the instance without performing cropping.
        super().save(*args, **kwargs)
        
        # After saving, if this is a custom upload, remove any default images for the same item.
        if self.image and "default_item_image.png" not in os.path.basename(self.image.name).lower():
            defaults = ItemImage.objects.filter(item=self.item, image__icontains="default_item_image.png")
            for default_obj in defaults:
                if default_obj.image:
                    default_obj.image.delete(save=False)
                default_obj.delete()
    
    def __str__(self):
        return f"Image for {self.item.title}"

# --- Collection Model ---
class Collection(models.Model):
    PUBLIC = 'public'
    PRIVATE = 'private'
    COLLECTION_TYPE_CHOICES = [
        (PUBLIC, 'Public'),
        (PRIVATE, 'Private'),
    ]
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    collection_type = models.CharField(
        max_length=7,
        choices=COLLECTION_TYPE_CHOICES,
        default=PUBLIC
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='collections'
    )
    # If a collection is private, allowed_users controls access.
    allowed_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='accessible_collections'
    )
    # Direct many-to-many relationship between collections and items.
    items = models.ManyToManyField(
        Item,
        related_name='collections',
        blank=True
    )
    image = models.ImageField(upload_to=collection_image_upload, blank=True, null=True, default="collections/default_collection_image.jpg")
    views = models.PositiveIntegerField(default=0)
    liked_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="liked_collections",
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def like_count(self):
        return self.liked_by.count()
    
    @property
    def comments(self):
        from .models import Comment  # Import here to avoid circular import
        return Comment.objects.filter(collection=self).order_by('-created_at')

    def __str__(self):
        return self.title
    
    @property
    def is_private(self):
        return self.collection_type == self.PRIVATE
    
    def save(self, *args, **kwargs):
        # If image is None or an empty string, set it to default.
        if not self.image:
            self.image = "collections/default_collection_image.jpg"
        super().save(*args, **kwargs)

# --- Comment Model ---
class Comment(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, null=True, blank=True, related_name="comments")
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, null=True, blank=True, related_name="collection_comments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    liked_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='liked_comments', blank=True)

    def like_count(self):
        return self.liked_by.count()

    def __str__(self):
        return f"Comment by {self.user}"
#----LoRA Upload feature:----
class LoRAModel(models.Model):
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='lora_models/')
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lora_models"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

# --- Enforce Private Collection Constraint ---
# When items are added to a collection, if the collection is private,
# the item must not belong to any other collection.
@receiver(m2m_changed, sender=Collection.items.through)
def enforce_private_collection_constraint(sender, instance, action, reverse, model, pk_set, **kwargs):
    if action == "pre_add":
        if instance.collection_type == Collection.PRIVATE:
            for item_pk in pk_set:
                conflicts = model.objects.filter(
                    pk=item_pk,
                    collections__collection_type=Collection.PRIVATE
                ).exclude(collections=instance)
                if conflicts.exists():
                    raise ValidationError(
                        f"Item with pk {item_pk} is already in a private collection and cannot be added."
                    )
        else:
            for item_pk in pk_set:
                conflicts = model.objects.filter(
                    pk=item_pk,
                    collections__collection_type=Collection.PRIVATE
                )
                if conflicts.exists():
                    raise ValidationError(
                        f"Item with pk {item_pk} is in a private collection and cannot be added to another collection."
                    )

from django.conf import settings
from django.db.models import Avg

class ItemRating(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="ratings")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="item_ratings")
    rating = models.PositiveSmallIntegerField()  # e.g., rating 1-5
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.rating} for {self.item.title} by {self.user.username}"

