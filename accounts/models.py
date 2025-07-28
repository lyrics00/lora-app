# Create your models here.
# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ("patron", "Patron"),
        ("librarian", "Librarian"),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="patron")

    def __str__(self):
        return self.username
