from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models

from listings.models import LoRA

User = get_user_model()


class ModelAccessRequest(models.Model):
    model = models.ForeignKey(
        "listings.Model", on_delete=models.CASCADE, related_name="access_requests_new"
    )
    patron = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="access_requests_new"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)
    archived = models.BooleanField(
        default=False, null=True
    )  # New field to mark archived requests

    def __str__(self):
        return f"Access request for {self.model} by {self.patron}"

    class Meta:
        ordering = ["-created_at"]


class BorrowRequest(models.Model):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (APPROVED, "Approved"),
        (DENIED, "Denied"),
    ]

    lora = models.ForeignKey(
        LoRA, on_delete=models.CASCADE, related_name="borrow_requests", null=True
    )

    patron = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="borrow_requests",
    )
    duration = models.DurationField(
        help_text="Exact borrowing duration (e.g., 1 day, 2:30:00)"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        title = self.lora.title if self.lora else "Unknown"
        return f"BorrowRequest: {self.patron.username} - {title} ({self.duration} days) [{self.status}]"


class BorrowedLoRA(models.Model):
    borrow_request = models.OneToOneField(
        "BorrowRequest", on_delete=models.CASCADE, related_name="borrowed_lora"
    )
    lora = models.ForeignKey(
        LoRA, on_delete=models.CASCADE, related_name="borrowed_instances"
    )
    patron = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="borrowed_loras",
    )
    start_date = models.DateTimeField(auto_now_add=True)
    duration = models.DurationField(
        help_text="Duration (e.g., '1 day, 2:30:00' for 1 day, 2 hours, and 30 minutes)"
    )
    reminder_sent = models.BooleanField(default=False)
    returned_at = models.DateTimeField(
        null=True, blank=True
    )  # new field for logging returns

    @property
    def due_date(self):
        return self.start_date + self.duration

    def __str__(self):
        return f"{self.lora.title} borrowed by {self.patron.username}"
