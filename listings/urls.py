from django.urls import path
from . import views

urlpatterns = [
    path("", views.collection_list, name="collection_list"),
    path("ítem/create/", views.listing_create, name="listing_create"),
    path("my-listings/", views.my_listings, name="my_listings"),
    path("<int:pk>/", views.listing_detail, name="listing_detail"),
    path("delete/<int:pk>/", views.item_delete, name="item_delete"),
    path("comment/delete/<int:pk>/", views.comment_delete, name="comment_delete"),
    path('like/<int:pk>/', views.like_listing, name="like_listing"),
    path('comment/<int:pk>/like/', views.like_comment, name='like_comment'),
    path("collection/<int:pk>/", views.collection_detail, name="collection_detail"),
    path("collection/create/", views.collection_create, name="collection_create"),
    path("collection/<int:pk>/delete/", views.collection_delete, name="collection_delete"),
    path("collection/<int:pk>/edit/", views.collection_edit, name="collection_edit"),
    path('collection/<int:collection_pk>/add-item/<int:item_pk>/', views.collection_add_item, name='collection_add_item'),
    path("collection/<int:collection_pk>/remove-item/<int:item_pk>/", views.collection_remove_item, name="collection_remove_item"),
    path("collection/<int:pk>/items/", views.collection_items, name="collection_items"),
    path("collection/<int:pk>/like/", views.like_collection, name="like_collection"),
    path("collection/<int:pk>/item-search/", views.collection_search_items, name="collection_item_search"),
    path("collection/<int:pk>/create-item/", views.collection_create_item, name="collection_create_item"),
    path('collection/<int:pk>/select-users/', views.select_allowed_users, name='select_allowed_users'),
    path('item-search/', views.item_search, name='item_search'),
    path('item/<int:pk>/edit', views.item_edit, name='item_edit'),
    path('item/<int:pk>/edit-status/', views.item_edit_status, name='item_edit_status'),
    path('item/image/<int:pk>/delete/', views.delete_item_image, name='delete_item_image'),
    path("listing/<int:pk>/rate/", views.rate_item, name="rate_item"),
]