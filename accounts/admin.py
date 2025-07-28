from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, UserRating, UserComment


class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + ((None, {"fields": ("role",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + ((None, {"fields": ("role",)}),)
    list_display = ("username", "email", "first_name", "last_name", "role", "is_staff")


admin.site.register(CustomUser, CustomUserAdmin)

@admin.register(UserRating)
class UserRatingAdmin(admin.ModelAdmin):
    list_display = ('rater', 'ratee', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('rater__username', 'ratee__username')

@admin.register(UserComment)
class UserCommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'profile', 'comment_preview', 'created_at')
    list_filter = ('created_at', 'user')
    search_fields = ('comment', 'user__username')
    readonly_fields = ('created_at',)
    filter_horizontal = ('liked_by',)

    def comment_preview(self, obj):
        return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
    comment_preview.short_description = "Comment"