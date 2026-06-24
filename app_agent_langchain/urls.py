from django.urls import path
from . import views

app_name = 'app_agent_langchain'

urlpatterns = [
    path('', views.chat_view, name='chat_view'),
    path('api/chat/', views.api_chat, name='api_chat'),
    path('api/clear/', views.api_clear_history, name='api_clear_history'),
]
