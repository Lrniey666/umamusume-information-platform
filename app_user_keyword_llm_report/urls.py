from django.urls import path
from . import views

app_name="app_user_keyword_llm_report"

urlpatterns = [
    path('', views.home, name='home'),
    # API endpoint for getting userkey data including occurrence, time frequency, sentiment analysis, etc.
    path('api_get_userkey_data/', views.api_get_userkey_data, name='api_get_userkey_data'),
    # API endpoint for getting LLM report
    path('api_get_userkey_llm_report/', views.api_get_userkey_llm_report, name='api_get_userkey_llm_report'),
    # AI 新聞（前台 / 後台共用）
    path('api/generate_ai_news/', views.api_generate_ai_news, name='api_generate_ai_news'),
    path('api/model_options/', views.api_ai_news_model_options, name='api_ai_news_model_options'),
    path('api/latest_ai_news/', views.api_latest_ai_news, name='api_latest_ai_news'),
    path('api/admin/news_list/', views.api_ai_news_admin_list, name='api_ai_news_admin_list'),
    path('api/admin/news/<int:news_id>/', views.api_ai_news_detail, name='api_ai_news_detail'),
    path('api/admin/news/<int:news_id>/toggle/', views.api_ai_news_toggle_status, name='api_ai_news_toggle_status'),
    path('api/admin/news/<int:news_id>/delete/', views.api_ai_news_delete, name='api_ai_news_delete'),
]
