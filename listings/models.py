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
User = get_user_model()

def item_image_upload(instance, filename):
    ext = os.path.splitext(filename)[1]
    title_slug = slugify(instance.item.title)
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    return os.path.join("items", f"{title_slug}_{timestamp}{ext}")

def generate_identifier():
    # Generate an 8-character identifier based on UUID
    return str(uuid.uuid4())[:8]

# --- Item Model ---
class Item(models.Model):
    STATUS_CHOICES = [
        ('checked_in', 'Checked In'),
        ('in_circulation', 'In Circulation'),
        ('being_repaired', 'Being Repaired'),
    ]

    title = models.CharField(max_length=255)
    identifier = models.CharField(max_length=100, unique=True, default=generate_identifier, null=True)  # now has a default
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='checked_in')
    location = models.CharField(max_length=255, help_text="e.g., home library, work library")
    description = models.TextField()
    image = models.ImageField(upload_to='items/', blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)

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
    
    @property
    def in_private_collection(self):
        """
        Returns True if the item is in any private collection.
        """
        return self.collections.filter(collection_type=Collection.PRIVATE).exists()
    
    @property
    def in_any_collection(self):
        """
        Returns True if the item belongs to any collection.
        """
        return self.collections.exists()
    
    def __str__(self):
        return self.title

# Optional model if you want to support multiple images per item.
class ItemImage(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=item_image_upload)
    uploaded_at = models.DateTimeField(auto_now_add=True)

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
    image = models.ImageField(upload_to="collections/", blank=True, null=True)
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

# --- Enforce Private Collection Constraint ---
# When items are added to a collection, if the collection is private,
# the item must not belong to any other collection.
@receiver(m2m_changed, sender=Collection.items.through)
def enforce_private_collection_constraint(sender, instance, action, reverse, model, pk_set, **kwargs):
    """
    If instance is a Collection and has type private, ensure that any added item is not
    in any other collection. Also, if an item is already in any private collection, raise error.
    """
    if action == "pre_add":
        # When adding items to a collection...
        if instance.collection_type == Collection.PRIVATE:
            for item_pk in pk_set:
                # Check if this item already belongs to any collection
                conflicts = model.objects.filter(pk=item_pk,
                    collections__collection_type=Collection.PRIVATE
                ).exclude(collection=instance)
                if conflicts.exists():
                    raise ValidationError(
                        f"Item with pk {item_pk} is already in a private collection and cannot be added."
                    )
        else:
            # Even in a public collection, if an item belongs to a private collection already, disallow adding.
            for item_pk in pk_set:
                conflicts = model.objects.filter(pk=item_pk,
                    collections__collection_type=Collection.PRIVATE
                )
                if conflicts.exists():
                    raise ValidationError(
                        f"Item with pk {item_pk} is in a private collection and cannot be added to another collection."
                    )
                
