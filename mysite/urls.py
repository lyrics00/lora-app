"""
URL configuration for mysite project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path

from .views import *

urlpatterns = [
    path("dashboard/", dashboard, name="dashboard"),
    path("accounts/", include("allauth.urls")),
    path("admin/", admin.site.urls),
    path("patron/", patron, name="patron"),
    path("librarian/", librarian, name="librarian"),
    path("choose_role/", choose_role, name="choose_role"),
    path("", home, name='home'),
    path("accounts/settings", settings, name="account_settings"),
    path("accounts/switch_roles", switch_roles, name="account_switch_role"),
    path("accounts/switch_role_librarian", switch_role_librarian, name="switch_role_librarian"),
    path("accounts/switch_role_patron", switch_role_patron, name="switch_role_patron"),
    path("accounts/", include("accounts.urls")),  # Include the accounts app URLs
    path("listings/", include("listings.urls")),  # Include the listings app URLs
    path("patron_requests/", include("patron_requests.urls")),
    path("notifications/", notifications_page, name="notifications_page"),
    path('resource/', include('resource.urls')),
]

