from django import forms
from django.utils import timezone

class BorrowLoRAForm(forms.Form):
    due_date = forms.DateTimeField(
        label="Due Date & Time",
        widget=forms.DateTimeInput(
            attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }
        ),
        help_text="Select the due date and time for returning the LoRA (e.g., 2025-04-05T14:30)"
    )

    def clean_due_date(self):
        due_date = self.cleaned_data.get("due_date")
        errors = []
        if not due_date:
            errors.append("This field is required.")
        else:
            now = timezone.now()
            if due_date <= now:
                errors.append("Due date must be in the future.")
        if errors:
            raise forms.ValidationError(errors)
        return due_date