from django.urls import path
from app_uma_top_character import views

app_name = 'app_uma_top_character'

urlpatterns = [
    path('', views.home, name='home'),
    path('api_get_topCharacter/', views.api_get_topCharacter, name='api_topCharacter'),
]
