from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class CollectionAccessRequest(models.Model):
    collection = models.ForeignKey('listings.Collection', on_delete=models.CASCADE, related_name="access_requests_new")
    patron = models.ForeignKey(User, on_delete=models.CASCADE, related_name="access_requests_new")
    created_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)