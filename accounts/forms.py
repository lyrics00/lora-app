from allauth.account.forms import SignupForm
from django import forms

class CustomSignupForm(SignupForm):
    ROLE_CHOICES = (
        ("librarian", "Librarian"),
        ("patron", "Patron"),
    )
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.RadioSelect,  
        label="Select your role"
    )

    def save(self, request):
        user = super().save(request)
        # Assuming your User model has a 'role' attribute
        user.role = self.cleaned_data["role"]
        user.save()
        return user