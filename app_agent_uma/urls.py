from django.urls import path
from app_agent_uma import views

app_name = 'app_agent_uma'

urlpatterns = [
    path('chat/', views.chat_view, name='chat_view'),
    path('clear-history/', views.clear_history, name='clear_history'),
    path('introduction/', views.poa_agent_introduction, name='poa_agent_introduction'),
]
