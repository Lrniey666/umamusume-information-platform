from django.urls import path
from . import api_views

urlpatterns = [
    path('stats/', api_views.api_stats, name='api_stats'),
    path('announcements/', api_views.api_announcements, name='api_announcements'),
    path('announcements/<int:pk>/', api_views.api_announcement_detail, name='api_announcement_detail'),
    path('analyze/<int:pk>/', api_views.api_analyze, name='api_analyze'),
]
