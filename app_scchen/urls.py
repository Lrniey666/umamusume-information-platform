from django.urls import path
from . import views

#  使用app_name是讓各個APP的變數與方法名稱有區隔
#  若名稱不衝突，不使用app_name也可以
#  app_name是一種namespace的概念
# 整合多個可獨立運作的APP成為一個大型專案必備知識
# 在template中如何使用?
# <a class="nav-link" href="{% url 'app_top_person:home' %}">熱門人物</a>

app_name = "app_scchen"

urlpatterns = [
    # top (popular) persons
    path("", views.home, name="home"),
    # api for getting data of chen shih chung
    path("api_chen_shih_chung/", views.api_chen_shih_chung, name="api_chen_shih_chung"),
]
