from django.shortcuts import render
import pandas as pd

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

'''
the format of data:
{'政治': [('韓國瑜', 6344),
  ('蔡英文', 2114),
  ('賴清德', 1480),
  ...
  }
'''


def home(request):
    return render(request, 'app_top_person_sqlalchemy_db/home.html')
    #return render(request, 'app_top_person_db/home.html') # home.html是相同的

# csrf_exempt is used for POST
# 單獨指定這一支程式忽略csrf驗證
@csrf_exempt
def api_get_topPerson(request):

    # chart_data, wf_pairs = get_category_topkey("科技", 10) #先做簡單的測試

    cate = request.POST.get('news_category')
    topk = request.POST.get('topk')
    topk = int(topk)
    #print(cate, topk)

    chart_data, wf_pairs = get_category_topPerson_db(cate, topk)
    #chart_data, wf_pairs = get_category_topPerson(cate, topk)

    # print(chart_data)
    response = {'chart_data':  chart_data,
                'wf_pairs': wf_pairs,
                }
    return JsonResponse(response)


import pandas as pd
import sqlalchemy
from sqlalchemy import text

# You can connect to your sqlite database
engine = sqlalchemy.create_engine('sqlite:///app_top_person_sqlalchemy_db/sqlite_db/newsdata.sqlite3.db')
conn = engine.connect()

# You can connect to your maria or mysql database
#engine = sqlalchemy.create_engine("mysql+pymysql://mis2:mis123@163.18.23.21:3306/poa")

# get charting data from database
def get_category_topPerson_db(cate, topk):

    # wf_pairs = data[cate][0:topk] # query from dataframe
    statement = "SELECT top_keys FROM topperson where category='{}'".format(cate)
    result = conn.execute(text(statement)).fetchone()
    wf_pairs = eval(result[0])[0:topk]
    
    words = [w for w, f in wf_pairs]
    freqs = [f for w, f in wf_pairs]
    chart_data = {
        "category": cate,
        "labels": words,
        "values": freqs}
    #print(chart_data)
    return chart_data, wf_pairs  # chart_data


'''
# load data
def load_data_topPerson():
    # read df
    df_topPerson = pd.read_csv(
        'app_top_person/dataset/news_top_person_by_category_via_ner.csv')
    # refresh data
    global data # make data global. It can be used everywhere.
    data = {}
    for idx, row in df_topPerson.iterrows():
        data[row['category']] = eval(row['top_keys'])


# Load data first when starting server.
load_data_topPerson()

#
def get_category_topPerson(cate, topk):
    wf_pairs = data[cate][0:topk]
    words = [w for w, f in wf_pairs]
    freqs = [f for w, f in wf_pairs]
    chart_data = {
        "category": cate,
        "labels": words,
        "values": freqs}
    return chart_data, wf_pairs  # chart_data is for charting
'''



print("app_news_analysis--類別熱門人物db載入成功!")


