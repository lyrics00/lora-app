from django.urls import path
from . import views

urlpatterns = [
    path("", views.listing_list, name="listing_list"),
    path("create/", views.listing_create, name="listing_create"),
    path("my-listings/", views.my_listings, name="my_listings"),
    path("<int:pk>/", views.listing_detail, name="listing_detail"),
    path("delete/<int:pk>/", views.listing_delete, name="listing_delete"),\
    path("comment/delete/<int:pk>/", views.comment_delete, name="comment_delete"),
]