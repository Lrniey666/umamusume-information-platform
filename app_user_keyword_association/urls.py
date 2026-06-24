from django.urls import path
from . import views

app_name = 'app_user_keyword_association'

urlpatterns = [
    path('', views.home, name='home'),
    path('api_get_userkey_associate/', views.api_get_userkey_associate, name='api_get_userkey_associate'),
]
