"""
api_views.py — 爬蟲後台 REST API（JSON）

所有端點均以 /crawler-admin/api/ 為前綴。
以短 polling 方案實作（Phase B），不依賴 WebSocket。
"""
import contextlib
import io
import json
import os
import threading
import time
import traceback
from datetime import datetime, timezone

from django.db import OperationalError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .runner import (SOURCE_META, trigger, stop, get_status, get_log, is_ready,
                     reconcile_stale_runs)
from .models import CrawlerRun, CrawlerSchedule, CrawlerConfig


# ── 工具函式 ─────────────────────────────────────────────

def _parse_bool(value, default=False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'yes', 'on'}
    return default


def _parse_int(value, default: int, min_value: int | None = None, max_value: int | None = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    if min_value is not None:
        parsed = max(min_value, parsed)
    if max_value is not None:
        parsed = min(max_value, parsed)
    return parsed


def _parse_float(value, default: float, min_value: float | None = None, max_value: float | None = None) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if min_value is not None:
        parsed = max(min_value, parsed)
    if max_value is not None:
        parsed = min(max_value, parsed)
    return parsed


def _run_with_sqlite_retry(fn, attempts: int = 3, delay_s: float = 0.15):
    """
    SQLite 在背景任務寫入時偶發 database is locked；
    這裡做短暫重試，降低前端操作失敗率。
    """
    last_error = None
    for i in range(attempts):
        try:
            return fn()
        except OperationalError as e:
            last_error = e
            if 'database is locked' not in str(e).lower() or i == attempts - 1:
                raise
            time.sleep(delay_s)
    if last_error:
        raise last_error

def _run_to_dict(run: CrawlerRun) -> dict:
    return {
        'run_id':       run.run_id,
        'source':       run.source,
        'status':       run.status,
        'triggered_by': run.triggered_by,
        'started_at':   run.started_at.strftime('%Y-%m-%d %H:%M:%S') if run.started_at else None,
        'ended_at':     run.ended_at.strftime('%Y-%m-%d %H:%M:%S') if run.ended_at else None,
        'articles_new':  run.articles_new,
        'articles_skip': run.articles_skip,
        'articles_err':  run.articles_err,
        'duration_s':   run.duration_seconds(),
    }


def _source_summary(source: str) -> dict:
    """組合單一來源的完整摘要（供儀表板用）"""
    ready = is_ready(source)
    st    = get_status(source) if ready else None
    last  = CrawlerRun.objects.filter(source=source).first()
    meta  = SOURCE_META[source]

    # 從 DB 計算文章數（若有 NewsData）
    total_articles = 0
    try:
        from app_user_keyword_db.models import NewsData
        total_articles = NewsData.objects.filter(source=source).count()
    except Exception:
        pass

    return {
        'source':          source,
        'name':            meta['name'],
        'label':           meta['label'],
        'ready':           ready,
        'status':          (st['status'] if st else 'not_ready'),
        'run_id':          (st['run_id'] if st else None),
        'total_articles':  total_articles,
        'last_run_at':     last.started_at.strftime('%Y-%m-%d %H:%M') if last else None,
        'last_status':     last.status if last else None,
        'articles_new':    st['articles_new']  if st and st['status'] == 'running' else (last.articles_new  if last else 0),
        'articles_err':    st['articles_err']  if st and st['status'] == 'running' else (last.articles_err  if last else 0),
    }


# ── API: 全部來源狀態 ─────────────────────────────────────

def api_status_all(request):
    # 先收尾伺服器重啟/重載遺留的孤兒 running 記錄，確保儀表板狀態真實
    reconcile_stale_runs()
    data = [_source_summary(src) for src in SOURCE_META]
    return JsonResponse({'sources': data})


def api_status_one(request, source):
    if source not in SOURCE_META:
        return JsonResponse({'error': '未知來源'}, status=404)
    st = get_status(source)
    st['log_tail'] = get_log(source)[-100:]
    return JsonResponse(st)


# ── API: 觸發 / 停止 ──────────────────────────────────────

@csrf_exempt
@require_http_methods(['POST'])
def api_trigger(request, source):
    if source == 'all':
        results = {}
        for src in SOURCE_META:
            results[src] = trigger(src)
        return JsonResponse({'results': results})

    if source not in SOURCE_META:
        return JsonResponse({'error': '未知來源'}, status=404)

    result = trigger(source)
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(['POST'])
def api_stop(request, source):
    if source not in SOURCE_META:
        return JsonResponse({'error': '未知來源'}, status=404)
    result = stop(source)
    return JsonResponse(result)


# ── API: log ─────────────────────────────────────────────

def api_log(request, source):
    if source not in SOURCE_META:
        return JsonResponse({'error': '未知來源'}, status=404)
    offset = _parse_int(request.GET.get('offset', 0), default=0, min_value=0)
    lines  = get_log(source)
    return JsonResponse({'lines': lines[offset:], 'total': len(lines)})


# ── API: 執行歷史 ─────────────────────────────────────────

def api_history(request):
    # 進入歷史頁前先校正孤兒 running 記錄，避免顯示永遠「運行中」的假狀態
    reconcile_stale_runs()
    source = request.GET.get('source', '')
    status = request.GET.get('status', '')
    limit = _parse_int(request.GET.get('limit', 30), default=30, min_value=1, max_value=100)

    qs = CrawlerRun.objects.all()
    if source:
        qs = qs.filter(source=source)
    if status:
        qs = qs.filter(status=status)
    qs = qs[:limit]

    runs = [_run_to_dict(r) for r in qs]
    return JsonResponse({'runs': runs})


def api_history_detail(request, run_id):
    try:
        run = CrawlerRun.objects.get(run_id=run_id)
    except CrawlerRun.DoesNotExist:
        return JsonResponse({'error': '找不到記錄'}, status=404)
    data = _run_to_dict(run)
    data['log_text'] = run.log_text
    return JsonResponse(data)


# ── API: 排程管理 ─────────────────────────────────────────

def api_schedule_list(request):
    schedules = list(CrawlerSchedule.objects.values())
    return JsonResponse({'schedules': schedules})


@csrf_exempt
def api_schedule_save(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': '無效 JSON'}, status=400)

        source = (body.get('source') or '').strip()
        mode = (body.get('mode') or 'daily').strip()
        raw_cron = body.get('cron_expr', None)
        cron_expr = '0 2 * * *' if raw_cron is None else str(raw_cron).strip()
        enabled = _parse_bool(body.get('enabled', True), default=True)

        if source not in SOURCE_META:
            return JsonResponse({'error': '未知來源'}, status=400)
        if mode not in {'daily', 'weekly', 'interval'}:
            return JsonResponse({'error': f'不支援的 mode: {mode}'}, status=400)
        # 若前端明確傳入空字串，應視為錯誤而非默默改預設值
        if raw_cron is not None and not cron_expr:
            return JsonResponse({'error': 'cron_expr 不可為空'}, status=400)

        try:
            obj, created = _run_with_sqlite_retry(
                lambda: CrawlerSchedule.objects.update_or_create(
            source=source,
            defaults={'mode': mode, 'cron_expr': cron_expr, 'enabled': enabled}
        )
            )
        except OperationalError:
            return JsonResponse({'error': '資料庫忙碌中，請稍後重試'}, status=503)
        # 更新 APScheduler
        try:
            from .scheduler import add_or_update_job
            add_or_update_job(obj)
        except Exception:
            pass
        return JsonResponse({'ok': True, 'created': created,
                             'schedule': {'source': obj.source, 'mode': obj.mode,
                                          'cron_expr': obj.cron_expr, 'enabled': obj.enabled}})

    return JsonResponse({'error': '只支援 POST'}, status=405)


@csrf_exempt
@require_http_methods(['POST', 'DELETE'])
def api_schedule_delete(request, source):
    if source not in SOURCE_META:
        return JsonResponse({'error': '未知來源'}, status=404)
    try:
        deleted, _ = _run_with_sqlite_retry(lambda: CrawlerSchedule.objects.filter(source=source).delete())
    except OperationalError:
        return JsonResponse({'error': '資料庫忙碌中，請稍後重試'}, status=503)
    try:
        from .scheduler import remove_job
        remove_job(source)
    except Exception:
        pass
    return JsonResponse({'ok': True, 'deleted': deleted})


# ── API: 爬蟲設定 ─────────────────────────────────────────

def api_config_get(request, source):
    if source not in SOURCE_META:
        return JsonResponse({'error': '未知來源'}, status=404)
    cfg, _ = CrawlerConfig.objects.get_or_create(
        source=source,
        defaults={'max_pages': 50, 'delay_min': 0.8, 'delay_max': 1.5}
    )
    return JsonResponse({
        'source':         cfg.source,
        'max_pages':      cfg.max_pages,
        'delay_min':      cfg.delay_min,
        'delay_max':      cfg.delay_max,
        'use_playwright': cfg.use_playwright,
        'user_agent':     cfg.user_agent,
        'extra_notes':    cfg.extra_notes,
    })


@csrf_exempt
@require_http_methods(['POST'])
def api_config_save(request, source):
    if source not in SOURCE_META:
        return JsonResponse({'error': '未知來源'}, status=404)
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': '無效 JSON'}, status=400)

    try:
        cfg, _ = _run_with_sqlite_retry(lambda: CrawlerConfig.objects.get_or_create(source=source))
    except OperationalError:
        return JsonResponse({'error': '資料庫忙碌中，請稍後重試'}, status=503)

    if 'max_pages' in body:
        cfg.max_pages = _parse_int(body['max_pages'], default=cfg.max_pages, min_value=0, max_value=5000)
    if 'delay_min' in body:
        cfg.delay_min = _parse_float(body['delay_min'], default=cfg.delay_min, min_value=0.0, max_value=60.0)
    if 'delay_max' in body:
        cfg.delay_max = _parse_float(body['delay_max'], default=cfg.delay_max, min_value=0.0, max_value=60.0)
    if cfg.delay_max < cfg.delay_min:
        return JsonResponse({'error': 'delay_max 不可小於 delay_min'}, status=400)
    if 'use_playwright' in body:
        cfg.use_playwright = _parse_bool(body['use_playwright'], default=cfg.use_playwright)
    if 'user_agent' in body:
        cfg.user_agent = str(body['user_agent'] or '')
    if 'extra_notes' in body:
        cfg.extra_notes = str(body['extra_notes'] or '')
    try:
        _run_with_sqlite_retry(lambda: cfg.save())
    except OperationalError:
        return JsonResponse({'error': '資料庫忙碌中，請稍後重試'}, status=503)
    return JsonResponse({
        'ok': True,
        'config': {
            'source': cfg.source,
            'max_pages': cfg.max_pages,
            'delay_min': cfg.delay_min,
            'delay_max': cfg.delay_max,
            'use_playwright': cfg.use_playwright,
            'user_agent': cfg.user_agent,
            'extra_notes': cfg.extra_notes,
        }
    })


# ── API: 來源統計（與主站共用端點橋接） ──────────────────

def api_stats(request):
    """各來源文章數統計，供 M5 統計圖表使用"""
    result = {}
    try:
        from app_user_keyword_db.models import NewsData
        from django.db.models import Count
        qs = NewsData.objects.values('source').annotate(count=Count('item_id'))
        for row in qs:
            result[row['source']] = row['count']
    except Exception:
        pass
    all_sources = set(SOURCE_META.keys()) | set(result.keys())
    return JsonResponse({'stats': result, 'sources': sorted(all_sources)})


# ── API: 新增（C-AD 統一儀表板）─────────────────────────

def api_source_stats(request):
    """各來源 NewsData 筆數，供儀表板長條圖使用"""
    result = {}
    total = 0
    try:
        from app_user_keyword_db.models import NewsData
        from django.db.models import Count
        qs = NewsData.objects.values('source').annotate(count=Count('item_id'))
        for row in qs:
            result[row['source']] = row['count']
            total += row['count']
    except Exception:
        pass
    all_sources = sorted(set(SOURCE_META.keys()) | set(result.keys()))
    return JsonResponse({'sources': result, 'total': total, 'all_sources': all_sources})


def api_sentiment_stats(request):
    """全資料庫情感分布（Positive/Neutral/Negative），供圓餅圖使用"""
    pos = neu = neg = 0
    try:
        from app_user_keyword_db.models import NewsData
        from django.db.models import Count
        qs = NewsData.objects.exclude(sentiment=None)
        for item in qs.iterator():
            s = item.sentiment
            if s is None:
                continue
            if s >= 0.6:
                pos += 1
            elif s <= 0.4:
                neg += 1
            else:
                neu += 1
    except Exception:
        pass
    return JsonResponse({'positive': pos, 'neutral': neu, 'negative': neg,
                         'total': pos + neu + neg})


def api_platform_stats(request):
    """全平台健康統計，供儀表板 AJAX 刷新"""
    from .views import _get_platform_stats
    return JsonResponse(_get_platform_stats())


# ── API: 留言情感排程（移轉自前台）──────────────────────────

def api_comment_scheduler_status(request):
    """留言情感排程狀態"""
    try:
        from app_comment_sentiment import scheduler_manager
        return JsonResponse(scheduler_manager.get_job_status())
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def api_comment_scheduler_start(request):
    """啟動留言情感排程"""
    try:
        from app_comment_sentiment import scheduler_manager
        scheduler_manager.start_jobs()
        return JsonResponse({'status': 'success', 'message': '留言情感排程已啟動'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def api_comment_scheduler_stop(request):
    """停止留言情感排程"""
    try:
        from app_comment_sentiment import scheduler_manager
        scheduler_manager.stop_jobs()
        return JsonResponse({'status': 'success', 'message': '留言情感排程已停止'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def api_comment_scheduler_run_task(request):
    """手動執行留言情感任務（scraper / analyzer）"""
    from django.conf import settings as django_settings
    import subprocess
    import sys

    task = request.POST.get('task', '').strip()
    if not task:
        try:
            body = json.loads(request.body or '{}')
            task = str(body.get('task', '')).strip()
        except Exception:
            task = ''

    if task == 'analyzer':
        command = 'analyze_comments'
        message = '留言情感分析任務已在背景啟動'
    elif task == 'scraper':
        command = 'scrape_bahamut'
        message = '巴哈匯入任務已在背景啟動'
    else:
        return JsonResponse({'status': 'error', 'message': '未知任務，僅支援 scraper / analyzer'}, status=400)

    try:
        subprocess.Popen(
            [sys.executable, 'manage.py', command],
            cwd=str(django_settings.BASE_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return JsonResponse({'status': 'success', 'message': message, 'task': task})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


def api_comment_scheduler_history(request):
    """留言情感排程執行歷史"""
    try:
        from app_comment_sentiment import scheduler_manager
        return JsonResponse(scheduler_manager.get_execution_history())
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def api_import_bahamut_articles(request):
    """手動觸發巴哈 Article 匯入（可選擇先爬再匯）"""
    from django.conf import settings as django_settings
    import subprocess
    import sys

    crawl_first = _parse_bool(request.POST.get('crawl', False), default=False)
    cmd = [sys.executable, 'manage.py', 'scrape_bahamut']
    if crawl_first:
        cmd.append('--crawl')

    try:
        subprocess.Popen(
            cmd,
            cwd=str(django_settings.BASE_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return JsonResponse({
            'status': 'started',
            'message': '巴哈 Article 匯入任務已啟動',
            'crawl': crawl_first,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ── API: RAG 管理（E1-E2）────────────────────────────────

def api_rag_status(request):
    """RAG 索引狀態"""
    from pathlib import Path
    from django.conf import settings as django_settings
    index_path = Path(django_settings.BASE_DIR) / 'app_rag_uma' / 'index' / 'uma_knowledge.faiss'
    exists = index_path.exists()
    size_kb = 0
    mtime = None
    vector_count = 0
    if exists:
        import time
        size_kb = round(index_path.stat().st_size / 1024, 1)
        mtime = time.strftime('%Y-%m-%d %H:%M', time.localtime(index_path.stat().st_mtime))
        try:
            import faiss
            idx = faiss.read_index(str(index_path))
            vector_count = idx.ntotal
        except Exception:
            vector_count = -1

    kb_dir = Path(django_settings.BASE_DIR) / 'knowledge_base'
    kb_files = []
    if kb_dir.exists():
        kb_files = [f.name for f in sorted(kb_dir.iterdir()) if f.suffix in ('.md', '.txt', '.pdf')]

    return JsonResponse({
        'index_exists': exists,
        'index_size_kb': size_kb,
        'last_built': mtime,
        'vector_count': vector_count,
        'kb_files': kb_files,
    })


@csrf_exempt
@require_http_methods(['POST'])
def api_rebuild_rag(request):
    """觸發 RAG 索引重建（非同步 subprocess）"""
    import subprocess
    import sys
    from django.conf import settings as django_settings
    from pathlib import Path
    script = Path(django_settings.BASE_DIR) / 'app_rag_uma' / 'build_index.py'
    if not script.exists():
        return JsonResponse({'error': 'build_index.py 不存在'}, status=404)
    try:
        subprocess.Popen(
            [sys.executable, str(script)],
            cwd=str(django_settings.BASE_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return JsonResponse({'status': 'started'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ── API: YouTube 管理（B1-B5）───────────────────────────

def api_youtube_quota(request):
    """今日 YouTube API 配額使用量"""
    try:
        from app_youtube_uma.models import YouTubeQuotaLog
        from django.utils import timezone
        today = timezone.now().date()
        quota, _ = YouTubeQuotaLog.objects.get_or_create(
            date=today,
            defaults={'units_used': 0, 'units_limit': 10000}
        )
        return JsonResponse({
            'date': str(quota.date),
            'units_used': quota.units_used,
            'units_limit': quota.units_limit,
            'percent': quota.percent,
            'last_crawl_at': quota.last_crawl_at.strftime('%Y-%m-%d %H:%M') if quota.last_crawl_at else None,
            'videos_added': quota.videos_added,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def api_youtube_crawl(request):
    """手動觸發 YouTube 爬取（非同步）"""
    import subprocess
    import sys
    from django.conf import settings as django_settings
    try:
        subprocess.Popen(
            [sys.executable, 'manage.py', 'crawl_youtube', '--max-videos', '20'],
            cwd=str(django_settings.BASE_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return JsonResponse({'status': 'started', 'job_id': 'crawl_youtube_manual'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ── API: Pipeline 執行（F1）──────────────────────────────

@csrf_exempt
@require_http_methods(['POST'])
def api_upload_kb(request):
    """上傳知識庫文件到 knowledge_base/"""
    from django.conf import settings as django_settings
    from pathlib import Path
    ALLOWED_EXT = {'.md', '.txt', '.pdf'}
    kb_dir = Path(django_settings.BASE_DIR) / 'knowledge_base'
    kb_dir.mkdir(exist_ok=True)

    uploaded = request.FILES.get('kb_file')
    if not uploaded:
        return JsonResponse({'error': '未收到文件'}, status=400)

    suffix = Path(uploaded.name).suffix.lower()
    if suffix not in ALLOWED_EXT:
        return JsonResponse({'error': f'不支援的文件類型 {suffix}，請使用 .md/.txt/.pdf'}, status=400)

    target = kb_dir / uploaded.name
    with open(target, 'wb') as f:
        for chunk in uploaded.chunks():
            f.write(chunk)

    return JsonResponse({'ok': True, 'filename': uploaded.name})


# 步驟 1 為「爬取 5 來源」，較特殊（多支腳本），此處逐支列出
PIPELINE_STEP1_SCRIPTS = [
    'pipeline/crawl_bilibili_uma.py',
    'pipeline/crawl_bahamut_uma.py',
    'pipeline/crawl_ettoday_uma.py',
    'pipeline/crawl_udn_uma.py',
    'pipeline/crawl_gamme_uma.py',
]

PIPELINE_STEPS = {
    # (label, script_rel, extra_args)
    1: ('爬取 5 來源 raw 資料',               None,                                        []),
    2: ('合併前處理（preprocess.py）',         'pipeline/preprocess.py',                   []),
    3: ('Gemini 情感標記（label_sentiment.py）', 'pipeline/label_sentiment.py',             []),
    4: ('生成熱門 CSV',                       'scripts/generate_topkey_csv.py',            []),
    5: ('清空網路來源 DB 並重新匯入',           'scripts/import_uma_data.py',               ['--clear']),
    6: ('Discord 訊息整合入庫',               'scripts/convert_discord_to_newsdata.py',    []),
    7: ('YouTube 影片整合入庫',               'scripts/convert_youtube_to_newsdata.py',    []),
}


# ── Pipeline 執行狀態（模組級，供背景執行緒與輪詢端點共享）─────────
import threading as _threading

_pipeline_lock  = _threading.Lock()
_pipeline_state = {
    'running':     False,
    'steps':       [],     # [{'step', 'label', 'status', 'tail', 'returncode', ...}]
    'started_at':  None,
    'finished_at': None,
}

PIPELINE_STEP_EST_SECONDS = {
    1: 45 * 60,  # 5 來源重爬，受網路波動影響大
    2: 5 * 60,
    3: 14 * 60,
    4: 3 * 60,
    5: 3 * 60,
    6: 1 * 60,   # Discord 增量轉換
    7: 1 * 60,   # YouTube 增量轉換
}


def _pipeline_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _pipeline_append_log(item: dict, text: str, max_chars: int = 12000):
    """將增量輸出追加到 step tail，保留最後 max_chars。"""
    if text is None:
        return
    merged = (item.get('tail') or '')
    if merged:
        merged += '\n'
    merged += str(text).rstrip('\r\n')
    if len(merged) > max_chars:
        merged = merged[-max_chars:]
    item['tail'] = merged
    item['log_updated_at'] = _pipeline_now_iso()


def _pipeline_parse_iso(iso_text: str | None):
    if not iso_text:
        return None
    try:
        return datetime.fromisoformat(iso_text)
    except Exception:
        return None


def _pipeline_step_progress(item: dict, now_dt: datetime) -> int:
    """依狀態與估計秒數回傳單步預估進度（0~100）。"""
    status = item.get('status')
    if status in {'success', 'failed'}:
        return 100
    if status != 'running':
        return 0
    est = max(30, int(item.get('est_seconds') or 60))
    started_dt = _pipeline_parse_iso(item.get('started_at'))
    if not started_dt:
        return 3
    elapsed = max(0.0, (now_dt - started_dt).total_seconds())
    # 執行中上限 95%，留給完成瞬間跳 100%
    return max(3, min(95, int((elapsed / est) * 100)))


def _pipeline_state_snapshot() -> dict:
    """輸出帶估計進度的狀態快照（供前端輪詢）。"""
    import copy

    with _pipeline_lock:
        state = copy.deepcopy(_pipeline_state)

    now_dt = datetime.now(tz=timezone.utc)
    steps = state.get('steps') or []
    total_weight = 0.0
    done_weight = 0.0
    remaining_s = 0.0
    running_step = None

    for item in steps:
        est = max(30, int(item.get('est_seconds') or 60))
        total_weight += est
        step_pct = _pipeline_step_progress(item, now_dt)
        item['progress_pct'] = step_pct

        status = item.get('status')
        if status in {'success', 'failed'}:
            done_weight += est
        elif status == 'running':
            running_step = item.get('step')
            done_weight += est * (step_pct / 100.0)
            remaining_s += est * (1 - (step_pct / 100.0))
        else:
            remaining_s += est

    if total_weight <= 0:
        overall_pct = 0
    else:
        overall_pct = int((done_weight / total_weight) * 100)

    if not state.get('running') and steps:
        overall_pct = 100
        remaining_s = 0

    state['progress_pct'] = max(0, min(100, overall_pct))
    state['estimated_remaining_s'] = int(max(0, remaining_s))
    state['running_step'] = running_step
    state['step_count'] = len(steps)
    return state


def _pipeline_run_script(script_rel, base, on_update=None, extra_args=None):
    """
    以 UTF-8 環境執行單支腳本（增量讀取），回傳 (returncode, tail_text)。

    on_update:  callable(line_text) -> None，可於執行中接收逐行輸出。
    extra_args: 額外命令列引數清單，例如 ['--clear']。
    """
    import subprocess
    import sys
    from pathlib import Path

    script = Path(base) / script_rel
    if not script.exists():
        return 127, f'[錯誤] 腳本不存在：{script_rel}'

    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'   # 避免 Windows cp950 列印中文時崩潰
    env['PYTHONUTF8'] = '1'

    # 單步最長 1 小時，避免永久卡死
    timeout_s = 60 * 60
    lines = []
    pending = ''
    captured = ''

    def _consume_delta(delta_text: str):
        nonlocal pending
        if not delta_text:
            return
        text = pending + delta_text
        parts = text.splitlines(keepends=True)
        pending = ''
        for part in parts:
            if part.endswith('\n') or part.endswith('\r'):
                line = part.rstrip('\r\n')
                lines.append(line)
                if on_update:
                    on_update(line)
            else:
                pending = part

    cmd = [sys.executable, str(script)] + (list(extra_args) if extra_args else [])
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(base),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
        )
        started = time.monotonic()
        while True:
            elapsed = time.monotonic() - started
            if elapsed >= timeout_s:
                proc.kill()
                lines.append('[逾時] 此步驟超過 1 小時仍未完成，已中止。')
                if on_update:
                    on_update(lines[-1])
                return 124, '\n'.join(lines[-120:])

            try:
                out, _ = proc.communicate(timeout=1.0)
                out = out or ''
                if len(out) > len(captured):
                    delta = out[len(captured):]
                    _consume_delta(delta)
                    captured = out
                break
            except subprocess.TimeoutExpired as exc:
                out = (exc.output or '')
                if len(out) > len(captured):
                    delta = out[len(captured):]
                    _consume_delta(delta)
                    captured = out
                continue

        if pending:
            line = pending.rstrip('\r\n')
            lines.append(line)
            if on_update:
                on_update(line)

        return proc.returncode, '\n'.join(lines[-120:])
    except Exception as exc:
        return 1, f'[例外] {exc}'


def _pipeline_worker(steps):
    """背景執行緒：依序執行選定步驟，並即時更新 _pipeline_state。"""
    from django.conf import settings as django_settings
    base = django_settings.BASE_DIR

    try:
        for item in _pipeline_state['steps']:
            step_num = item['step']

            def _push_line(line_text: str, _item=item):
                with _pipeline_lock:
                    _pipeline_append_log(_item, line_text)

            with _pipeline_lock:
                item['status'] = 'running'
                item['started_at'] = _pipeline_now_iso()
                item['finished_at'] = None
                item['returncode'] = None
                item['tail'] = ''
                _pipeline_append_log(item, f'▶ Step {step_num} 開始：{item["label"]}')

            if step_num == 1:
                # 爬取 5 來源：逐支執行，全部成功才算成功
                rc_total, tails = 0, []
                for sc in PIPELINE_STEP1_SCRIPTS:
                    with _pipeline_lock:
                        _pipeline_append_log(item, f'$ {os.path.basename(sc)}')
                    rc, tail = _pipeline_run_script(
                        sc,
                        base,
                        on_update=_push_line,
                    )
                    tails.append(f'$ {os.path.basename(sc)} (rc={rc})\n{tail}')
                    if rc != 0:
                        rc_total = rc
                rc, tail = rc_total, '\n\n'.join(tails)
            else:
                _label, script_rel, step_extra_args = PIPELINE_STEPS[step_num]
                rc, tail = _pipeline_run_script(
                    script_rel,
                    base,
                    on_update=_push_line,
                    extra_args=step_extra_args,
                )

            with _pipeline_lock:
                item['returncode'] = rc
                if tail:
                    item['tail'] = tail[-12000:]
                item['finished_at'] = _pipeline_now_iso()
                item['status'] = 'success' if rc == 0 else 'failed'
                _pipeline_append_log(
                    item,
                    f'{"✅" if rc == 0 else "❌"} Step {step_num} 結束（rc={rc}）'
                )
    finally:
        with _pipeline_lock:
            _pipeline_state['running'] = False
            _pipeline_state['finished_at'] = _pipeline_now_iso()


@csrf_exempt
@require_http_methods(['POST'])
def api_run_pipeline(request):
    """
    觸發 Pipeline 分步執行（背景執行緒、依序、可輪詢）。
    若已有一輪執行進行中則回 409，避免重複觸發。
    """
    import json as _json

    try:
        body  = _json.loads(request.body)
        steps = body.get('steps', [2, 3])
    except Exception:
        steps = [2, 3]

    steps = [s for s in steps if s in PIPELINE_STEPS]
    if not steps:
        return JsonResponse({'error': '未選擇有效步驟'}, status=400)

    with _pipeline_lock:
        if _pipeline_state['running']:
            return JsonResponse(
                {'error': '已有一輪 Pipeline 正在執行中，請待其完成。',
                 'state': _pipeline_state},
                status=409,
            )
        _pipeline_state['running']     = True
        _pipeline_state['started_at']  = _pipeline_now_iso()
        _pipeline_state['finished_at'] = None
        _pipeline_state['steps'] = [
            {'step': s, 'label': PIPELINE_STEPS[s][0],
             'status': 'pending', 'tail': '', 'returncode': None,
             'started_at': None, 'finished_at': None,
             'est_seconds': PIPELINE_STEP_EST_SECONDS.get(s, 180),
             'log_updated_at': None}
            for s in steps
        ]

    t = _threading.Thread(target=_pipeline_worker, args=(steps,), daemon=True)
    t.start()

    return JsonResponse({'status': 'started', 'steps': steps})


def api_pipeline_status(request):
    """回傳目前 Pipeline 執行狀態（供前端輪詢）。"""
    return JsonResponse(_pipeline_state_snapshot())


# ── API: 資料清理（G1 — 重複/舊格式檔案管理）────────────────

def _canonical_raw_header() -> str:
    """統一 raw CSV 規格的標準表頭。"""
    return 'item_id|source|date|category|title|content|link|photo_link'


def _stale_file_specs():
    """
    回傳可安全刪除的「舊格式 / 重複」檔案規格清單。

    每筆: (相對路徑, 類別, 說明)
    僅列出與 data/processed 或 data/raw 正典資料重複、
    或為遷移前殘留的中間檔；絕不含 data/ 目錄下的正典資料與 參考專案/。
    """
    return [
        # 路徑遷移前殘留於 pipeline/ 的 raw 與中間檔
        ('pipeline/bilibili_uma_raw.csv',         'duplicate_raw',   'P1 路徑遷移前殘留（已移至 data/raw/）'),
        ('pipeline/bahamut_uma_raw.csv',          'duplicate_raw',   'P2 路徑遷移前殘留（已移至 data/raw/）'),
        ('pipeline/bilibili_uma_preprocessed.csv','stale_intermediate', '舊版單來源前處理中間檔（已被多來源管線取代）'),
        ('pipeline/bilibili_uma_tokenized.csv',   'stale_intermediate', '舊版單來源斷詞中間檔（已被多來源管線取代）'),
        ('pipeline/pk_uma_characters.csv',        'duplicate_dataset', '與 data/processed/pk_uma_characters.csv 重複'),
        ('pipeline/uma_characters_bilingual.csv', 'duplicate_dataset', '與 data/processed/ 重複'),
        # 散落於各 app dataset/ 的過時副本（views 應改讀 services.news_service）
        ('app_user_keyword/dataset/uma_news_preprocessed.csv',          'stale_app_copy', '過時分散副本（正典在 data/processed/）'),
        ('app_user_keyword_sentiment/dataset/uma_news_preprocessed.csv','stale_app_copy', '過時分散副本（正典在 data/processed/）'),
        ('app_character_pk/dataset/pk_uma_characters.csv',              'stale_app_copy', '過時分散副本（正典在 data/processed/）'),
        ('app_uma_top_keyword/dataset/uma_topkey_with_category.csv',    'stale_app_copy', '過時分散副本（正典在 data/processed/）'),
        ('app_uma_top_character/dataset/uma_top_character_with_category.csv', 'stale_app_copy', '過時分散副本（正典在 data/processed/）'),
    ]


def api_data_inventory(request):
    """
    資料盤點：列出 raw CSV 格式狀態 + 可清理的重複/舊檔清單。
    供「資料清理」UI 顯示，不執行任何刪除。
    """
    from pathlib import Path
    from django.conf import settings as dj_settings

    base = Path(dj_settings.BASE_DIR)
    target_header = _canonical_raw_header()

    # ── 各來源 raw CSV 格式檢查 ──
    raw_status = []
    for src in SOURCE_META:
        path = base / 'data' / 'raw' / f'{src}_uma_raw.csv'
        entry = {'source': src, 'exists': path.exists(),
                 'format_ok': False, 'header': None,
                 'size_kb': 0, 'mtime': None}
        if path.exists():
            import time
            stat = path.stat()
            entry['size_kb'] = round(stat.st_size / 1024, 1)
            entry['mtime'] = time.strftime('%Y-%m-%d %H:%M', time.localtime(stat.st_mtime))
            try:
                with open(path, encoding='utf-8-sig') as f:
                    header = f.readline().strip()
                entry['header'] = header
                entry['format_ok'] = header.startswith(target_header)
            except Exception:
                pass
        raw_status.append(entry)

    # ── 可清理檔案盤點 ──
    cleanup = []
    total_kb = 0.0
    for rel, kind, note in _stale_file_specs():
        path = base / rel
        if path.exists():
            import time
            stat = path.stat()
            size_kb = round(stat.st_size / 1024, 1)
            total_kb += size_kb
            cleanup.append({
                'path': rel, 'kind': kind, 'note': note,
                'size_kb': size_kb,
                'mtime': time.strftime('%Y-%m-%d %H:%M', time.localtime(stat.st_mtime)),
            })

    return JsonResponse({
        'target_header': target_header,
        'raw_status': raw_status,
        'cleanup_files': cleanup,
        'cleanup_total_kb': round(total_kb, 1),
        'cleanup_total_mb': round(total_kb / 1024, 2),
    })


@csrf_exempt
@require_http_methods(['POST'])
def api_cleanup_files(request):
    """
    刪除指定的重複/舊格式檔案。
    Body: {"paths": ["pipeline/bilibili_uma_raw.csv", ...]}
    僅允許刪除 _stale_file_specs() 白名單內的路徑（安全防護）。
    """
    import json as _json
    from pathlib import Path
    from django.conf import settings as dj_settings

    try:
        body = _json.loads(request.body)
        requested = body.get('paths', [])
    except Exception:
        return JsonResponse({'error': '無效 JSON'}, status=400)

    allowed = {rel for rel, _, _ in _stale_file_specs()}
    base = Path(dj_settings.BASE_DIR).resolve()

    deleted, skipped, errors = [], [], []
    freed_kb = 0.0

    for rel in requested:
        if rel not in allowed:
            skipped.append({'path': rel, 'reason': '不在可清理白名單內'})
            continue
        path = (base / rel).resolve()
        # 二次防護：確認解析後路徑仍在專案目錄內
        if not str(path).startswith(str(base)):
            skipped.append({'path': rel, 'reason': '路徑越界，已拒絕'})
            continue
        if not path.exists():
            skipped.append({'path': rel, 'reason': '檔案不存在'})
            continue
        try:
            freed_kb += round(path.stat().st_size / 1024, 1)
            path.unlink()
            deleted.append(rel)
        except Exception as e:
            errors.append({'path': rel, 'error': str(e)})

    return JsonResponse({
        'ok': True,
        'deleted': deleted,
        'skipped': skipped,
        'errors': errors,
        'freed_kb': round(freed_kb, 1),
        'freed_mb': round(freed_kb / 1024, 2),
    })


@csrf_exempt
@require_http_methods(['POST'])
def api_clear_db(request):
    """
    清空資料庫 NewsData（可選擇單一來源或全部）。
    Body: {"source": "udn"}  或  {"source": "all"}
    """
    import json as _json
    try:
        body = _json.loads(request.body)
        source = body.get('source', 'all')
    except Exception:
        return JsonResponse({'error': '無效 JSON'}, status=400)

    try:
        from app_user_keyword_db.models import NewsData
        qs = NewsData.objects.all()
        if source and source != 'all':
            if source not in SOURCE_META:
                return JsonResponse({'error': f'未知來源：{source}'}, status=400)
            qs = qs.filter(source=source)
        count = qs.count()
        deleted, _ = qs.delete()
        return JsonResponse({'ok': True, 'source': source,
                             'matched': count, 'deleted': deleted})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


DISCORD_TASK_META = {
    'crawl': {'label': '爬取頻道訊息', 'estimated_seconds': 360},
    'classify': {'label': '分類待分類訊息', 'estimated_seconds': 240},
    'convert': {'label': '轉換至 NewsData', 'estimated_seconds': 180},
    'news': {'label': '手動推播 AI 新聞', 'estimated_seconds': 300},
}


def _discord_read_json(request) -> dict:
    try:
        return json.loads(request.body or '{}')
    except Exception:
        return {}


def _discord_task_to_dict(run) -> dict:
    return {
        'id': run.id,
        'task_type': run.task_type,
        'task_label': dict(run.TASK_CHOICES).get(run.task_type, run.task_type),
        'status': run.status,
        'progress_pct': run.progress_pct,
        'estimated_seconds': run.estimated_seconds,
        'started_at': run.started_at.strftime('%Y-%m-%d %H:%M:%S') if run.started_at else None,
        'ended_at': run.ended_at.strftime('%Y-%m-%d %H:%M:%S') if run.ended_at else None,
        'triggered_by': run.triggered_by,
        'summary': run.summary,
        'error_message': run.error_message,
        'result': run.result_json or {},
        'updated_at': run.updated_at.strftime('%Y-%m-%d %H:%M:%S') if run.updated_at else None,
    }


def _append_task_log(run, text: str):
    merged = run.log_text or ''
    if merged:
        merged += '\n'
    merged += str(text).rstrip('\r\n')
    if len(merged) > 50000:
        merged = merged[-50000:]
    run.log_text = merged
    run.save(update_fields=['log_text', 'updated_at'])


def _update_task(run, *, status=None, progress_pct=None, summary=None, error_message=None, result_json=None, ended=False):
    from django.utils import timezone as dj_timezone
    fields = ['updated_at']
    if status is not None:
        run.status = status
        fields.append('status')
    if progress_pct is not None:
        run.progress_pct = max(0, min(100, int(progress_pct)))
        fields.append('progress_pct')
    if summary is not None:
        run.summary = summary
        fields.append('summary')
    if error_message is not None:
        run.error_message = error_message
        fields.append('error_message')
    if result_json is not None:
        run.result_json = result_json
        fields.append('result_json')
    if ended:
        run.ended_at = dj_timezone.now()
        fields.append('ended_at')
    run.save(update_fields=fields)


_EPHEMERAL_CONNECT_TIMEOUT = 45   # 臨時 Bot 連線超時秒數（Bot 未啟動時的 fallback 用）


def _run_discord_ephemeral_bot(job_name: str, task_run, worker_coroutine_fn):
    """
    Fallback：持久 Bot 未啟動時，建立一條臨時 Bot 連線來執行任務。
    正常情況下，crawl/news 任務由持久 Bot 的 task_poller 接管，不會走到這裡。
    """
    import asyncio
    import discord

    token = os.getenv('DISCORD_BOT_TOKEN', '').strip()
    if not token or token == '你的Bot Token':
        raise RuntimeError('DISCORD_BOT_TOKEN 未設定，無法執行需要 Discord 連線的任務')

    run_id = getattr(task_run, 'id', None)

    async def _main():
        intents = discord.Intents.default()
        intents.guilds = True
        intents.message_content = True
        result_box = {'value': None, 'error': None}

        class _TempBot(discord.Client):
            async def on_ready(self):
                from app_discord_bot.crawler import CrawlCancelledError
                if _CANCEL_FLAGS.get(run_id):
                    result_box['error'] = CrawlCancelledError('連線後立即取消')
                    await self.close()
                    return
                _append_task_log(task_run, f'[{job_name}] Bot 已連線，伺服器數: {len(self.guilds)}')
                try:
                    result_box['value'] = await worker_coroutine_fn(self)
                except Exception as exc:
                    result_box['error'] = exc
                finally:
                    await self.close()

        bot = _TempBot(intents=intents)

        async def _watch_cancel():
            """背景監看取消旗標，連線中也能透過 bot.close() 中斷"""
            from app_discord_bot.crawler import CrawlCancelledError
            try:
                while True:
                    await asyncio.sleep(0.4)
                    if not _CANCEL_FLAGS.get(run_id):
                        continue
                    if result_box['error'] is None:
                        result_box['error'] = CrawlCancelledError('使用者取消')
                    try:
                        if not bot.is_closed():
                            await bot.close()
                    except Exception:
                        pass
                    return
            except asyncio.CancelledError:
                pass

        watcher = asyncio.create_task(_watch_cancel())
        try:
            # 加入連線超時保護：若 Gateway 在 N 秒內未觸發 on_ready 則中止
            await asyncio.wait_for(bot.start(token), timeout=_EPHEMERAL_CONNECT_TIMEOUT)
        except asyncio.TimeoutError:
            result_box['error'] = TimeoutError(
                f'Discord Gateway 連線超時（{_EPHEMERAL_CONNECT_TIMEOUT} 秒）'
                '，請確認 Bot Token 是否正確、網路是否正常，或稍後重試。'
            )
            try:
                if not bot.is_closed():
                    await bot.close()
            except Exception:
                pass
        finally:
            watcher.cancel()
            try:
                await watcher
            except asyncio.CancelledError:
                pass

        if result_box['error'] is not None:
            raise result_box['error']
        return result_box['value']

    # Windows 的 ProactorEventLoop 在非主執行緒中有執行緒親和性限制，
    # 會導致 discord.py 的 WebSocket 連線永久卡住（on_ready 不觸發）。
    # 改用 SelectorEventLoop 可在任意執行緒正常運作。
    try:
        if os.name == 'nt':
            import asyncio
            loop = asyncio.SelectorEventLoop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(_main())
            finally:
                loop.close()
        else:
            return asyncio.run(_main())
    finally:
        pass


# 取消旗標與 worker 執行緒追蹤
_CANCEL_FLAGS: dict[int, bool] = {}
_ACTIVE_WORKERS: dict[int, threading.Thread] = {}
# news 任務啟動前寫入：
# {'mode': 'weekly'|'article'|'articles', 'article_id': int?, 'article_ids': list[int]?, 'guild_ids': list?}
_PENDING_NEWS_OPTS: dict[int, dict] = {}


def _task_cancel_requested(run_id: int) -> bool:
    if _CANCEL_FLAGS.get(run_id):
        return True
    # 同時查 DB，確保即使記憶體旗標已清除也能偵測取消
    try:
        from app_discord_bot.models import DiscordTaskRun
        return bool(DiscordTaskRun.objects.filter(pk=run_id, cancel_requested=True).exists())
    except Exception:
        return False


def _finalize_cancelled(run, summary: str = '已被使用者取消') -> None:
    """將任務標記為 cancelled 並清除旗標"""
    _CANCEL_FLAGS.pop(run.id, None)
    _update_task(
        run, status='cancelled', progress_pct=run.progress_pct,
        summary=summary, ended=True,
    )
    _append_task_log(run, f'⛔ {summary}')


def _run_discord_task_worker(run_id: int):
    from django.utils import timezone as dj_timezone
    from app_discord_bot.models import DiscordTaskRun, DiscordMessage

    run = DiscordTaskRun.objects.get(id=run_id)
    run.started_at = dj_timezone.now()
    run.status = 'running'
    run.progress_pct = 5
    run.summary = '任務啟動中'
    run.save(update_fields=['started_at', 'status', 'progress_pct', 'summary', 'updated_at'])

    try:
        _append_task_log(run, f'▶ 任務開始：{run.task_type}')

        if _task_cancel_requested(run.id):
            _finalize_cancelled(run, '任務在啟動前已被取消')
            return

        if run.task_type == 'classify':
            from app_discord_bot.classifier import run_classifier
            before = DiscordMessage.objects.filter(is_umamusume=None).count()
            _append_task_log(run, f'待分類訊息數：{before}')
            _update_task(run, progress_pct=20, summary='執行分類中')
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
                classify_result = run_classifier(
                    cancel_check=lambda: _task_cancel_requested(run.id)
                )
            logs = buffer.getvalue().strip()
            if logs:
                _append_task_log(run, logs)
            if classify_result == 'cancelled' or _task_cancel_requested(run.id):
                _finalize_cancelled(run, '分類任務已取消')
                return
            after = DiscordMessage.objects.filter(is_umamusume=None).count()
            classified = max(0, before - after)
            result = {'before_unclassified': before, 'after_unclassified': after, 'classified_count': classified}
            if classify_result == 'limit_reached':
                _update_task(
                    run, status='success', progress_pct=100,
                    summary=f'分類完成（已達 Layer 2 批次上限），本次處理 {classified} 筆，剩餘 {after} 筆待下次繼續',
                    result_json=result, ended=True
                )
                _append_task_log(run, f'⚠️ 本次分類 {classified} 筆，剩餘 {after} 筆未分類，請再次觸發以繼續')
            else:
                _update_task(
                    run, status='success', progress_pct=100, summary=f'分類完成，共處理 {classified} 筆',
                    result_json=result, ended=True
                )
                _append_task_log(run, f'✅ 分類完成：{classified} 筆')
            return

        if run.task_type == 'convert':
            from app_discord_bot.converter import convert_discord_to_newsdata
            if _task_cancel_requested(run.id):
                _finalize_cancelled(run, '轉換任務在啟動前已被取消')
                return
            _update_task(run, progress_pct=30, summary='轉換中')
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
                created = int(convert_discord_to_newsdata() or 0)
            if _task_cancel_requested(run.id):
                _finalize_cancelled(run, '轉換任務已取消')
                return
            logs = buffer.getvalue().strip()
            if logs:
                _append_task_log(run, logs)
            result = {'created_newsdata': created}
            _update_task(
                run, status='success', progress_pct=100, summary=f'轉換完成，新增 {created} 筆',
                result_json=result, ended=True
            )
            _append_task_log(run, f'✅ 轉換完成：新增 {created} 筆')
            return

        if run.task_type == 'crawl':
            from app_discord_bot.crawler import crawl_all_channels, CrawlCancelledError
            from asgiref.sync import sync_to_async

            if _task_cancel_requested(run.id):
                _finalize_cancelled(run, '爬取任務在連線前已被取消')
                return

            _update_task(run, progress_pct=10, summary='建立 Discord 連線中…')
            _append_task_log(run, '⏳ 正在連線至 Discord Gateway…')

            _alog    = sync_to_async(_append_task_log)
            _aupdate = sync_to_async(_update_task)

            async def _log_fn(msg: str):
                await _alog(run, msg)

            async def _progress_fn(pct: int, summary: str):
                await _aupdate(run, progress_pct=pct, summary=summary)

            async def _cancel_fn() -> bool:
                return _task_cancel_requested(run.id)

            async def _crawl(bot):
                guild_total = len(bot.guilds)
                await _alog(run, f'✓ 已連線至 Discord Gateway  ·  Bot 帳號：{bot.user}  ·  加入 {guild_total} 個伺服器')
                await _aupdate(run, progress_pct=15, summary=f'已連線，準備爬取 {guild_total} 個伺服器')
                return await crawl_all_channels(
                    bot, log_fn=_log_fn, progress_fn=_progress_fn, cancel_fn=_cancel_fn
                )

            try:
                created = _run_discord_ephemeral_bot('crawl', run, _crawl)
                if _task_cancel_requested(run.id):
                    _finalize_cancelled(run)
                    return
                result = {'new_messages': int(created or 0)}
                _update_task(
                    run, status='success', progress_pct=100,
                    summary=f'爬取完成，共新增 {created} 筆訊息',
                    result_json=result, ended=True,
                )
                _append_task_log(run, f'✅ 全部完成，共新增 {created} 筆訊息')
            except CrawlCancelledError:
                _finalize_cancelled(run)
            finally:
                _CANCEL_FLAGS.pop(run.id, None)
            return

        if run.task_type == 'news':
            from app_discord_bot.crawler import CrawlCancelledError
            from datetime import datetime as _dt
            import pytz

            opts = _PENDING_NEWS_OPTS.pop(run.id, None) or {}
            push_mode = opts.get('mode', 'weekly')

            if _task_cancel_requested(run.id):
                _finalize_cancelled(run, '推播任務在連線前已被取消')
                return

            if push_mode == 'article':
                mode_label = f'文章 #{opts["article_id"]}'
            elif push_mode == 'articles':
                mode_label = f'批次文章（{len(opts.get("article_ids") or [])} 篇）'
            else:
                mode_label = '週報摘要'
            _update_task(run, progress_pct=15, summary=f'建立 Discord 連線（{mode_label}）')

            if push_mode == 'article':
                article_id = int(opts['article_id'])
                guild_ids = opts.get('guild_ids')

                async def _news(bot):
                    from app_crawler_admin.discord_push import push_article
                    return await push_article(bot, article_id, guild_ids=guild_ids)
            else:
                if push_mode == 'articles':
                    from app_crawler_admin.discord_push import push_article
                    article_ids = [int(v) for v in (opts.get('article_ids') or [])]
                    guild_ids = opts.get('guild_ids')

                    async def _news(bot):
                        summary = {
                            'sent': 0,
                            'failed': 0,
                            'article_results': [],
                        }
                        for article_id in article_ids:
                            if _task_cancel_requested(run.id):
                                raise CrawlCancelledError('批次推播已取消')
                            one = await push_article(bot, article_id, guild_ids=guild_ids)
                            summary['article_results'].append({'article_id': article_id, **one})
                            summary['sent'] += int(one.get('sent', 0))
                            summary['failed'] += int(one.get('failed', 0))
                        return summary
                else:
                    from app_discord_bot.scheduler import _run_per_guild_news

                    async def _news(bot):
                        now_hour = _dt.now(pytz.timezone('Asia/Taipei')).hour
                        return await _run_per_guild_news(bot, current_hour=now_hour, force_send=True)

            try:
                result = _run_discord_ephemeral_bot('news', run, _news) or {}
                if _task_cancel_requested(run.id):
                    _finalize_cancelled(run, '推播任務已取消')
                    return
                if result.get('error') and not int(result.get('sent', 0)):
                    raise RuntimeError(result['error'])
                sent = int(result.get('sent', 0))
                failed = int(result.get('failed', 0))
                _update_task(
                    run, status='success', progress_pct=100,
                    summary=f'推播完成（成功 {sent}、失敗 {failed}）',
                    result_json=result, ended=True
                )
                _append_task_log(run, f'✅ 推播完成：成功 {sent}、失敗 {failed}')
            except CrawlCancelledError:
                _finalize_cancelled(run, '推播任務已取消')
            finally:
                _CANCEL_FLAGS.pop(run.id, None)
                _PENDING_NEWS_OPTS.pop(run.id, None)
            return

        raise RuntimeError(f'不支援的任務類型：{run.task_type}')

    except Exception as exc:
        from app_discord_bot.crawler import CrawlCancelledError
        if isinstance(exc, CrawlCancelledError):
            _finalize_cancelled(run)
            return
        err = f'{exc}\n{traceback.format_exc()}'
        _append_task_log(run, f'❌ 任務失敗：{exc}')
        _update_task(
            run, status='failed', progress_pct=100, summary='任務失敗',
            error_message=str(exc), result_json={'error': str(exc)}, ended=True
        )
        _append_task_log(run, err)
    finally:
        _ACTIVE_WORKERS.pop(run_id, None)
        _CANCEL_FLAGS.pop(run_id, None)


def _launch_discord_task(
    task_type: str,
    triggered_by: str = 'admin-ui',
    *,
    news_opts: dict | None = None,
):
    from app_discord_bot.models import DiscordTaskRun
    from django.utils import timezone as dj_timezone

    meta = DISCORD_TASK_META.get(task_type)
    if not meta:
        raise ValueError('未知任務類型')

    # 同一種類任務避免重複觸發：
    # 若找到 running/pending 任務，先確認其 runner 與存活狀態；
    # 若 worker 已死（Django 重啟後殘留），自動標記為 failed 再建新任務。
    active = DiscordTaskRun.objects.filter(task_type=task_type, status__in=['pending', 'running']).first()
    if active:
        if active.runner == 'bot':
            # 由持久 Bot 負責執行，確認 Bot 是否仍在線
            try:
                from app_discord_bot.bot_manager import get_bot_status
                bot_alive = get_bot_status().get('running', False)
            except Exception:
                bot_alive = False
            if bot_alive:
                return active, False
            # Bot 已停止，殘留任務 → 標記 failed，讓流程重建
            from django.utils import timezone as _tz
            active.status = 'failed'
            active.summary = 'Bot 行程已停止，任務中止（已自動清除）'
            active.ended_at = _tz.now()
            active.save(update_fields=['status', 'summary', 'ended_at', 'updated_at'])
        worker = _ACTIVE_WORKERS.get(active.id)
        worker_alive = worker is not None and worker.is_alive()
        if worker_alive:
            return active, False
        # Worker 不存在（重啟後殘留）→ 強制標記 failed
        from django.utils import timezone as _tz
        active.status = 'failed'
        active.summary = '任務因伺服器重啟而中止（已自動清除）'
        active.ended_at = _tz.now()
        active.save(update_fields=['status', 'summary', 'ended_at', 'updated_at'])
        _CANCEL_FLAGS.pop(active.id, None)

    # 判斷是否應由持久 Bot 執行（crawl / news 需要 Discord 連線）
    use_bot_runner = False
    if task_type in ('crawl', 'news'):
        try:
            from app_discord_bot.bot_manager import get_bot_status
            use_bot_runner = get_bot_status().get('running', False)
        except Exception:
            pass

    # result_json 用於傳遞 news_opts 給 Bot 執行器
    init_result_json: dict = {}
    if news_opts and task_type == 'news':
        init_result_json = {
            'news_mode': news_opts.get('mode', 'weekly'),
            'article_id': news_opts.get('article_id'),
            'guild_ids': news_opts.get('guild_ids'),
        }

    run = DiscordTaskRun.objects.create(
        task_type=task_type,
        status='pending',
        runner='bot' if use_bot_runner else 'thread',
        progress_pct=0,
        estimated_seconds=meta['estimated_seconds'],
        triggered_by=triggered_by,
        summary='等待持久 Bot 接手' if use_bot_runner else '等待背景執行',
        started_at=dj_timezone.now(),
        result_json=init_result_json,
    )

    if use_bot_runner:
        # 持久 Bot 的 task_poller 每 2 秒會自動接手，無需另開執行緒
        return run, True

    # ── Django 執行緒 fallback（Bot 未啟動時，或 classify/convert）──
    if news_opts and task_type == 'news':
        _PENDING_NEWS_OPTS[run.id] = news_opts

    th = threading.Thread(target=_run_discord_task_worker, args=(run.id,), daemon=True)
    _ACTIVE_WORKERS[run.id] = th
    th.start()
    return run, True


# ═══════════════════════════════════════════════════════════
# Discord Bot 管理 API（整合至控制台）
# ═══════════════════════════════════════════════════════════

@csrf_exempt
@require_http_methods(['POST'])
def api_discord_channel_add(request):
    """新增或更新頻道設定（update_or_create by channel_id）"""
    data = _discord_read_json(request)

    channel_id = (data.get('channel_id') or '').strip()
    name = (data.get('name') or '').strip()
    ch_type = (data.get('channel_type') or '').strip()
    is_active = data.get('is_active', True)
    note = (data.get('note') or '').strip()

    if not channel_id or not channel_id.isdigit():
        return JsonResponse({'error': '頻道 ID 必須為純數字'}, status=400)
    if ch_type not in ('crawl', 'news'):
        return JsonResponse({'error': '頻道類型必須為 crawl 或 news'}, status=400)
    if not name:
        return JsonResponse({'error': '名稱不可為空'}, status=400)

    try:
        from app_discord_bot.models import DiscordBotConfig
        obj, created = DiscordBotConfig.objects.update_or_create(
            channel_id=channel_id,
            defaults={'name': name, 'channel_type': ch_type, 'is_active': bool(is_active), 'note': note}
        )
        return JsonResponse({
            'status': 'created' if created else 'updated',
            'id': obj.pk, 'channel_id': obj.channel_id,
            'name': obj.name, 'channel_type': obj.channel_type,
            'is_active': obj.is_active,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def api_discord_channel_delete(request, pk):
    """刪除指定頻道設定"""
    try:
        from app_discord_bot.models import DiscordBotConfig
        deleted, _ = DiscordBotConfig.objects.filter(pk=pk).delete()
        if not deleted:
            return JsonResponse({'error': '找不到此設定'}, status=404)
        return JsonResponse({'status': 'deleted', 'id': pk})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def api_discord_channel_toggle(request, pk):
    """切換頻道啟用狀態"""
    from app_discord_bot.models import DiscordBotConfig
    try:
        cfg = DiscordBotConfig.objects.get(pk=pk)
        cfg.is_active = not cfg.is_active
        cfg.save(update_fields=['is_active'])
        return JsonResponse({'status': 'ok', 'is_active': cfg.is_active})
    except DiscordBotConfig.DoesNotExist:
        return JsonResponse({'error': '找不到此設定'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def api_discord_task_start(request):
    """啟動 Discord 手動任務（crawl/classify/convert/news）"""
    data = _discord_read_json(request)
    task_type = str(data.get('task') or '').strip().lower()
    if task_type not in DISCORD_TASK_META:
        return JsonResponse({'error': '未知任務，僅支援 crawl/classify/convert/news'}, status=400)
    try:
        run, created = _launch_discord_task(task_type, triggered_by='crawler-admin')
        return JsonResponse({
            'status': 'started' if created else 'already_running',
            'task': task_type,
            'run': _discord_task_to_dict(run),
        })
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=500)


def api_discord_task_status(request):
    """取得 Discord 任務狀態（可帶 run_id，否則回最近 20 筆）"""
    from app_discord_bot.models import DiscordTaskRun
    run_id = _parse_int(request.GET.get('run_id'), default=0, min_value=0)
    if run_id:
        run = DiscordTaskRun.objects.filter(id=run_id).first()
        if not run:
            return JsonResponse({'error': '找不到任務'}, status=404)
        return JsonResponse({'run': _discord_task_to_dict(run)})
    runs = [ _discord_task_to_dict(r) for r in DiscordTaskRun.objects.all()[:20] ]
    return JsonResponse({'runs': runs})


def api_discord_task_log(request, run_id):
    """取得任務日誌（offset 增量）"""
    from app_discord_bot.models import DiscordTaskRun
    run = DiscordTaskRun.objects.filter(id=run_id).first()
    if not run:
        return JsonResponse({'error': '找不到任務'}, status=404)
    offset = _parse_int(request.GET.get('offset', 0), default=0, min_value=0)
    lines = (run.log_text or '').splitlines()
    return JsonResponse({'lines': lines[offset:], 'total': len(lines), 'run': _discord_task_to_dict(run)})


@csrf_exempt
@require_http_methods(['POST'])
def api_discord_task_cancel(request, run_id):
    """請求取消執行中的 Discord 任務（crawl / classify / convert / news）"""
    from app_discord_bot.models import DiscordTaskRun
    run = DiscordTaskRun.objects.filter(id=run_id).first()
    if not run:
        return JsonResponse({'error': '找不到任務'}, status=404)
    if run.status not in ('pending', 'running'):
        return JsonResponse({'error': f'任務狀態為 {run.status}，無法取消', 'status': run.status}, status=400)

    _CANCEL_FLAGS[run_id] = True
    # 同時寫 DB 欄位，讓持久 Bot 行程的 cancel_fn 也能偵測到
    run.cancel_requested = True
    run.save(update_fields=['cancel_requested', 'updated_at'])

    # Bot runner：不需要 worker 存活確認，交給 Bot 自行偵測取消
    if run.runner == 'bot':
        _update_task(run, summary='正在取消…')
        return JsonResponse({'status': 'cancel_requested', 'run_id': run_id, 'run': _discord_task_to_dict(run)})

    # Worker 已不存在（例如伺服器重啟後殘留的 running 紀錄）→ 直接標記取消
    worker = _ACTIVE_WORKERS.get(run_id)
    if worker is None or not worker.is_alive():
        _finalize_cancelled(run, '任務已強制標記為取消（worker 不存在）')
        run.refresh_from_db()
        return JsonResponse({
            'status': 'cancelled',
            'run_id': run_id,
            'run': _discord_task_to_dict(run),
        })

    _update_task(run, summary='正在取消…')
    _append_task_log(run, '⚠ 已收到取消請求，正在停止任務…')
    run.refresh_from_db()
    return JsonResponse({
        'status': 'cancel_requested',
        'run_id': run_id,
        'run': _discord_task_to_dict(run),
    })


@csrf_exempt
@require_http_methods(['POST'])
def api_discord_run_classify(request):
    """相容舊端點：手動分類"""
    try:
        run, created = _launch_discord_task('classify', triggered_by='crawler-admin-legacy')
        return JsonResponse({'status': 'started' if created else 'already_running', 'task': 'classify', 'run': _discord_task_to_dict(run)})
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def api_discord_run_convert(request):
    """相容舊端點：手動轉換"""
    try:
        run, created = _launch_discord_task('convert', triggered_by='crawler-admin-legacy')
        return JsonResponse({'status': 'started' if created else 'already_running', 'task': 'convert', 'run': _discord_task_to_dict(run)})
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def api_discord_run_crawl(request):
    """手動執行 Discord 爬取"""
    try:
        run, created = _launch_discord_task('crawl', triggered_by='crawler-admin-legacy')
        return JsonResponse({'status': 'started' if created else 'already_running', 'task': 'crawl', 'run': _discord_task_to_dict(run)})
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def api_discord_trigger_news(request):
    """相容舊端點：手動推播"""
    try:
        run, created = _launch_discord_task('news', triggered_by='crawler-admin-legacy')
        return JsonResponse({'status': 'started' if created else 'already_running', 'task': 'news', 'run': _discord_task_to_dict(run)})
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=500)


# ═══════════════════════════════════════════════════════════
# AI 新聞頁 — Discord 推播整合
# ═══════════════════════════════════════════════════════════

@require_http_methods(['GET'])
def api_ai_news_discord_status(request):
    """AI 新聞頁：Bot 狀態、推播目標、近期紀錄、進行中任務"""
    try:
        from app_crawler_admin.discord_push import get_discord_push_status
        return JsonResponse({'ok': True, **get_discord_push_status()})
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def api_ai_news_discord_push_weekly(request):
    """AI 新聞頁：觸發週報摘要推播（與 Discord 控制台 news 任務相同）"""
    try:
        run, created = _launch_discord_task('news', triggered_by='ai-news-weekly')
        return JsonResponse({
            'ok': True,
            'status': 'started' if created else 'already_running',
            'run': _discord_task_to_dict(run),
        })
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def api_ai_news_discord_push_article(request):
    """AI 新聞頁：將指定 GeneratedNewsArticle 推播至 Discord"""
    data = _discord_read_json(request)
    article_id = data.get('article_id')
    if article_id is None:
        return JsonResponse({'error': '缺少 article_id'}, status=400)
    try:
        article_id = int(article_id)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'article_id 無效'}, status=400)

    guild_ids = data.get('guild_ids')
    if guild_ids is not None and not isinstance(guild_ids, list):
        return JsonResponse({'error': 'guild_ids 須為陣列'}, status=400)

    from app_user_keyword_llm_report.models import GeneratedNewsArticle
    if not GeneratedNewsArticle.objects.filter(pk=article_id).exists():
        return JsonResponse({'error': f'找不到新聞 #{article_id}'}, status=404)

    try:
        run, created = _launch_discord_task(
            'news',
            triggered_by='ai-news-article',
            news_opts={
                'mode': 'article',
                'article_id': article_id,
                'guild_ids': guild_ids,
            },
        )
        return JsonResponse({
            'ok': True,
            'status': 'started' if created else 'already_running',
            'article_id': article_id,
            'run': _discord_task_to_dict(run),
        })
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def api_ai_news_discord_push_articles(request):
    """AI 新聞頁：將多篇指定 GeneratedNewsArticle 批次推播至 Discord（預設全伺服器）"""
    data = _discord_read_json(request)
    article_ids = data.get('article_ids')
    if not isinstance(article_ids, list) or not article_ids:
        return JsonResponse({'error': 'article_ids 需為非空陣列'}, status=400)

    normalized_ids = []
    for value in article_ids:
        try:
            normalized_ids.append(int(value))
        except (TypeError, ValueError):
            return JsonResponse({'error': f'article_id 無效：{value}'}, status=400)
    normalized_ids = list(dict.fromkeys(normalized_ids))

    guild_ids = data.get('guild_ids')
    if guild_ids is not None and not isinstance(guild_ids, list):
        return JsonResponse({'error': 'guild_ids 須為陣列'}, status=400)

    from app_user_keyword_llm_report.models import GeneratedNewsArticle
    existing_ids = set(
        GeneratedNewsArticle.objects.filter(pk__in=normalized_ids).values_list('pk', flat=True)
    )
    missing = [nid for nid in normalized_ids if nid not in existing_ids]
    if missing:
        return JsonResponse({'error': f'找不到新聞 ID：{missing}'}, status=404)

    try:
        run, created = _launch_discord_task(
            'news',
            triggered_by='ai-news-articles',
            news_opts={
                'mode': 'articles',
                'article_ids': normalized_ids,
                'guild_ids': guild_ids,
            },
        )
        return JsonResponse(
            {
                'ok': True,
                'status': 'started' if created else 'already_running',
                'article_ids': normalized_ids,
                'run': _discord_task_to_dict(run),
            }
        )
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=500)


# ═══════════════════════════════════════════════════════════
# 爬取全域設定 API（crawl_limit / concurrency）
# ═══════════════════════════════════════════════════════════

@require_http_methods(['GET'])
def api_discord_crawl_settings_get(request):
    """GET：回傳目前爬取全域設定"""
    try:
        from app_discord_bot.models import DiscordCrawlSettings
        s = DiscordCrawlSettings.get()
        return JsonResponse({
            'ok': True,
            'crawl_limit': s.crawl_limit,
            'concurrency': s.concurrency,
            'updated_at': s.updated_at.strftime('%Y-%m-%d %H:%M:%S') if s.updated_at else None,
        })
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def api_discord_crawl_settings_save(request):
    """POST：儲存爬取全域設定"""
    data = _discord_read_json(request)
    try:
        crawl_limit = int(data.get('crawl_limit', 1000))
        concurrency = int(data.get('concurrency', 3))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'crawl_limit / concurrency 須為整數'}, status=400)

    if crawl_limit < 0:
        return JsonResponse({'error': 'crawl_limit 不得為負數（0 = 不限）'}, status=400)
    if not (1 <= concurrency <= 10):
        return JsonResponse({'error': 'concurrency 須介於 1–10'}, status=400)

    try:
        from app_discord_bot.models import DiscordCrawlSettings
        s = DiscordCrawlSettings.get()
        s.crawl_limit = crawl_limit
        s.concurrency = concurrency
        s.save()
        return JsonResponse({
            'ok': True,
            'crawl_limit': s.crawl_limit,
            'concurrency': s.concurrency,
        })
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=500)


def api_discord_recent_messages(request):
    """Discord 訊息查詢（支援篩選/排序/分頁）"""
    try:
        from app_discord_bot.models import DiscordMessage
        from app_uma_info_portal.models import DiscordGuild

        limit = _parse_int(request.GET.get('limit', 20), default=20, min_value=5, max_value=200)
        page = _parse_int(request.GET.get('page', 1), default=1, min_value=1)
        keyword = (request.GET.get('keyword') or '').strip()
        guild_id = (request.GET.get('guild_id') or '').strip()
        channel_id = (request.GET.get('channel_id') or '').strip()
        msg_id = (request.GET.get('msg_id') or '').strip()
        classify = (request.GET.get('classify') or 'all').strip()
        date_from = (request.GET.get('date_from') or '').strip()
        date_to = (request.GET.get('date_to') or '').strip()
        sort_by = (request.GET.get('sort_by') or 'timestamp').strip()
        sort_dir = (request.GET.get('sort_dir') or 'desc').strip().lower()

        allowed_sort = {'timestamp', 'author', 'channel_name', 'created_at'}
        if sort_by not in allowed_sort:
            sort_by = 'timestamp'
        order_expr = f'-{sort_by}' if sort_dir != 'asc' else sort_by

        qs = DiscordMessage.objects.all()
        if keyword:
            qs = qs.filter(content__icontains=keyword)
        if guild_id:
            qs = qs.filter(guild_id=guild_id)
        if channel_id:
            qs = qs.filter(channel_id=channel_id)
        if msg_id:
            qs = qs.filter(msg_id=msg_id)
        if classify == 'uma':
            qs = qs.filter(is_umamusume=True)
        elif classify == 'nonuma':
            qs = qs.filter(is_umamusume=False)
        elif classify == 'pending':
            qs = qs.filter(is_umamusume=None)
        if date_from:
            qs = qs.filter(timestamp__date__gte=date_from)
        if date_to:
            qs = qs.filter(timestamp__date__lte=date_to)

        total = qs.count()
        offset = (page - 1) * limit
        rows = list(
            qs.order_by(order_expr)[offset: offset + limit].values(
                'msg_id', 'guild_id', 'channel_id', 'channel_name', 'author',
                'content', 'timestamp', 'is_umamusume', 'classified_by', 'news_data_id',
                'created_at',
            )
        )

        guild_map = dict(DiscordGuild.objects.values_list('guild_id', 'name'))
        for row in rows:
            if row['timestamp']:
                row['timestamp'] = row['timestamp'].strftime('%Y-%m-%d %H:%M')
            if row.get('created_at'):
                row['created_at'] = row['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            row['guild_name'] = guild_map.get(row['guild_id'], '')
            row['is_converted'] = bool(row['news_data_id'])

        guild_filters = list(
            DiscordMessage.objects.exclude(guild_id='').values('guild_id').distinct().order_by('guild_id')
        )
        for g in guild_filters:
            gid = g['guild_id']
            g['guild_name'] = guild_map.get(gid, gid)

        return JsonResponse({
            'messages': rows,
            'page': page,
            'limit': limit,
            'total': total,
            'total_pages': max(1, (total + limit - 1) // limit),
            'filters': {'guilds': guild_filters},
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def api_discord_delete_messages(request):
    """刪除 Discord 訊息（支援依 msg_id 清單或目前篩選條件刪除）"""
    from app_discord_bot.models import DiscordMessage
    data = _discord_read_json(request)

    msg_ids = data.get('msg_ids') or []
    delete_filtered = _parse_bool(data.get('delete_filtered'), default=False)
    if msg_ids:
        deleted, _ = DiscordMessage.objects.filter(msg_id__in=msg_ids).delete()
        return JsonResponse({'status': 'ok', 'deleted': deleted, 'mode': 'selected'})

    if not delete_filtered:
        return JsonResponse({'error': '請提供 msg_ids 或 delete_filtered=true'}, status=400)

    qs = DiscordMessage.objects.all()
    keyword = (data.get('keyword') or '').strip()
    guild_id = (data.get('guild_id') or '').strip()
    channel_id = (data.get('channel_id') or '').strip()
    classify = (data.get('classify') or 'all').strip()
    date_from = (data.get('date_from') or '').strip()
    date_to = (data.get('date_to') or '').strip()

    if keyword:
        qs = qs.filter(content__icontains=keyword)
    if guild_id:
        qs = qs.filter(guild_id=guild_id)
    if channel_id:
        qs = qs.filter(channel_id=channel_id)
    if classify == 'uma':
        qs = qs.filter(is_umamusume=True)
    elif classify == 'nonuma':
        qs = qs.filter(is_umamusume=False)
    elif classify == 'pending':
        qs = qs.filter(is_umamusume=None)
    if date_from:
        qs = qs.filter(timestamp__date__gte=date_from)
    if date_to:
        qs = qs.filter(timestamp__date__lte=date_to)

    matched = qs.count()
    deleted, _ = qs.delete()
    return JsonResponse({'status': 'ok', 'matched': matched, 'deleted': deleted, 'mode': 'filtered'})


def api_discord_stats(request):
    """Discord Bot 即時統計（供前端 polling）"""
    try:
        from app_discord_bot.models import DiscordMessage, DiscordBotConfig, DiscordNewsLog, DiscordTaskRun
        from django.utils import timezone as dj_timezone
        today = dj_timezone.now().date()
        latest_task = DiscordTaskRun.objects.first()
        return JsonResponse({
            'total_messages': DiscordMessage.objects.count(),
            'uma_messages': DiscordMessage.objects.filter(is_umamusume=True).count(),
            'unclassified': DiscordMessage.objects.filter(is_umamusume=None).count(),
            'active_channels': DiscordBotConfig.objects.filter(is_active=True).count(),
            'news_total': DiscordNewsLog.objects.count(),
            'news_today': DiscordNewsLog.objects.filter(created_at__date=today, status='sent').count(),
            'task_running': DiscordTaskRun.objects.filter(status__in=['pending', 'running']).exists(),
            'latest_task': _discord_task_to_dict(latest_task) if latest_task else None,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ══════════════════════════════════════════════════════════════
# Discord Bot 行程開關（啟動 / 停止 / 狀態查詢）
# ══════════════════════════════════════════════════════════════

@require_http_methods(['GET'])
def api_discord_bot_status(request):
    """GET：回傳 Bot 行程目前狀態"""
    try:
        from app_discord_bot.bot_manager import get_bot_status
        status = get_bot_status()
        return JsonResponse(status)
    except Exception as e:
        return JsonResponse({'running': False, 'pid': None, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def api_discord_bot_start(request):
    """POST：啟動 Discord Bot 子行程"""
    try:
        from app_discord_bot.bot_manager import start_bot
        success, message = start_bot()
        return JsonResponse({'success': success, 'message': message})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def api_discord_bot_stop(request):
    """POST：停止 Discord Bot 子行程"""
    try:
        from app_discord_bot.bot_manager import stop_bot
        success, message = stop_bot()
        return JsonResponse({'success': success, 'message': message})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


# ══════════════════════════════════════════════════════════════
# 資料管理 API（DB 化遷移計畫 Phase 1）
# ══════════════════════════════════════════════════════════════

_WEB_SOURCES = ['bilibili', 'bahamut', 'ettoday', 'gamme', 'udn']
_ALL_SOURCES  = _WEB_SOURCES + ['discord', 'youtube']


@require_http_methods(['GET'])
def api_data_manager_stats(request):
    """GET：取得 NewsData 各來源 / 各 status 統計"""
    try:
        from app_user_keyword_db.models import NewsData
        from django.db.models import Count

        source_counts = dict(
            NewsData.objects.values_list('source').annotate(c=Count('item_id'))
        )
        status_counts = dict(
            NewsData.objects.values_list('status').annotate(c=Count('item_id'))
        )
        total = NewsData.objects.count()
        return JsonResponse({
            'total': total,
            'by_source': source_counts,
            'by_status': status_counts,
            'web_sources': _WEB_SOURCES,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def api_data_manager_clear_source(request):
    """POST：清除指定來源的所有 NewsData
    Body JSON: {"source": "bilibili"}   或  {"source": "web"}（清全 5 網路來源）
    Discord/YouTube 需明確指定 source，不在 web 批次範圍。
    """
    try:
        data = json.loads(request.body)
        source = data.get('source', '').strip()
        if not source:
            return JsonResponse({'error': '必須指定 source'}, status=400)

        from app_user_keyword_db.models import NewsData
        if source == 'web':
            deleted, _ = NewsData.objects.filter(source__in=_WEB_SOURCES).delete()
            msg = f'已清除網路來源（{", ".join(_WEB_SOURCES)}）共 {deleted} 筆'
        elif source in _ALL_SOURCES:
            deleted, _ = NewsData.objects.filter(source=source).delete()
            msg = f'已清除 {source} 共 {deleted} 筆'
        else:
            return JsonResponse({'error': f'不支援的來源：{source}'}, status=400)

        return JsonResponse({'success': True, 'deleted': deleted, 'message': msg})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def api_data_manager_clear_date(request):
    """POST：清除指定日期之前的資料
    Body JSON: {"before_date": "2024-01-01", "source": "bilibili"}（source 可選）
    """
    try:
        data = json.loads(request.body)
        before_date = data.get('before_date', '').strip()
        source      = data.get('source', '').strip()
        if not before_date:
            return JsonResponse({'error': '必須指定 before_date（格式 YYYY-MM-DD）'}, status=400)

        from app_user_keyword_db.models import NewsData
        qs = NewsData.objects.filter(date__lt=before_date)
        if source:
            qs = qs.filter(source=source)
        deleted, _ = qs.delete()
        msg = f'已清除 {before_date} 之前{"（" + source + "）" if source else ""} 共 {deleted} 筆'
        return JsonResponse({'success': True, 'deleted': deleted, 'message': msg})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def api_data_manager_delete_item(request):
    """POST：依 item_id 刪除單筆
    Body JSON: {"item_id": "bilibili_特別週"}
    """
    try:
        data    = json.loads(request.body)
        item_id = data.get('item_id', '').strip()
        if not item_id:
            return JsonResponse({'error': '必須指定 item_id'}, status=400)

        from app_user_keyword_db.models import NewsData
        deleted, _ = NewsData.objects.filter(item_id=item_id).delete()
        if deleted:
            return JsonResponse({'success': True, 'message': f'已刪除 {item_id}'})
        return JsonResponse({'success': False, 'message': f'找不到 {item_id}'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def api_data_manager_reset_status(request):
    """POST：重設 status 為指定值（預設 raw），觸發重新處理
    Body JSON: {"source": "bilibili", "to_status": "raw"}（source 可選）
    """
    try:
        data      = json.loads(request.body)
        source    = data.get('source', '').strip()
        to_status = data.get('to_status', 'raw').strip()
        if to_status not in ('raw', 'tokenized', 'labeled'):
            return JsonResponse({'error': f'不支援的狀態：{to_status}'}, status=400)

        from app_user_keyword_db.models import NewsData
        qs = NewsData.objects.all()
        if source:
            qs = qs.filter(source=source)
        updated = qs.update(status=to_status)
        msg = f'已將{"（" + source + "）" if source else "全部"} {updated} 筆重設為 {to_status}'
        return JsonResponse({'success': True, 'updated': updated, 'message': msg})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(['GET'])
def api_data_manager_scan(request):
    """GET：掃描資料品質問題
    回傳：異常筆數（item_id 格式不符來源、date 為 null、content 空）
    """
    try:
        from app_user_keyword_db.models import NewsData
        from django.db.models import Q

        null_date   = NewsData.objects.filter(date__isnull=True).count()
        empty_title = NewsData.objects.filter(Q(title='') | Q(title__isnull=True)).count()
        empty_content = NewsData.objects.filter(Q(content='') | Q(content__isnull=True)).count()
        not_labeled = NewsData.objects.exclude(status='labeled').count()

        # 檢查 Bilibili item_id 是否含舊格式（bilibili_{category}_{idx}）
        # 舊格式特徵：item_id 不含中文或英文頁面名，而是 "bilibili_XXX_數字"
        import re
        bilibili_items = list(
            NewsData.objects.filter(source='bilibili').values_list('item_id', flat=True)
        )
        old_format_count = sum(
            1 for iid in bilibili_items
            if re.match(r'^bilibili_[^_]+_\d+$', iid)
        )

        return JsonResponse({
            'null_date':        null_date,
            'empty_title':      empty_title,
            'empty_content':    empty_content,
            'not_labeled':      not_labeled,
            'bilibili_old_id':  old_format_count,
            'bilibili_total':   len(bilibili_items),
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
