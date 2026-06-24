import json
import os
import subprocess
from pathlib import Path

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings as django_settings

from .runner import SOURCE_META, reconcile_stale_runs


def _ctx(extra=None):
    keys = list(SOURCE_META.keys())
    ctx = {
        'sources':      keys,
        'sources_json': json.dumps(keys),
        'source_meta':  json.dumps(SOURCE_META),
    }
    if extra:
        ctx.update(extra)
    return ctx


def _get_platform_stats():
    """收集全平台健康數據，供儀表板使用"""
    stats = {}

    # ── NewsData 筆數（5 來源）
    try:
        from app_user_keyword_db.models import NewsData
        stats['news_total'] = NewsData.objects.count()
        from django.db.models import Count
        source_counts = dict(
            NewsData.objects.values_list('source').annotate(c=Count('item_id'))
        )
        stats['source_counts'] = source_counts
    except Exception:
        stats['news_total'] = 0
        stats['source_counts'] = {}

    # ── Article / Comment 筆數
    try:
        from app_comment_sentiment.models import Article, Comment
        stats['article_count'] = Article.objects.count()
        stats['comment_count'] = Comment.objects.count()
        stats['article_count_error'] = None
        stats['article_count_hint'] = (
            '目前尚未匯入巴哈 Article，請至後台執行「巴哈資料匯入」。'
            if stats['article_count'] == 0 else None
        )
    except Exception:
        stats['article_count'] = 0
        stats['comment_count'] = 0
        stats['article_count_error'] = '讀取 app_comment_sentiment 資料表失敗，請確認 migration 與 DB 狀態'
        stats['article_count_hint'] = '讀取資料時發生錯誤，請先檢查資料庫結構後再重試。'

    # ── YouTubeVideo 筆數
    try:
        from app_youtube_uma.models import YouTubeVideo
        stats['youtube_count'] = YouTubeVideo.objects.count()
    except Exception:
        stats['youtube_count'] = 0

    # ── YouTube 今日配額
    try:
        from app_youtube_uma.models import YouTubeQuotaLog
        from django.utils import timezone
        today = timezone.now().date()
        quota = YouTubeQuotaLog.objects.filter(date=today).first()
        stats['yt_quota_used'] = quota.units_used if quota else 0
        stats['yt_quota_limit'] = 10000
        stats['yt_quota_pct'] = round(stats['yt_quota_used'] / 100, 1)
    except Exception:
        stats['yt_quota_used'] = 0
        stats['yt_quota_limit'] = 10000
        stats['yt_quota_pct'] = 0

    # ── DiscordMessage 筆數
    try:
        from app_discord_bot.models import DiscordMessage, DiscordNewsLog
        from django.utils import timezone
        stats['discord_count'] = DiscordMessage.objects.count()
        stats['discord_uma'] = DiscordMessage.objects.filter(is_umamusume=True).count()
        today = timezone.now().date()
        stats['discord_news_today'] = DiscordNewsLog.objects.filter(
            created_at__date=today, status='sent'
        ).count()
    except Exception:
        stats['discord_count'] = 0
        stats['discord_uma'] = 0
        stats['discord_news_today'] = 0

    # ── FAISS 索引狀態
    index_path = Path(django_settings.BASE_DIR) / 'app_rag_uma' / 'index' / 'uma_knowledge.faiss'
    stats['rag_index_exists'] = index_path.exists()
    if stats['rag_index_exists']:
        size_kb = round(index_path.stat().st_size / 1024, 1)
        stats['rag_index_size_kb'] = size_kb
        import time
        stats['rag_index_mtime'] = time.strftime(
            '%Y-%m-%d %H:%M', time.localtime(index_path.stat().st_mtime)
        )
    else:
        stats['rag_index_size_kb'] = 0
        stats['rag_index_mtime'] = None

    # ── 知識庫文件數量
    kb_dir = Path(django_settings.BASE_DIR) / 'knowledge_base'
    if kb_dir.exists():
        stats['kb_file_count'] = len(list(kb_dir.glob('*.md')) + list(kb_dir.glob('*.txt')))
    else:
        stats['kb_file_count'] = 0

    # ── 最近一次爬蟲執行
    try:
        from .models import CrawlerRun
        last_run = CrawlerRun.objects.first()
        stats['last_run_source'] = last_run.source if last_run else None
        stats['last_run_status'] = last_run.status if last_run else None
        stats['last_run_at'] = (
            last_run.started_at.strftime('%Y-%m-%d %H:%M') if last_run else None
        )
    except Exception:
        stats['last_run_source'] = None
        stats['last_run_status'] = None
        stats['last_run_at'] = None

    return stats


def dashboard(request):
    reconcile_stale_runs()
    platform_stats = _get_platform_stats()
    return render(request, 'app_crawler_admin/dashboard.html',
                  _ctx({'platform_stats': platform_stats}))


def live_monitor(request, source):
    meta = SOURCE_META.get(source, {})
    return render(request, 'app_crawler_admin/live_monitor.html',
                  _ctx({'source': source, 'source_name': meta.get('name', source)}))


def schedule_page(request):
    return render(request, 'app_crawler_admin/schedule.html', _ctx())


def history_page(request):
    reconcile_stale_runs()
    return render(request, 'app_crawler_admin/history.html', _ctx())


def stats_page(request):
    return render(request, 'app_crawler_admin/stats.html', _ctx())


def settings_page(request):
    return render(request, 'app_crawler_admin/settings.html', _ctx())


# ── YouTube 管理頁 ─────────────────────────────────────────

