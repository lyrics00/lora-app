from django.urls import path
from .views import profile_edit

urlpatterns = [
    path('profile/', profile_edit, name='account_profile_edit'),
    # ... any other patterns
]