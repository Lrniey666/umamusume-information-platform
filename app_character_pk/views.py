from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import pandas as pd
import ast
import os

from services.news_service import PK_CSV

def _load_pk_data():
    global _pk_data
    csv_path = PK_CSV
    _pk_data = {}
    if not os.path.exists(csv_path):
        return
    df = pd.read_csv(csv_path)
    for _, row in df.iterrows():
        try:
            _pk_data[row['name']] = ast.literal_eval(str(row['value']))
        except Exception:
            pass

_load_pk_data()


def home(request):
    return render(request, 'app_character_pk/home.html')


def popularity_list(request):
    return render(request, 'app_character_pk/popularity_list.html')


@csrf_exempt
def api_get_character_pk(request):
    return JsonResponse(_pk_data)


print('app_character_pk 角色人氣PK站載入完成！')
