from django.urls import path
from . import views

app_name = 'app_course_intro'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/', views.api_introduction, name='api_introduction'),
    path('course/', views.course_introduction, name='course_introduction'),
]
