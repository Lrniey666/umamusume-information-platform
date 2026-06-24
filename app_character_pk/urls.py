from django.urls import path
from . import views

app_name = 'app_character_pk'

urlpatterns = [
    path('', views.home, name='home'),
    path('popularity-list/', views.popularity_list, name='popularity_list'),
    path('api_get_character_pk/', views.api_get_character_pk, name='api_get_character_pk'),
]
