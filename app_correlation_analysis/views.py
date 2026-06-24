from django.http import JsonResponse
from django.shortcuts import render
import pandas as pd
from datetime import datetime, timedelta
try:
    from scipy import stats
except Exception:
    stats = None

from django.views.decorators.csrf import csrf_exempt
from app_user_keyword.views import df


def load_data_correlation():
    # Read data from csv file
    global df
    df = pd.read_csv(
        'app_correlation_analysis/dataset/news_dataset_preprocessed_for_django.csv', sep='|')


# load data
# load_data_correlation()


def home(request):
    return render(request, 'app_correlation_analysis/home.html')


# csrf_exempt is used for POST
# 單獨指定這一支程式忽略csrf驗證
@csrf_exempt
def api_get_corr_data(request):

    # (1) get keywords, category, condition, and weeks passed from frontend
    userkey1 = request.POST['userkey1']
    userkey2 = request.POST['userkey2']
    print(userkey2)
    print(type(userkey2))

    userkey1 = userkey1.split()
    userkey2 = userkey2.split()

    pearson_coef, p_value, a_line_xy_data, b_line_xy_data = get_correlation_data(userkey1,
        userkey2, weeks=12)

    response = {
        'pearson_coef': pearson_coef,
        'p_value': p_value,
        'a_line_xy_data': a_line_xy_data,
        'b_line_xy_data': b_line_xy_data
    }
    return JsonResponse(response)


def get_correlation_data(queryA, queryB, weeks=12):
    a_line_xy_data, a_freq_data = get_keyword_occurrence_time_series(
        queryA, weeks)
    b_line_xy_data, b_freq_data = get_keyword_occurrence_time_series(
        queryB, weeks)

    try:
        pearson_coef, p_value = stats.pearsonr(a_freq_data, b_freq_data)
        # person = np.corrcoef(y_A, y_B)[0,1]
    except:
        return None

    pearson_coef = round(pearson_coef,3)
    p_value = round(p_value,5)

    return pearson_coef, p_value, a_line_xy_data, b_line_xy_data

def get_keyword_occurrence_time_series(query_keywords, cond='or', weeks=12):
    # end_date
    end_date = df.date.max()
    # start date
    start_date_delta = (datetime.strptime(end_date, '%Y-%m-%d').date() - timedelta(weeks=weeks)).strftime('%Y-%m-%d')
    start_date_min = df.date.min()
    # set start_date as the larger one from the start_date_delta and start_date_min
    start_date = max(start_date_delta,   start_date_min)

    # (1) proceed filtering: a duration of a period of time
    # 期間條件
    period_condition = (df.date >= start_date) & (df.date <= end_date) 

    # (2) proceed filtering: news category
    # and or 條件
    if (cond == 'and'):
        # query keywords condition使用者輸入關鍵字條件and
        condition = period_condition & df.content.apply(lambda text: all((qk in text) for qk in query_keywords)) #寫法:all()
    else:
        # query keywords condition使用者輸入關鍵字條件
        condition = period_condition & df.content.apply(lambda text: any((qk in text) for qk in query_keywords)) #寫法:any()

    # condiction is a list of True or False boolean value
    df_query = df[condition]

    query_freq = pd.DataFrame({'date_index':pd.to_datetime( df_query.date ),'freq':[1 for _ in range(len(df_query))]})


    # 開始時間、結束時間兩項必須也加入到query_freq，計算次數時才會有完整的時間軸，否則時間軸長度會因為新聞時間不同，導致時間軸不一致
    dt_start_date = datetime.strptime(start_date, '%Y-%m-%d')
    dt_end_date = datetime.strptime(end_date, '%Y-%m-%d')    
    
    query_freq = pd.concat([query_freq, pd.DataFrame({'date_index': [dt_start_date], 'freq': [0]})])
    query_freq = pd.concat([query_freq, pd.DataFrame({'date_index': [dt_end_date], 'freq': [0]})])
    
    #query_freq = query_freq.append({'date_index': dt_start_date, 'freq': 0}, ignore_index=True)
    #query_freq = query_freq.append({'date_index': dt_end_date, 'freq': 0}, ignore_index=True)

    freq_data = query_freq.groupby(pd.Grouper(key='date_index', freq='D')).sum()

    freq_data.reset_index(inplace=True)

    # 只有y, 沒有時間變數x
    y_freq_data = freq_data.freq.to_list()
    # 有時間變數x,y
    line_xy_data = [{'x':date.strftime('%Y-%m-%d'),'y':freq} for date, freq in zip(freq_data.date_index,freq_data.freq)]

    return line_xy_data, y_freq_data


print('app_correlation was loaded!')
