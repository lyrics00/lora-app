from django.urls import path
from . import views

urlpatterns = [
    path('lora/', views.lora_resources, name='lora_resources'),
]
