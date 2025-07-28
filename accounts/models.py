# Create your models here.
# accounts/models.py
from allauth.account.utils import user_username
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.files.storage import default_storage

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ("patron", "Patron"),
        ("librarian", "Librarian"),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="patron")
    profile_picture = models.ImageField(storage=S3Boto3Storage(), upload_to='profile_pictures/', blank=True, null=True)

    def __str__(self):
        return self.username


