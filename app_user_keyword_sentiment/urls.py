from django.urls import path

from . import views

app_name="app_user_keyword_sentiment"

urlpatterns = [

    path('', views.home, name='home'),
    # 本地端處理資料
    path('api_get_userkey_sentiment/', views.api_get_userkey_sentiment),
    path('api_get_userkey_sentiment_from_remote_api_through_backend/', views.api_get_userkey_sentiment_from_remote_api_through_backend),

]
