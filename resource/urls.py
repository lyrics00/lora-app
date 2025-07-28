from django.urls import path
from . import views
from .views import gettingstarted_page
from .views import faq_page

urlpatterns = [
    path('lora/', views.lora_resources, name='lora_resources'),
    path('lora/colab-guide/', views.lora_colab_guide, name='lora_colab_guide'),
    path('resources/gettingstarted/', views.gettingstarted_page, name='gettingstarted_page'),
    path('resources/faq/', views.faq_page, name='faq_page'),
    path('resources/help/', views.help_page, name='help_page'),
    path('lora/dataset-guide/', views.dataset_guide, name='dataset_guide'),
    path('lora/tuning-guide/', views.tuning_guide, name='tuning_guide'),

]
