from django.urls import path
from . import views

app_name = 'app_discord_bot'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('api/stats/', views.api_stats, name='api_stats'),
    path('api/trigger_news/', views.api_trigger_news, name='api_trigger_news'),
    path('api/channels/add/', views.api_channel_add, name='api_channel_add'),
    path('api/channels/<int:pk>/delete/', views.api_channel_delete, name='api_channel_delete'),
    path('api/channels/<int:pk>/toggle/', views.api_channel_toggle, name='api_channel_toggle'),
]
