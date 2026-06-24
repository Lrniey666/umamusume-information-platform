import subprocess
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from . import scheduler_manager
from .models import Article, CommentSentiment


# ──────────────────────────────────────────────────────────────
# 儀表板頁面視圖（C1 修復 / H2 完整修復）
# ──────────────────────────────────────────────────────────────

def dashboard(request):
    """留言情感儀表板主頁面"""
    return render(request, 'app_comment_sentiment/dashboard.html')


def api_data(request):
    """返回 Article 列表 + 情緒六維度 JSON（供前端 Chart.js 使用）"""
    query = request.GET.get('q', '').strip()

    articles = (
        Article.objects
        .prefetch_related('comments')
        .select_related('emotion')
        .order_by('-published_date', '-created_at')
    )
    if query:
        articles = articles.filter(
            Q(title__icontains=query) | Q(content__icontains=query)
        )

    data = []
    for article in articles[:50]:
        emotion = getattr(article, 'emotion', None)
        emotion_data = {}
        if emotion is not None:
            emotion_data = {
                'excited':     round(emotion.cheer_up, 2),
                'happy':       round(emotion.happy, 2),
                'mixed':       round(emotion.mixed, 2),
                'disappointed': round(emotion.dumbfounded, 2),
                'angry':       round(emotion.angry, 2),
                'sad':         round(emotion.sad, 2),
            }
        data.append({
            'id':             article.id,
            'title':          article.title,
            'url':            article.url,
            'category':       article.category,
            'published_date': str(article.published_date) if article.published_date else '',
            'source':         article.source,
            'positive_score': article.positive_score,
            'negative_score': article.negative_score,
            'neutral_score':  article.neutral_score,
            'comments_count': article.comments.count(),
            'emotion':        emotion_data,
            'analyzed':       article.analyzed_at is not None,
        })

    return JsonResponse({
        'articles': data,
        'total':    Article.objects.count(),
    })


# ──────────────────────────────────────────────────────────────
# 排程控制 API（原有）
# ──────────────────────────────────────────────────────────────

@require_http_methods(['GET'])
def api_scheduler_status(request):
    return JsonResponse(scheduler_manager.get_job_status())


@csrf_exempt
@require_http_methods(['POST'])
def api_scheduler_start(request):
    scheduler_manager.start_jobs()
    return JsonResponse({'status': 'success', 'message': '排程已啟動'})


@csrf_exempt
@require_http_methods(['POST'])
def api_scheduler_stop(request):
    scheduler_manager.stop_jobs()
    return JsonResponse({'status': 'success', 'message': '排程已停止'})


@csrf_exempt
@require_http_methods(['POST'])
def api_run_task(request):
    task = request.POST.get('task', '')
    if task == 'analyzer':
        subprocess.Popen(['python', 'manage.py', 'analyze_articles'])
        return JsonResponse({'status': 'success', 'message': '分析任務已在背景啟動'})
    if task == 'scraper':
        subprocess.Popen(['python', 'manage.py', 'scrape_bahamut'])
        return JsonResponse({'status': 'success', 'message': '爬蟲任務已在背景啟動'})
    return JsonResponse({'status': 'error', 'message': '未知的任務'}, status=400)


@require_http_methods(['GET'])
def api_scheduler_history(request):
    return JsonResponse(scheduler_manager.get_execution_history())
