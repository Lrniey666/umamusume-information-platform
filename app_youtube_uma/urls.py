from django.urls import path
from . import views

app_name = 'app_youtube_uma'

urlpatterns = [
    path('',           views.dashboard,   name='dashboard'),
    path('api/videos/', views.api_videos,  name='api_videos'),
    path('api/stats/',  views.api_stats,   name='api_stats'),
]
