from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse

from datetime import datetime, timedelta
import pandas as pd
import re
from collections import Counter

import app_user_keyword.views as userkeyword_views

def load_df_data():
    global df
    df = userkeyword_views.df

load_df_data()


def home(request):
    return render(request, 'app_user_keyword_association/home.html')


@csrf_exempt
def api_get_userkey_associate(request):
    userkey = request.POST.get('userkey')
    cate    = request.POST.get('cate')
    cond    = request.POST.get('cond')
    weeks   = int(request.POST.get('weeks'))
    keys    = userkey.split()

    df_query = filter_dataFrame_fullText(keys, cond, cate, weeks)

    if len(df_query) == 0:
        return JsonResponse({'error': '查無相關公告，請嘗試其他關鍵字。'})

    newslinks       = get_title_link_topk(df_query, k=15)
    related_words, clouddata = get_related_word_clouddata(df_query)
    same_paragraph  = get_same_para(df_query, keys, cond, k=10)

    return JsonResponse({
        'newslinks':      newslinks,
        'related_words':  related_words,
        'same_paragraph': same_paragraph,
        'clouddata':      clouddata,
        'num_articles':   len(df_query),
    })


def filter_dataFrame_fullText(user_keywords, cond, cate, weeks):
    # 過濾有效日期字串，避免混型欄位（str + float NaN）導致 max() TypeError
    valid_dates = df.date.dropna()
    valid_dates = valid_dates[valid_dates.apply(lambda d: isinstance(d, str) and len(d) == 10)]
    end_date = valid_dates.max() if len(valid_dates) else None
    if not end_date or not isinstance(end_date, str):
        return df.iloc[0:0]
    try:
        start_date = (datetime.strptime(end_date, '%Y-%m-%d').date() -
                      timedelta(weeks=weeks)).strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        return df.iloc[0:0]

    str_mask    = df.date.apply(lambda d: isinstance(d, str) and len(d) == 10)
    period_cond = str_mask & (df.date >= start_date) & (df.date <= end_date)
    condition   = period_cond if cate == '全部' else period_cond & (df.category == cate)

    if cond == 'and':
        condition = condition & df.content.apply(
            lambda t: all(kw in str(t) for kw in user_keywords))
    else:
        condition = condition & df.content.apply(
            lambda t: any(kw in str(t) for kw in user_keywords))

    return df[condition]


def get_title_link_topk(df_query, k=15):
    items = []
    for i in range(min(k, len(df_query))):
        row = df_query.iloc[i]
        link = row.get('link', '') if not pd.isna(row.get('link', float('nan'))) else ''
        items.append({
            'category': row['category'],
            'title':    row['title'],
            'link':     link,
        })
    return items


def get_related_word_clouddata(df_query):
    counter = Counter()
    for idx in range(len(df_query)):
        raw = df_query.iloc[idx].get('top_key_freq', '')
        try:
            pair_dict = dict(eval(str(raw)))
            counter += Counter(pair_dict)
        except Exception:
            pass

    wf_pairs = counter.most_common(20)
    if not wf_pairs:
        return [], []

    min_ = wf_pairs[-1][1]
    max_ = wf_pairs[0][1]
    text_min, text_max = 20, 120
    denom = (max_ - min_) if max_ != min_ else 1
    clouddata = [
        {'text': w, 'size': int(text_min + (f - min_) / denom * (text_max - text_min))}
        for w, f in wf_pairs
    ]
    return wf_pairs, clouddata


def cut_paragraph(text):
    paragraphs = str(text).split('。')
    return list(filter(None, paragraphs))


def get_same_para(df_query, user_keywords, cond, k=30):
    same_para = []
    for text in df_query.content:
        for para in cut_paragraph(text):
            para += '。'
            if cond == 'and':
                if all(re.search(kw, para) for kw in user_keywords):
                    same_para.append(para)
            else:
                if any(re.search(kw, para) for kw in user_keywords):
                    same_para.append(para)
    return same_para[:k]


print("app_user_keyword_association loaded!")
