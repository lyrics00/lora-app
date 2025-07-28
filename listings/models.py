import os
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import slugify

User = get_user_model()


def lora_image_upload(instance, filename):
    ext = os.path.splitext(filename)[1]
    base = os.path.splitext(filename)[0]
    title_slug = slugify(instance.lora.title)
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    return os.path.join("items", f"{title_slug}_{timestamp}_{slugify(base)}{ext}")


def model_image_upload(instance, filename):
    ext = os.path.splitext(filename)[1]
    title_slug = slugify(instance.title)
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    return os.path.join("collections", f"{title_slug}_{timestamp}{ext}")


def generate_identifier():
    # Generate an 8-character identifier based on UUID
    return str(uuid.uuid4())[:8]


class LoRA(models.Model):
    # Define status constants
    CHECKED_IN = "checked_in"
    IN_CIRCULATION = "in_circulation"
    BEING_REPAIRED = "being_repaired"

    STATUS_CHOICES = [
        (CHECKED_IN, "Checked In"),
        (IN_CIRCULATION, "In Circulation"),
        (BEING_REPAIRED, "Being Repaired"),
    ]

    title = models.CharField(max_length=255)
    identifier = models.CharField(
        max_length=100, unique=True, default=generate_identifier, null=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=CHECKED_IN)
    location = models.CharField(
        max_length=255, help_text="e.g., home library, work library"
    )
    description = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)
    librarian = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="loras"
    )
    liked_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="liked_loras"
    )
    views = models.PositiveIntegerField(default=0)

    def like_count(self):
        return self.liked_by.count()

    def __str__(self):
        return self.title


class LoRAImage(models.Model):
    lora = models.ForeignKey(LoRA, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(
        upload_to=lora_image_upload, default="items/default_item_image.png"
    )

    def delete(self, *args, **kwargs):
        # Delete file from storage unless it is the default.
        if (
            self.image
            and "default_item_image.png"
            not in os.path.basename(self.image.name).lower()
        ):
            self.image.delete(save=False)
        super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        # Save the instance without performing cropping.
        super().save(*args, **kwargs)

        # After saving, if this is a custom upload, remove any default images for the same lora.
        if (
            self.image
            and "default_item_image.png"
            not in os.path.basename(self.image.name).lower()
        ):
            defaults = LoRAImage.objects.filter(
                lora=self.lora, image__icontains="default_item_image.png"
            )
            for default_obj in defaults:
                if default_obj.image:
                    default_obj.image.delete(save=False)
                default_obj.delete()

    def __str__(self):
        return f"Image for {self.lora.title}"


# --- Model Model ---
class Model(models.Model):
    PUBLIC = "public"
    PRIVATE = "private"
    MODEL_TYPE_CHOICES = [
        (PUBLIC, "Public"),
        (PRIVATE, "Private"),
    ]
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    model_type = models.CharField(
        max_length=7, choices=MODEL_TYPE_CHOICES, default=PUBLIC
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="models"
    )
    # If a model is private, allowed_users controls access.
    allowed_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="accessible_models"
    )
    # Direct many-to-many relationship between models and loras.
    loras = models.ManyToManyField(LoRA, related_name="models", blank=True)
    image = models.ImageField(
        upload_to=model_image_upload,
        blank=True,
        null=True,
        default="collections/default_collection_image.jpg",
    )
    views = models.PositiveIntegerField(default=0)
    liked_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="liked_models", blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def like_count(self):
        return self.liked_by.count()

    @property
    def comments(self):
        from .models import Comment  # Import here to avoid circular import

        return Comment.objects.filter(model=self).order_by("-created_at")

    def __str__(self):
        return self.title

    @property
    def is_private(self):
        return self.model_type == self.PRIVATE

    def save(self, *args, **kwargs):
        # If image is None or an empty string, set it to default.
        if not self.image:
            self.image = "collections/default_collection_image.jpg"
        super().save(*args, **kwargs)


# --- Comment Model ---
class Comment(models.Model):
    lora = models.ForeignKey(
        LoRA, on_delete=models.CASCADE, null=True, blank=True, related_name="comments"
    )
    model = models.ForeignKey(
        Model,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="model_comments",
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    liked_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="liked_comments", blank=True
    )

    def like_count(self):
        return self.liked_by.count()

    def __str__(self):
        return f"Comment by {self.user}"


# --- Enforce Private Model Constraint ---
# When loras are added to a model, if the model is private,
# the lora must not belong to any other model.
@receiver(m2m_changed, sender=Model.loras.through)
def enforce_private_model_constraint(
    sender, instance, action, reverse, model, pk_set, **kwargs
):
    if action == "pre_add":
        if instance.model_type == Model.PRIVATE:
            for lora_pk in pk_set:
                conflicts = model.objects.filter(
                    pk=lora_pk, models__model_type=Model.PRIVATE
                ).exclude(models=instance)
                if conflicts.exists():
                    raise ValidationError(
                        f"LoRA with pk {lora_pk} is already in a private model and cannot be added."
                    )
        else:
            for lora_pk in pk_set:
                conflicts = model.objects.filter(
                    pk=lora_pk, models__model_type=Model.PRIVATE
                )
                if conflicts.exists():
                    raise ValidationError(
                        f"LoRA with pk {lora_pk} is in a private model and cannot be added to another model."
                    )


class LoRARating(models.Model):
    lora = models.ForeignKey(LoRA, on_delete=models.CASCADE, related_name="ratings")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lora_ratings"
    )
    rating = models.PositiveSmallIntegerField()  # e.g., rating 1-5
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.rating} for {self.lora.title} by {self.user.username}"
