from django.shortcuts import render
import pandas as pd
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
import re


def _load_df_from_db() -> pd.DataFrame:
    """優先從 NewsData(status='labeled') 建立 DataFrame；無資料時 fallback 至 CSV。"""
    try:
        from app_user_keyword_db.models import NewsData
        qs = NewsData.objects.filter(status='labeled').values(
            'item_id', 'source', 'date', 'category', 'title', 'content',
            'link', 'photo_link', 'tokens_filtered', 'top_key_freq', 'sentiment',
        )
        df_db = pd.DataFrame.from_records(list(qs))
        if not df_db.empty:
            df_db['date'] = df_db['date'].astype(str)
            print(f"[app_user_keyword] 從 DB 載入 {len(df_db)} 筆（status=labeled）")
            return df_db
    except Exception as exc:
        print(f"[app_user_keyword] DB 載入失敗，改讀 CSV：{exc}")
    # fallback: CSV
    try:
        from services.news_service import load_news_df
        _df = load_news_df()
        print(f"[app_user_keyword] fallback: 從 CSV 載入 {len(_df)} 筆")
        return _df
    except FileNotFoundError:
        print("[app_user_keyword] CSV 亦不存在，回傳空 DataFrame")
        return pd.DataFrame(columns=[
            'item_id', 'source', 'date', 'category', 'title', 'content',
            'link', 'photo_link',
        ])


df = _load_df_from_db()


def reload_df_data():
    global df
    df = _load_df_from_db()

def home(request):
    return render(request, 'app_user_keyword/home.html')

# When POST is used, make this function be exempted from the csrf 
@csrf_exempt
def api_get_top_userkey(request):
    userkey = request.POST['userkey']
    cate    = request.POST['cate']
    cond    = request.POST['cond']
    weeks   = int(request.POST['weeks'])
    source  = request.POST.get('source', 'all')
    key     = userkey.split()

    df_query = filter_dataFrame(key, cond, cate, weeks, source)

    if len(df_query) == 0:
        return JsonResponse({'error': '查無符合條件的公告，請嘗試其他關鍵字或放寬篩選條件。'})

    key_freq_cat, key_occurrence_cat = count_keyword(df_query, key)
    print(key_occurrence_cat)

    key_time_freq = get_keyword_time_based_freq(df_query)

    return JsonResponse({
        'key_occurrence_cat': key_occurrence_cat,
        'key_freq_cat':       key_freq_cat,
        'key_time_freq':      key_time_freq,
    })


# Searching keywords from "content" column
def filter_dataFrame(user_keywords, cond, cate, weeks, source='all'):
    # dropna() 避免 NaN（float）與字串比較時的 TypeError
    valid_dates = df.date.dropna()
    end_date    = valid_dates.max() if len(valid_dates) else None
    if not end_date or not isinstance(end_date, str):
        # fallback：無日期資料時回傳空 DataFrame
        return df.iloc[0:0]
    start_date = (datetime.strptime(end_date, '%Y-%m-%d').date() - timedelta(weeks=weeks)).strftime('%Y-%m-%d')

    condition = df.date.notna() & (df.date >= start_date) & (df.date <= end_date)

    if cate != '全部':
        condition = condition & (df.category == cate)

    # source 篩選（向下相容：'all' 時不篩）
    if source != 'all' and 'source' in df.columns:
        condition = condition & (df.source == source)

    if cond == 'and':
        condition = condition & df.content.apply(lambda text: all(qk in text for qk in user_keywords))
    elif cond == 'or':
        condition = condition & df.content.apply(lambda text: any(qk in text for qk in user_keywords))

    return df[condition]



# ** How many pieces of news were the keyword(s) mentioned in?
# ** How many times were the keyword(s) mentioned?

# For the query_df, count the occurence and frequency for each category.

# (1) cate_occurence={}  被多少篇新聞報導 How many pieces of news contain the keywords.
# (2) cate_freq={}       被提到多少次? How many times are the keywords mentioned

# bilibili 原生類別 + bahamut 類別（小量的非洲/歐洲/新馬娘等討論串歸入「其他」）
news_categories = [
    # bilibili
    '活動', '卡池', '競賽', '系統',
    # bahamut
    '情報', '心得', '討論', '攻略', '公告',
    '問題', '閒聊', '繪圖', '繪畫', '史實', '整理', '小說',
    # 通用
    '其他', '全部',
]

def count_keyword(df_query, query_keywords):

    cate_occurrence = {}
    cate_freq = {}
    
    # 字典初始化
    for cate in news_categories:
        cate_occurrence[cate] = 0   # {'政治':0, '科技':0}
        cate_freq[cate] = 0
        

    for idx, row in df_query.iterrows():
        # 未知類別（多來源資料）歸入「其他」
        cate = row.category if (row.category in cate_occurrence and row.category != '全部') else '其他'
        cate_occurrence[cate] += 1
        cate_occurrence['全部'] += 1

        # count the keyword frequency各類別次數統計
        content = str(row.content) if pd.notna(row.content) else ''
        freq = sum([ len(re.findall(keyword, content, re.I)) for keyword in query_keywords] )
        cate_freq[cate] += freq
        cate_freq['全部'] += freq

    return cate_freq, cate_occurrence


def get_keyword_time_based_freq(df_query):
    date_samples = df_query.date
    parsed_dates = pd.to_datetime(date_samples, errors='coerce')
    # 過濾掉解析失敗（NaT）的列
    valid_mask = parsed_dates.notna()
    if not valid_mask.any():
        return []
    query_freq = pd.DataFrame({
        'date_index': parsed_dates[valid_mask],
        'freq': [1] * int(valid_mask.sum()),
    })
    data = query_freq.groupby(pd.Grouper(key='date_index', freq='D')).sum()
    time_data = []
    for i, idx in enumerate(data.index):
        time_data.append({'x': idx.strftime('%Y-%m-%d'), 'y': int(data.iloc[i].freq)})
    return time_data

print("app_user_keyword was loaded!")

