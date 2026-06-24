from django.urls import path
from . import views

app_name = 'app_comment_sentiment'

urlpatterns = [
    # 儀表板頁面（C1）
    path('', views.dashboard, name='dashboard'),
    path('api/data/', views.api_data, name='api_data'),
    # 排程控制 API（原有）
    path('api/status/', views.api_scheduler_status, name='api_scheduler_status'),
    path('api/start/', views.api_scheduler_start, name='api_scheduler_start'),
    path('api/stop/', views.api_scheduler_stop, name='api_scheduler_stop'),
    path('api/run_task/', views.api_run_task, name='api_run_task'),
    path('api/history/', views.api_scheduler_history, name='api_scheduler_history'),
]
