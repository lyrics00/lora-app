from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + ((None, {"fields": ("role",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + ((None, {"fields": ("role",)}),)
    list_display = ("username", "email", "first_name", "last_name", "role", "is_staff")


admin.site.register(CustomUser, CustomUserAdmin)