def youtube_management(request):
    """YouTube API 配額管理 + 影片清單頁"""
    yt_videos = []
    yt_stats = {'total': 0, 'sentiment_avg': 0, 'quota_used': 0, 'quota_pct': 0}
    try:
        from app_youtube_uma.models import YouTubeVideo, YouTubeQuotaLog
        from django.db.models import Avg
        from django.utils import timezone
        yt_videos = list(YouTubeVideo.objects.order_by('-published_at')[:20].values(
            'video_id', 'title', 'channel_name', 'view_count', 'sentiment', 'published_at'
        ))
        yt_stats['total'] = YouTubeVideo.objects.count()
        avg = YouTubeVideo.objects.exclude(sentiment=None).aggregate(a=Avg('sentiment'))['a']
        yt_stats['sentiment_avg'] = round(avg * 100, 1) if avg else 0
        today = timezone.now().date()
        quota = YouTubeQuotaLog.objects.filter(date=today).first()
        yt_stats['quota_used'] = quota.units_used if quota else 0
        yt_stats['quota_pct'] = round(yt_stats['quota_used'] / 100, 1)
    except Exception:
        pass

    return render(request, 'app_crawler_admin/youtube.html',
                  _ctx({'yt_videos': yt_videos, 'yt_stats': yt_stats}))


# ── Discord Bot 管理頁 ─────────────────────────────────────

def discord_management(request):
    """Discord Bot 狀態 + 設定 + 推播歷史（整合版）"""
    discord_data = {
        'total_messages': 0,
        'uma_messages':   0,
        'unclassified':   0,
        'news_logs':      [],
        'configs':        [],
        'recent_messages': [],
        'news_today':     0,
        'news_model':     os.getenv('DISCORD_NEWS_MODEL', 'gemini'),
        'bot_token_set':  bool(os.getenv('DISCORD_BOT_TOKEN')),
    }
    try:
        from app_discord_bot.models import DiscordMessage, DiscordBotConfig, DiscordNewsLog
        from django.utils import timezone
        discord_data['total_messages'] = DiscordMessage.objects.count()
        discord_data['uma_messages']   = DiscordMessage.objects.filter(is_umamusume=True).count()
        discord_data['unclassified']   = DiscordMessage.objects.filter(is_umamusume=None).count()
        discord_data['news_logs']      = list(DiscordNewsLog.objects.order_by('-created_at')[:10])
        discord_data['configs']        = list(DiscordBotConfig.objects.order_by('channel_type', 'name'))
        discord_data['recent_messages'] = list(
            DiscordMessage.objects.order_by('-timestamp')[:20]
        )
        today = timezone.now().date()
        discord_data['news_today'] = DiscordNewsLog.objects.filter(
            created_at__date=today, status='sent'
        ).count()
    except Exception:
        pass

    return render(request, 'app_crawler_admin/discord.html',
                  _ctx({'discord_data': discord_data}))


# ── RAG 知識庫管理頁 ──────────────────────────────────────

def rag_management(request):
    """RAG 索引狀態 + 知識庫文件清單"""
    rag_data = {
        'index_exists': False,
        'index_size_kb': 0,
        'index_mtime': None,
        'vector_count': 0,
        'kb_files': [],
    }
    base = Path(django_settings.BASE_DIR)
    index_path = base / 'app_rag_uma' / 'index' / 'uma_knowledge.faiss'
    if index_path.exists():
        import time
        rag_data['index_exists'] = True
        rag_data['index_size_kb'] = round(index_path.stat().st_size / 1024, 1)
        rag_data['index_mtime'] = time.strftime(
            '%Y-%m-%d %H:%M', time.localtime(index_path.stat().st_mtime)
        )
        # 嘗試讀取向量數量
        try:
            import faiss
            idx = faiss.read_index(str(index_path))
            rag_data['vector_count'] = idx.ntotal
        except Exception:
            rag_data['vector_count'] = '?'

    kb_dir = base / 'knowledge_base'
    if kb_dir.exists():
        rag_data['kb_files'] = [
            {
                'name': f.name,
                'size_kb': round(f.stat().st_size / 1024, 1),
            }
            for f in sorted(kb_dir.iterdir())
            if f.suffix in ('.md', '.txt', '.pdf')
        ]

    return render(request, 'app_crawler_admin/rag.html',
                  _ctx({'rag_data': rag_data}))


# ── Pipeline 分步執行頁 ───────────────────────────────────

def pipeline_page(request):
    """Pipeline 分步執行頁（F1）"""
    reconcile_stale_runs()
    try:
        from .models import CrawlerRun
        recent_runs = list(
            CrawlerRun.objects.order_by('-started_at')[:15].values(
                'run_id', 'source', 'status', 'started_at', 'ended_at',
                'articles_new', 'articles_err', 'triggered_by'
            )
        )
    except Exception:
        recent_runs = []
    return render(request, 'app_crawler_admin/pipeline.html',
                  _ctx({'recent_runs': recent_runs}))


def data_manager(request):
    """資料管理頁 — DB 化遷移計畫 Phase 1（/crawler-admin/data-manager/）"""
    return render(request, 'app_crawler_admin/data_manager.html', _ctx())


def ai_news_management(request):
    """AI 新聞生成與發布管理頁"""
    from app_user_keyword_llm_report.models import GeneratedNewsArticle

    latest_news = list(
        GeneratedNewsArticle.objects.order_by('-created_at')[:20].values(
            'id', 'title', 'query', 'status', 'created_at'
        )
    )
    return render(
        request,
        'app_crawler_admin/ai_news.html',
        _ctx({'latest_ai_news': latest_news}),
    )
