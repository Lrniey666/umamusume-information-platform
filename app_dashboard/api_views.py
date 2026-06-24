import re
import json
from django.http import JsonResponse
from django.db.models import Avg
from django.db.models.functions import TruncMonth
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from app_uma_news.models import GameAnnouncement
from app_uma_comments.models import PlayerComment
from app_comment_sentiment.models import CommentSentiment


def api_stats(request):
    total          = GameAnnouncement.objects.count()
    analyzed_qs    = CommentSentiment.objects.filter(analyzed_at__isnull=False)
    analyzed_count = analyzed_qs.count()
    pending_count  = total - analyzed_count

    total_comments = PlayerComment.objects.count()

    avg = analyzed_qs.aggregate(
        avg_pos=Avg('positive_score'),
        avg_neg=Avg('negative_score'),
        avg_neu=Avg('neutral_score'),
    )

    categories = list(GameAnnouncement.objects.values_list('category', flat=True).distinct())
    bar_cats, bar_pos = [], []
    for cat in categories:
        cat_avg = analyzed_qs.filter(
            announcement__category=cat
        ).aggregate(avg=Avg('positive_score'))['avg'] or 0
        bar_cats.append(cat)
        bar_pos.append(round(cat_avg * 100, 1))

    monthly = (
        analyzed_qs
        .annotate(month=TruncMonth('announcement__published_date'))
        .values('month')
        .annotate(
            avg_pos=Avg('positive_score'),
            avg_neg=Avg('negative_score'),
            avg_neu=Avg('neutral_score'),
        )
        .order_by('month')
    )
    labels, pos_l, neg_l, neu_l = [], [], [], []
    for m in monthly:
        if m['month']:
            labels.append(m['month'].strftime('%Y-%m'))
            pos_l.append(round(m['avg_pos'] or 0, 3))
            neg_l.append(round(m['avg_neg'] or 0, 3))
            neu_l.append(round(m['avg_neu'] or 0, 3))

    return JsonResponse({
        'summary': {
            'total_analyzed': analyzed_count,
            'total_comments': total_comments,
            'pending_count':  pending_count,
            'avg_positive':   round((avg['avg_pos'] or 0), 3),
        },
        'pie_data': {
            'positive': round((avg['avg_pos'] or 0) * 100, 1),
            'negative': round((avg['avg_neg'] or 0) * 100, 1),
            'neutral':  round((avg['avg_neu'] or 0) * 100, 1),
        },
        'bar_data': {'categories': bar_cats, 'positive_rates': bar_pos},
        'line_data': {'labels': labels, 'positive': pos_l, 'negative': neg_l, 'neutral': neu_l},
    })


def api_announcements(request):
    q        = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')
    limit    = request.GET.get('limit', '')

    qs = GameAnnouncement.objects.select_related('sentiment').prefetch_related('comments')
    if q:
        qs = (qs.filter(title__icontains=q) | GameAnnouncement.objects.filter(content__icontains=q)).distinct()
    if category and category != '全部':
        qs = qs.filter(category=category)

    qs = qs.order_by('-published_date', '-created_at')
    try:
        limit_int = int(limit)
        if limit_int > 0:
            qs = qs[:limit_int]
    except (ValueError, TypeError):
        pass

    data = []
    for ann in qs:
        s = getattr(ann, 'sentiment', None)
        analyzed = s is not None and s.analyzed_at is not None
        data.append({
            'id':             ann.pk,
            'title':          ann.title,
            'category':       ann.category,
            'published_date': ann.published_date.strftime('%Y-%m-%d') if ann.published_date else '',
            'comments_count': ann.comments.count(),
            'analyzed':       analyzed,
            'positive_score': s.positive_score if analyzed else None,
            'negative_score': s.negative_score if analyzed else None,
            'neutral_score':  s.neutral_score  if analyzed else None,
        })
    return JsonResponse({'announcements': data})


def api_announcement_detail(request, pk):
    try:
        ann = GameAnnouncement.objects.get(pk=pk)
    except GameAnnouncement.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': '公告不存在'}, status=404)

    comments = list(ann.comments.order_by('-upvotes').values(
        'content', 'author', 'upvotes', 'downvotes', 'floor'
    )[:30])

    s = getattr(ann, 'sentiment', None)
    analyzed = s is not None and s.analyzed_at is not None
    sentiment_data = None
    if analyzed:
        sentiment_data = {
            'positive_score': s.positive_score,
            'negative_score': s.negative_score,
            'neutral_score':  s.neutral_score,
            'excited':        s.excited,
            'happy':          s.happy,
            'mixed':          s.mixed,
            'disappointed':   s.disappointed,
            'angry':          s.angry,
            'sad':            s.sad,
            'ai_model':       s.ai_model,
            'analyzed_at':    s.analyzed_at.isoformat(),
        }

    return JsonResponse({
        'id':             ann.pk,
        'title':          ann.title,
        'content':        ann.content,
        'category':       ann.category,
        'published_date': ann.published_date.strftime('%Y-%m-%d') if ann.published_date else '',
        'source_url':     ann.source_url,
        'comments':       comments,
        'sentiment':      sentiment_data,
    })


@csrf_exempt
@require_http_methods(['POST'])
def api_analyze(request, pk):
    from app_comment_sentiment.llm_client import client, MODEL_NAME
    from app_comment_sentiment.management.commands.analyze_comments import analyze_one

    try:
        ann = GameAnnouncement.objects.get(pk=pk)
    except GameAnnouncement.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': '公告不存在'}, status=404)

    try:
        sentiment = analyze_one(ann)
        return JsonResponse({
            'status': 'success',
            'sentiment': {
                'positive_score': sentiment.positive_score,
                'negative_score': sentiment.negative_score,
                'neutral_score':  sentiment.neutral_score,
                'excited':        sentiment.excited,
                'happy':          sentiment.happy,
                'mixed':          sentiment.mixed,
                'disappointed':   sentiment.disappointed,
                'angry':          sentiment.angry,
                'sad':            sentiment.sad,
                'ai_model':       sentiment.ai_model,
                'analyzed_at':    sentiment.analyzed_at.isoformat(),
            },
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'AI 分析失敗：{str(e)}'}, status=500)
