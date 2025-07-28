from django import forms
from .models import LoRA, Model, Comment
from django.contrib.auth import get_user_model
import logging
logger = logging.getLogger(__name__)
User = get_user_model()
class LoRAForm(forms.ModelForm):
    class Meta:
        model = LoRA
        fields = ['title', 'description', 'location']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': "Enter LoRA description..."})
        }

class ModelForm(forms.ModelForm):
    class Meta:
        model = Model
        # Include model_type by default (librarians can choose)
        fields = ['title', 'description', 'model_type', 'image']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        if self.request:
            role = getattr(self.request.user, 'role', '').strip().lower()
            logger.debug("User role: %s", role)
            # If user is a patron, remove the model_type field.
            if role == 'patron':
                self.fields.pop('model_type', None)

    def save(self, commit=True):
        # Create instance without saving
        instance = super().save(commit=False)
        # For patrons, ensure the model type is public.
        if self.request and getattr(self.request.user, 'role', '').strip().lower() == 'patron':
            instance.model_type = Model.PUBLIC
        if commit:
            instance.save()
            self.save_m2m()
        return instance

    
class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3, 'placeholder': "Enter your comment here..."})
        }

class LoRAStatusForm(forms.ModelForm):
    class Meta:
        model = LoRA
        fields = ['status']


class BorrowLoRAForm(forms.Form):
    borrow_duration = forms.IntegerField(
        min_value=1,
        label="Borrow Duration (Days)",
        help_text="Enter the number of days you wish to borrow this LoRA."
    )