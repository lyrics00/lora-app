from django.urls import path
from . import views
from .views import help_page
from .views import faq_page

urlpatterns = [
    path('lora/', views.lora_resources, name='lora_resources'),
    path('lora/colab-guide/', views.lora_colab_guide, name='lora_colab_guide'),
    path('help/', help_page, name='help_page'),
    path('help/faq/', faq_page, name='faq_page'),
]
