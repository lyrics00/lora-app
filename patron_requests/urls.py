from django.urls import path
from . import views

urlpatterns = [
    path("model/<int:pk>/request-access/", views.request_model_access, name="request_model_access"),
    path("librarian/active-model-requests/", views.view_active_model_requests, name="view_active_model_requests"),
    # path("librarian/active-borrow-requests/", views.view_active_borrow_requests, name="view_active_borrow_requests"),
    path("librarian/approve-request/<int:request_id>/", views.approve_model_request, name="approve_model_request"),
    path("librarian/deny-request/<int:request_id>/", views.deny_model_request, name="deny_model_request"),
    path('lora/<int:pk>/borrow_page/', views.borrow_lora_page, name='borrow_lora_page'),
    path("librarian/active-borrow-requests/", views.view_active_borrow_requests, name="view_active_borrow_requests"),
    path("librarian/approve-borrow-request/<int:request_id>/", views.approve_borrow_request, name="approve_borrow_request"),
    path("librarian/deny-borrow-request/<int:request_id>/", views.deny_borrow_request, name="deny_borrow_request"),
    path("active-borrowed-loras/", views.view_active_borrowed_loras, name="view_active_borrowed_loras"),
    path("return/<int:pk>/", views.return_borrowed_lora, name="return_borrowed_lora"),
    path('promote/', views.promote_patron, name='promote_patron'),
]
