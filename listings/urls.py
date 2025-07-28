from django.urls import path

from . import views

urlpatterns = [
    path("", views.model_list, name="model_list"),
    path("lora/create/", views.listing_create, name="lora_create"),
    path("my-loras/", views.my_loras, name="my_listings"),
    path("<int:pk>/", views.listing_detail, name="listing_detail"),
    path("delete/<int:pk>/", views.lora_delete, name="lora_delete"),
    path("comment/delete/<int:pk>/", views.comment_delete, name="comment_delete"),
    path("like/<int:pk>/", views.like_listing, name="like_listing"),
    path("comment/<int:pk>/like/", views.like_comment, name="like_comment"),
    path("model/<int:pk>/", views.model_detail, name="model_detail"),
    path("model/create/", views.model_create, name="model_create"),
    path("model/<int:pk>/delete/", views.model_delete, name="model_delete"),
    path("model/<int:pk>/edit/", views.model_edit, name="model_edit"),
    path(
        "model/<int:model_pk>/add-lora/<int:lora_pk>/",
        views.model_add_lora,
        name="model_add_lora",
    ),
    path(
        "model/<int:model_pk>/remove-lora/<int:lora_pk>/",
        views.model_remove_lora,
        name="model_remove_lora",
    ),
    path("model/<int:pk>/loras/", views.model_loras, name="model_loras"),
    path("model/<int:pk>/like/", views.like_model, name="like_model"),
    path(
        "model/<int:pk>/lora-search/",
        views.model_search_loras,
        name="model_lora_search",
    ),
    path(
        "model/<int:pk>/create-lora/", views.model_create_lora, name="model_create_lora"
    ),
    path(
        "model/<int:pk>/select-users/",
        views.select_allowed_users,
        name="select_allowed_users",
    ),
    # path('collection/<int:pk>/create-item/', views.collection_create_item, name='collection_create_item'),
    path("lora-search/", views.lora_search, name="lora_search"),
    path("lora/<int:pk>/edit", views.lora_edit, name="lora_edit"),
    path("lora/<int:pk>/edit-status/", views.lora_edit_status, name="lora_edit_status"),
    path(
        "lora/image/<int:pk>/delete/", views.delete_lora_image, name="delete_lora_image"
    ),
    path("lora/<int:pk>/rate/", views.rate_lora, name="rate_lora"),
]

