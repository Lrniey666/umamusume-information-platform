from django.urls import path
from . import views

app_name = 'app_user_keyword_db'

urlpatterns = [
    path('', views.home, name='home'),
    path('api_get_userkey_data/', views.api_get_userkey_data, name='api_get_userkey_data'),
    path('api_source_stats/',     views.api_source_stats,     name='api_source_stats'),
]
