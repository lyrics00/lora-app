from django.urls import path
from . import views

urlpatterns = [
    path("profile/<str:username>/", views.profile, name="profile"),
    path("comment/delete/<int:pk>/", views.user_comment_delete, name="user_comment_delete"),
    path(
        "comment/<int:pk>/like/",
        views.user_like_comment,
        name="user_like_comment"
    ),
    path("profile_edit/", views.profile_edit, name="profile_edit"),
]