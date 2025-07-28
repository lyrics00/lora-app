from allauth.account.forms import SignupForm
from django import forms
from django.contrib.auth import get_user_model
import re
User = get_user_model()
class CustomSignupForm(SignupForm):
    ROLE_CHOICES = (
        ("librarian", "Librarian"),
        ("patron", "Patron"),
    )
    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.RadioSelect, label="Select your role")

    def save(self, request):
        user = super().save(request)
        user.role = self.cleaned_data["role"]
        user.email = self.cleaned_data.get("email", "")  # Make sure the email is assigned
        user.save()
        return user
    


User = get_user_model()

class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'image']
        labels = {
            'username': 'Username',
            'image': 'Profile Image',
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username and not re.match(r'^[A-Za-z0-9]+$', username):
            raise forms.ValidationError("Username must contain only letters and digits.")
        return username

from .models import UserRating

class UserRatingForm(forms.ModelForm):
    class Meta:
        model = UserRating
        fields = ["rating"]
        widgets = {
            "rating": forms.NumberInput(attrs={"min":1, "max":5, "class":"form-control"})
        }

from .models import UserComment

class UserProfileCommentForm(forms.ModelForm):
    class Meta:
        model = UserComment
        fields = ["comment"]  # <-- use 'comment', not 'text'
        widgets = {
            "comment": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Leave a comment about this user..."
            }),
        }
        labels = {
            "comment": "",
        }