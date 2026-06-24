from django.urls import path
from django.views.generic import TemplateView
from . import views

app_name = "app_poa_introduction"

urlpatterns = [
    path('', views.introduction, name='introduction'),
    path('platform/', TemplateView.as_view(template_name='app_poa_introduction/platform-introduction.html'), name='platform_introduction'),
]

