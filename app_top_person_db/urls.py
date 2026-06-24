from django.urls import path
from . import views

app_name="app_top_person_db"

urlpatterns = [
    # top (popular) persons
    path('', views.home, name='home'),
    # ajax path
    path('api_get_topPerson/', views.api_get_topPerson, name='api_get_topPerson'),
    
    # calculate top person
    path('calculate_top_person/', views.calculate_top_person, name='calculate_top_person'),
]

