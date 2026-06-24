"""
runner.py — 爬蟲 subprocess 啟動、停止、log 捕捉（Phase B polling 版本）

registry 結構：
  { source: { 'process': Popen, 'run_id': str, 'log_lines': [str], 'done': bool } }
"""
import os
import sys
import threading
import signal
from datetime import datetime, timezone

from django.conf import settings

# ── 來源定義 ──────────────────────────────────────────────
SOURCE_META = {
    'bilibili': {'name': 'Bilibili BWIKI',   'script': 'pipeline/crawl_bilibili_uma.py', 'label': '官方來源'},
    'bahamut':  {'name': '巴哈姆特哈啦板',   'script': 'pipeline/crawl_bahamut_uma.py',  'label': '社群論壇'},
    'udn':      {'name': '聯合新聞網',        'script': 'pipeline/crawl_udn_uma.py',      'label': '媒體新聞'},
    'ettoday':  {'name': 'ETtoday 新聞雲',   'script': 'pipeline/crawl_ettoday_uma.py',  'label': '媒體新聞'},
    'gamme':    {'name': '宅宅新聞',          'script': 'pipeline/crawl_gamme_uma.py',    'label': 'ACG 媒體'},
}

_registry: dict = {}   # 全域行程登錄表
_lock = threading.Lock()


def _script_path(source: str) -> str:
    return os.path.join(settings.BASE_DIR, SOURCE_META[source]['script'])


def is_ready(source: str) -> bool:
    """腳本檔案存在即視為已就緒"""
    return os.path.isfile(_script_path(source))


def get_registry_entry(source: str) -> dict | None:
    with _lock:
        return _registry.get(source)


def _log_reader(source: str, process):
    """背景執行緒：讀取 subprocess stdout/stderr 並存入 registry"""
    import re
    new_re   = re.compile(r'新增|已儲存|saved|article', re.IGNORECASE)
    skip_re  = re.compile(r'略過|跳過|skip|duplicate', re.IGNORECASE)
    err_re   = re.compile(r'錯誤|error|exception|failed', re.IGNORECASE)

    # 以 try/finally 包覆，確保即使讀取過程拋出例外（例如編碼問題），
    # 仍一定會收尾並更新 DB 狀態，避免 CrawlerRun 永遠停在 'running'。
    try:
        while True:
            try:
                line = process.stdout.readline()
            except (UnicodeDecodeError, ValueError) as exc:
                # 單行解碼失敗不應中斷整個讀取迴圈
                line = f'[log 讀取警告] {exc}\n'
            if not line:
                break
            text = line.rstrip('\n')
            with _lock:
                entry = _registry.get(source)
                if entry is None:
                    break
                entry['log_lines'].append(text)
                # 解析計數器（模糊匹配）
                if new_re.search(text):
                    entry['articles_new'] += 1
                elif skip_re.search(text):
                    entry['articles_skip'] += 1
                elif err_re.search(text):
                    entry['articles_err'] += 1
                # 僅保留最近 1000 行，避免記憶體無限增長
                if len(entry['log_lines']) > 1000:
                    entry['log_lines'] = entry['log_lines'][-1000:]
    finally:
        # subprocess 結束（無論讀取迴圈是否正常退出都要 wait + 收尾）
        try:
            process.wait()
            returncode = process.returncode
        except Exception:
            returncode = 1
        _finish_run(source, returncode)


def _finish_run(source: str, returncode: int):
    from .models import CrawlerRun
    with _lock:
        entry = _registry.get(source)
        if entry is None:
            return
        entry['done'] = True
        status = 'success' if returncode == 0 else ('cancelled' if returncode < 0 else 'failed')
        run_id = entry['run_id']
        log_snapshot = '\n'.join(entry['log_lines'][-300:])
        articles_new  = entry.get('articles_new', 0)
        articles_skip = entry.get('articles_skip', 0)
        articles_err  = entry.get('articles_err', 0)

    try:
        run = CrawlerRun.objects.get(run_id=run_id)
        run.status       = status
        run.ended_at     = datetime.now(tz=timezone.utc)
        run.articles_new = articles_new
        run.articles_skip= articles_skip
        run.articles_err = articles_err
        run.log_text     = log_snapshot
        run.save()
    except Exception:
        pass


