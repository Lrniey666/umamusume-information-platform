# app_user_keyword_db/views.py
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Max, Count
from datetime import timedelta
import pandas as pd

from .models import NewsData
from app_user_keyword.views import get_keyword_time_based_freq
from app_user_keyword_sentiment.views import get_article_sentiment

VALID_SOURCES = {'bilibili', 'bahamut', 'udn', 'ettoday', 'gamme'}


def home(request):
    return render(request, 'app_user_keyword_db/home.html')


@csrf_exempt
def api_get_userkey_data(request):
    userkey = request.POST.get('userkey', '')
    cate    = request.POST.get('cate', '全部')
    cond    = request.POST.get('cond', 'or')
    weeks   = int(request.POST.get('weeks', 52))
    source  = request.POST.get('source', 'all')
    key     = userkey.split()

    if not key:
        return JsonResponse({'error': '請輸入關鍵字'})

    queryset = filter_database_fullText(key, cond, cate, weeks, source)

    if not queryset.exists():
        return JsonResponse({'error': '查無結果，請換個關鍵字試試'})

    df_query = pd.DataFrame(list(queryset.values(
        'date', 'category', 'title', 'content',
        'link', 'photo_link', 'top_key_freq', 'sentiment',
    )))
    df_query['date'] = df_query['date'].astype(str)

    key_time_freq = get_keyword_time_based_freq(df_query)
    sentiCount, _ = get_article_sentiment(df_query)
    newslinks     = _get_newslinks(df_query, k=10)
    num_articles  = len(df_query)

    return JsonResponse({
        'newslinks':     newslinks,
        'num_articles':  num_articles,
        'key_time_freq': key_time_freq,
        'sentiCount':    sentiCount,
    })


def filter_database_fullText(user_keywords, cond, cate, weeks, source='all'):
    latest_date = NewsData.objects.filter(
        date__isnull=False
    ).aggregate(max_date=Max('date'))['max_date']

    if latest_date is None:
        queryset = NewsData.objects.all()
    else:
        start_date = latest_date - timedelta(weeks=weeks)
        queryset   = NewsData.objects.filter(
            Q(date__gte=start_date) | Q(date__isnull=True)
        )

    if cate != '全部':
        queryset = queryset.filter(category=cate)

    # source 篩選（向下相容：'all' 時不篩）
    if source != 'all' and source in VALID_SOURCES:
        queryset = queryset.filter(source=source)

    if cond == 'and':
        for kw in user_keywords:
            queryset = queryset.filter(content__contains=kw)
    elif cond == 'or':
        q_obj = Q()
        for kw in user_keywords:
            q_obj |= Q(content__contains=kw)
        queryset = queryset.filter(q_obj)

    return queryset


def _get_newslinks(df_query, k=10):
    results = []
    for _, row in df_query.head(k).iterrows():
        results.append({
            'title':      str(row.get('title', '')),
            'link':       str(row.get('link', '')),
            'photo_link': str(row.get('photo_link', '')),
        })
    return results


def api_source_stats(request):
    """GET /api/source_stats/ — 回傳各 source 文章數統計。"""
    total = NewsData.objects.count()
    by_source_qs = (
        NewsData.objects
        .values('source')
        .annotate(n=Count('source'))
        .order_by('source')
    )
    by_source = {row['source']: row['n'] for row in by_source_qs}
    return JsonResponse({'total': total, 'by_source': by_source})
