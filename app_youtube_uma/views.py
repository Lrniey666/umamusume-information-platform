from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncWeek
from .models import YouTubeVideo, YouTubeComment

POS_THR, NEG_THR = 0.6, 0.4


def dashboard(request):
    """YouTube 影片情感儀表板主頁面"""
    query = request.GET.get('q', '').strip()
    videos = YouTubeVideo.objects.all()
    if query:
        videos = videos.filter(
            Q(title__icontains=query) | Q(channel_name__icontains=query)
        )
    top_videos = videos.order_by('-view_count')[:20]
    stats = videos.filter(sentiment__isnull=False).aggregate(
        avg_sentiment=Avg('sentiment'),
        pos_count=Count('video_id', filter=Q(sentiment__gte=POS_THR)),
        neg_count=Count('video_id', filter=Q(sentiment__lte=NEG_THR)),
        total=Count('video_id'),
    )
    return render(request, 'app_youtube_uma/dashboard.html', {
        'videos': top_videos,
        'stats': stats,
        'query': query,
        'total_videos': YouTubeVideo.objects.count(),
        'total_comments': YouTubeComment.objects.count(),
    })


def api_videos(request):
    """JSON API — 影片列表（供 Chart.js 圖表使用）"""
    videos = YouTubeVideo.objects.filter(
        sentiment__isnull=False
    ).order_by('-published_at')[:50]
    data = [{
        'video_id': v.video_id,
        'title': v.title,
        'channel': v.channel_name,
        'published_at': v.published_at.strftime('%Y-%m-%d') if v.published_at else '',
        'view_count': v.view_count,
        'like_count': v.like_count,
        'comment_count': v.comment_count,
        'thumbnail': v.thumbnail_url,
        'sentiment': v.sentiment,
        'sentiment_label': (
            '正面' if v.sentiment >= POS_THR else
            '負面' if v.sentiment <= NEG_THR else '中立'
        ),
        'url': f'https://www.youtube.com/watch?v={v.video_id}',
    } for v in videos]
    return JsonResponse({'videos': data, 'total': len(data)})


def api_stats(request):
    """JSON API — 聲量趨勢統計（週維度）；支援 ?q= 與 dashboard 同步篩選"""
    query = request.GET.get('q', '').strip()
    qs = YouTubeVideo.objects.filter(
        sentiment__isnull=False,
        published_at__isnull=False,
    )
    if query:
        qs = qs.filter(
            Q(title__icontains=query) | Q(channel_name__icontains=query)
        )
    weekly = (
        qs
        .annotate(week=TruncWeek('published_at'))
        .values('week')
        .annotate(
            count=Count('video_id'),
            avg_sentiment=Avg('sentiment'),
        )
        .order_by('week')
    )
    return JsonResponse({
        'weekly_trend': [
            {
                'week': str(w['week'])[:10],
                'count': w['count'],
                'avg_sentiment': round(w['avg_sentiment'] or 0, 3),
            } for w in weekly
        ]
    })
