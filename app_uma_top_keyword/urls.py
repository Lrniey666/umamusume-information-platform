from django.urls import path
from app_uma_top_keyword import views

app_name = 'app_uma_top_keyword'

urlpatterns = [
    path('', views.home, name='home'),
    path('api_get_cate_topword/', views.api_get_cate_topword, name='api_cate_topword'),
]
