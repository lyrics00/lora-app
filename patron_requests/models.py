from django.db import models
from django.contrib.auth import get_user_model
from listings.models import Item
from django.conf import settings

User = get_user_model()

class CollectionAccessRequest(models.Model):
    collection = models.ForeignKey('listings.Collection', on_delete=models.CASCADE, related_name="access_requests_new")
    patron = models.ForeignKey(User, on_delete=models.CASCADE, related_name="access_requests_new")
    created_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)
    archived = models.BooleanField(default=False, null=True)  # New field to mark archived requests

    def __str__(self):
        return f"Access request for {self.collection} by {self.patron}"

    class Meta:
        ordering = ['-created_at']


class BorrowRequest(models.Model):
    PENDING = 'pending'
    APPROVED = 'approved'
    DENIED = 'denied'
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (DENIED, 'Denied'),
    ]
    
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="borrow_requests")
    patron = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="borrow_requests")
    duration = models.PositiveIntegerField(help_text="Duration in days")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"BorrowRequest: {self.patron.username} - {self.item.title} ({self.duration} days) [{self.status}]"