from django.urls import path
from . import views

urlpatterns = [
    path("collection/<int:pk>/request-access/", views.request_collection_access, name="request_collection_access"),
    path("librarian/active-collection-requests/", views.view_active_collection_requests, name="view_active_collection_requests"),
    # path("librarian/active-borrow-requests/", views.view_active_borrow_requests, name="view_active_borrow_requests"),
    path("librarian/approve-request/<int:request_id>/", views.approve_collection_request, name="approve_collection_request"),
    path("librarian/deny-request/<int:request_id>/", views.deny_collection_request, name="deny_collection_request"),
    path('item/<int:pk>/borrow_page/', views.borrow_item_page, name='borrow_item_page'),
    path("librarian/active-borrow-requests/", views.view_active_borrow_requests, name="view_active_borrow_requests"),
    path("librarian/approve-borrow-request/<int:request_id>/", views.approve_borrow_request, name="approve_borrow_request"),
    path("librarian/deny-borrow-request/<int:request_id>/", views.deny_borrow_request, name="deny_borrow_request"),
]