def trigger(source: str, triggered_by: str = 'manual') -> dict:
    """啟動指定來源爬蟲，回傳 {'ok': bool, 'run_id': str, 'error': str}"""
    import subprocess
    from .models import CrawlerRun, CrawlerConfig

    if source not in SOURCE_META:
        return {'ok': False, 'error': f'未知來源：{source}'}

    with _lock:
        entry = _registry.get(source)
        if entry and not entry.get('done', True):
            proc = entry.get('process')
            if proc and proc.poll() is None:
                return {'ok': False, 'error': f'{source} 爬蟲正在執行中，請先停止'}

    if not is_ready(source):
        return {'ok': False, 'error': f'{source} 腳本尚未就緒'}

    # 讀取設定
    config, _ = CrawlerConfig.objects.get_or_create(
        source=source,
        defaults={'max_pages': 50, 'delay_min': 0.8, 'delay_max': 1.5}
    )

    script = _script_path(source)
    cmd = [sys.executable, script,
           f'--max-pages={config.max_pages}']
    if config.use_playwright:
        cmd.append('--playwright')

    run = CrawlerRun.objects.create(
        source=source,
        status='running',
        triggered_by=triggered_by,
    )

    env = os.environ.copy()
    env['PYTHONUNBUFFERED'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'   # 防止 Windows CP950 環境下 print 中文時 UnicodeEncodeError
    env['CRAWLER_ADMIN_RUN_ID'] = run.run_id
    # 將後台設定注入爬蟲腳本（腳本可選擇讀取）
    env['CRAWLER_DELAY_MIN'] = str(config.delay_min)
    env['CRAWLER_DELAY_MAX'] = str(config.delay_max)
    env['CRAWLER_USER_AGENT'] = config.user_agent or ''

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',   # 子程序以 UTF-8 輸出，須明確指定避免 Windows cp950 解碼錯誤
            errors='replace',   # 萬一遇到無法解碼的位元組，以替代字元取代而非拋出例外
            bufsize=1,
            cwd=settings.BASE_DIR,
            env=env,
        )
    except Exception as exc:
        run.status = 'failed'
        run.log_text = str(exc)
        run.ended_at = datetime.now(tz=timezone.utc)
        run.save()
        return {'ok': False, 'error': str(exc)}

    with _lock:
        _registry[source] = {
            'process':      process,
            'run_id':       run.run_id,
            'log_lines':    [f'[啟動] {SOURCE_META[source]["name"]} 爬蟲  PID={process.pid}'],
            'done':         False,
            'articles_new':  0,
            'articles_skip': 0,
            'articles_err':  0,
        }

    t = threading.Thread(target=_log_reader, args=(source, process), daemon=True)
    t.start()

    return {'ok': True, 'run_id': run.run_id}


def stop(source: str) -> dict:
    """終止指定來源爬蟲"""
    with _lock:
        entry = _registry.get(source)
        if not entry:
            return {'ok': False, 'error': '該爬蟲未在執行中'}
        proc = entry.get('process')

    if proc is None or proc.poll() is not None:
        return {'ok': False, 'error': '該爬蟲已結束'}

    try:
        proc.terminate()
    except Exception as exc:
        return {'ok': False, 'error': str(exc)}
    return {'ok': True}


def get_status(source: str) -> dict:
    """
    回傳單一來源狀態 dict：
      status: 'running' | 'idle' | 'not_ready'
      run_id, log_tail (最後 50 行), articles_new/skip/err
    """
    from .models import CrawlerRun

    if not is_ready(source):
        return {'source': source, 'status': 'not_ready', 'log_tail': [], 'run_id': None,
                'articles_new': 0, 'articles_skip': 0, 'articles_err': 0}

    with _lock:
        entry = _registry.get(source)
        if entry:
            proc = entry.get('process')
            still_running = proc is not None and proc.poll() is None
            return {
                'source':       source,
                'status':       'running' if still_running else 'idle',
                'run_id':       entry['run_id'],
                'log_tail':     entry['log_lines'][-50:],
                'articles_new':  entry.get('articles_new', 0),
                'articles_skip': entry.get('articles_skip', 0),
                'articles_err':  entry.get('articles_err', 0),
            }

    # 不在 registry，查最近一筆 DB 記錄
    last = CrawlerRun.objects.filter(source=source).first()
    return {
        'source':       source,
        'status':       'idle',
        'run_id':       last.run_id if last else None,
        'log_tail':     [],
        'articles_new':  last.articles_new if last else 0,
        'articles_skip': last.articles_skip if last else 0,
        'articles_err':  last.articles_err if last else 0,
    }


def get_log(source: str) -> list[str]:
    with _lock:
        entry = _registry.get(source)
        if entry:
            return list(entry['log_lines'])
    return []


def _active_run_ids() -> set:
    """回傳目前確實有活躍 subprocess 的 run_id 集合。"""
    ids = set()
    with _lock:
        for entry in _registry.values():
            proc = entry.get('process')
            if proc is not None and proc.poll() is None:
                rid = entry.get('run_id')
                if rid:
                    ids.add(rid)
    return ids


def reconcile_stale_runs() -> int:
    """
    執行期自我修復：將 DB 中標記為 'running'、但沒有對應活躍 subprocess 的
    孤兒記錄收尾為 'failed'。

    這類孤兒記錄通常來自：開發伺服器 autoreload／重啟／崩潰，使得記憶體中的
    _registry 與收尾執行緒被清掉，導致 CrawlerRun 永遠停在 'running'。

    回傳被修復的筆數。供 api_status_all / api_history 等讀取端點呼叫，
    確保前台顯示永遠與真實狀態一致。
    """
    from .models import CrawlerRun

    active = _active_run_ids()
    try:
        stale_qs = CrawlerRun.objects.filter(status='running')
        if active:
            stale_qs = stale_qs.exclude(run_id__in=active)
        stale = list(stale_qs)
    except Exception:
        return 0

    updated = 0
    note = '[系統] 偵測到伺服器重啟/重載，此執行已中斷，狀態自動標記為失敗。'
    for run in stale:
        run.status = 'failed'
        run.ended_at = datetime.now(tz=timezone.utc)
        run.log_text = (run.log_text + '\n' + note) if run.log_text else note
        try:
            run.save(update_fields=['status', 'ended_at', 'log_text'])
            updated += 1
        except Exception:
            pass
    return updated
