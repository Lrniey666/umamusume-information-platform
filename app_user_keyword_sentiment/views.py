from django.http import JsonResponse
from django.shortcuts import render
import pandas as pd
from datetime import datetime, timedelta
from django.views.decorators.csrf import csrf_exempt
import requests
from app_user_keyword.views import filter_dataFrame
import app_user_keyword.views as userkeyword_views

'''
# 跟別人借用df
# (1) Load news data--approach 1 直接指定某個csv檔案
def load_df_data_v1():
    global df # global variable
    # df = pd.read_csv('app_user_keyword/dataset/cna_news_200_preprocessed.csv',sep='|')
    df = pd.read_csv('app_user_keyword_sentiment/dataset/uma_news_preprocessed.csv',sep='|')

# (2) Load news data--approach 2 跟隔壁的app借用df
# import from app_user_keyword.views and use df later
def load_df_data():
    # import and use df from app_user_keyword 
    global df # global variable
    df = userkeyword_views.df

# call load data function when starting server
#load_df_data_v1()
#load_df_data()
'''

def home(request):
    return render(request, 'app_user_keyword_sentiment/home.html')

# GET: csrf_exempt is not necessary
# POST: csrf_exempt should be used
@csrf_exempt
def api_get_userkey_sentiment_from_remote_api_through_backend(request):

    userkey = request.POST['userkey']
    cate = request.POST['cate']
    cond = request.POST['cond']
    weeks = int(request.POST['weeks'])

    try:
        # (可選擇)展示從後端呼叫API: Call internet sentiment API using requests  但是不能自己呼叫自己!
        url_api_get_sentiment = "http://163.18.23.20:8000/userkeyword_senti/api_get_userkey_sentiment/"
        # Setup data for sentiment analysis request
        sentiment_data = {
            'userkey': userkey,
            'cate': cate,
            'cond': cond,
            'weeks': weeks
        }
        # Alternative way to call the sentiment API directly with requests
        sentiment_response = requests.post(url_api_get_sentiment, data=sentiment_data, timeout=5)
        if sentiment_response.status_code == 200:
            print("由後端呼叫他處API，取得情感分析數據成功!")
            # 解析來自API的回應內容。 .json() 方法會將回應的 JSON 格式資料轉換成 Python 的字典(dictionary)或列表(list)。
            # Parse the response content from the API. The .json() method converts the JSON formatted data from the response into a Python dictionary or list.
            response = sentiment_response.json()
            return JsonResponse(response)
        else:
            print(f"回傳有錯誤")
            print(f"Sentiment API error: {sentiment_response.status_code}")
            return JsonResponse({'error': 'Failed to get sentiment analysis.'})
    except Exception as e:
        # Catch any other unexpected errors during the process
        print(f"An unexpected error occurred while processing sentiment data: {e}")
        print(f"呼叫異常失敗，進行本地處理資料")
        return JsonResponse({'error': 'An internal error occurred while processing sentiment data.'}, status=500) # Internal Server Error
 
# GET: csrf_exempt is not necessary
# POST: csrf_exempt should be used
@csrf_exempt
def api_get_userkey_sentiment(request):

    userkey = request.POST['userkey']
    cate    = request.POST['cate']
    cond    = request.POST['cond']
    weeks   = int(request.POST['weeks'])
    source  = request.POST.get('source', 'all')

    query_keywords = userkey.split()
    df_query = filter_dataFrame(query_keywords, cond, cate, weeks, source)
    
    # if df_query is empty, return an error message
    if len(df_query) == 0:
        return JsonResponse({'error': 'No results found for the given keywords.'})
    
    sentiCount, sentiPercnt = get_article_sentiment(df_query)

    if weeks <= 4:
        freq_type = 'D'
    else:
        freq_type = 'W'

    line_data_pos = get_daily_basis_sentiment_count(df_query, sentiment_type='pos', freq_type=freq_type)
    line_data_neg = get_daily_basis_sentiment_count(df_query, sentiment_type='neg', freq_type=freq_type)

    response = {
        'sentiCount': sentiCount,
        'data_pos':line_data_pos,
        'data_neg':line_data_neg,
    }
    return JsonResponse(response)

def get_article_sentiment(df_query):
    sentiCount = {'Positive': 0, 'Negative': 0, 'Neutral': 0}
    sentiPercnt = {'Positive': 0, 'Negative': 0, 'Neutral': 0}
    numberOfArticle = len(df_query)
    for senti in df_query.sentiment:
        try:
            s = float(senti)
        except (TypeError, ValueError):
            sentiCount['Neutral'] += 1
            continue
        # determine sentimental polarity
        if s >= 0.6:
            sentiCount['Positive'] += 1
        elif s <= 0.4:
            sentiCount['Negative'] += 1
        else:
            sentiCount['Neutral'] += 1
    for polar in sentiCount :
        try:
            sentiPercnt[polar]=int(sentiCount[polar]/numberOfArticle*100)
        except:
            sentiPercnt[polar] = 0 # 若分母 numberOfArticle=0會報錯
    return sentiCount, sentiPercnt


def get_daily_basis_sentiment_count(df_query, sentiment_type='pos', freq_type='D'):

    # 自訂正負向中立的標準，sentiment score是機率值，介於0~1之間
    # Using lambda to determine if an article is postive or not.
    if sentiment_type == 'pos':
        lambda_function = lambda senti: 1 if senti >= 0.6 else 0 #大於0.6為正向 
    elif sentiment_type == 'neg':
        lambda_function = lambda senti: 1 if senti <= 0.4 else 0 #小於0.4為負向
    elif sentiment_type == 'neutral':
        lambda_function = lambda senti: 1 if senti > 0.4 & senti < 0.4 else 0 #介於中間為中立
    else:
        return None 
        
    parsed_dates = pd.to_datetime(df_query.date, errors='coerce')
    safe_senti = [
        lambda_function(float(s)) if s is not None and str(s) not in ('nan', 'None', '') else 0
        for s in df_query.sentiment
    ]
    freq_df = pd.DataFrame({'date_index': parsed_dates, 'frequency': safe_senti})
    freq_df = freq_df[freq_df['date_index'].notna()]
    # Group rows by the date to the daily number of articles. 加總合併同一天新聞，篇數就被計算好了
    freq_df_group = freq_df.groupby(pd.Grouper(key='date_index',freq=freq_type)).sum()
    
    # 'date_index'為index(索引)，將其變成欄位名稱，inplace=True表示原始檔案會被異動
    freq_df_group.reset_index(inplace=True)
    
    # x,y，用於畫趨勢線圖
    xy_line_data = [{'x':date.strftime('%Y-%m-%d'),'y':freq} for date, freq in zip(freq_df_group.date_index,freq_df_group.frequency)]
    return xy_line_data


print("app_userkey_sentiment was loaded!")
