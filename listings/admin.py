from django.contrib import admin

from .models import Model, Comment, LoRA, LoRAImage, LoRARating


class LoRAImageInline(admin.TabularInline):
    model = LoRAImage
    extra = 1


class LoRACommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    fields = ("user", "comment", "created_at")
    readonly_fields = ("created_at",)
    fk_name = "lora"
    verbose_name = "LoRA Comment"
    verbose_name_plural = "LoRA Comments"


class LoRARatingInline(admin.TabularInline):
    model = LoRARating
    extra = 0
    readonly_fields = ("user", "rating", "created_at")
    can_delete = False
    max_num = 0
    verbose_name = "LoRA Rating"
    verbose_name_plural = "LoRA Ratings"


@admin.register(LoRA)
class LoRAAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "identifier",
        "status",
        "location",
        "rating",
        "librarian",
        "created_at",
    )
    list_filter = ("status", "librarian", "created_at")
    search_fields = ("title", "description", "identifier")
    readonly_fields = ("rating", "views", "created_at")
    inlines = [LoRAImageInline, LoRACommentInline, LoRARatingInline]
    filter_horizontal = ("liked_by",)


class ModelCommentInline(admin.TabularInline):
    model = Comment
    extra = 0
    fields = ("user", "comment", "created_at")
    readonly_fields = ("created_at",)
    fk_name = "model"
    verbose_name = "Model Comment"
    verbose_name_plural = "Model Comments"


@admin.register(Model)
class ModelAdmin(admin.ModelAdmin):
    list_display = ("title", "model_type", "creator", "created_at", "views")
    list_filter = ("model_type", "creator", "created_at")
    search_fields = ("title", "description")
    readonly_fields = ("views", "created_at")
    filter_horizontal = ("loras", "allowed_users", "liked_by")
    inlines = [ModelCommentInline]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("user", "comment_preview", "lora_or_model", "created_at")
    list_filter = ("created_at", "user")
    search_fields = ("comment", "user__username")
    readonly_fields = ("created_at",)
    filter_horizontal = ("liked_by",)

    def comment_preview(self, obj):
        return obj.comment[:50] + "..." if len(obj.comment) > 50 else obj.comment

    comment_preview.short_description = "Comment"

    def lora_or_model(self, obj):
        if obj.lora:
            return f"LoRA: {obj.lora.title}"
        elif obj.model:
            return f"Model: {obj.model.title}"
        return "None"

    lora_or_model.short_description = "Target"


@admin.register(LoRARating)
class LoRARatingAdmin(admin.ModelAdmin):
    list_display = ("lora", "user", "rating", "created_at")
    list_filter = ("rating", "created_at")
    search_fields = ("lora__title", "user__username")
    readonly_fields = ("created_at",)
