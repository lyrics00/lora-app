from django.contrib import admin
from .models import ModelAccessRequest, BorrowRequest, BorrowedLoRA

@admin.register(ModelAccessRequest)
class ModelAccessRequestAdmin(admin.ModelAdmin):
    list_display = ('model', 'patron', 'created_at', 'approved', 'archived')
    list_filter = ('approved', 'archived', 'created_at')
    search_fields = ('model__title', 'patron__username')

@admin.register(BorrowRequest)
class BorrowRequestAdmin(admin.ModelAdmin):
    # Drop non‑existent fields and show only real attributes
    list_display = ('lora', 'patron', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('lora__title', 'patron__username')

@admin.register(BorrowedLoRA)
class BorrowedLoRAAdmin(admin.ModelAdmin):
    # Align with actual model fields
    list_display = ('lora', 'patron', 'start_date', 'returned_at')
    list_filter = ('start_date', 'returned_at')
    search_fields = ('lora__title', 'patron__username')
