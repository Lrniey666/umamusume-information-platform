import subprocess
import threading
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore

_scheduler = BackgroundScheduler(jobstores={'default': MemoryJobStore()})
_history = []
_lock = threading.Lock()


def _run_analyze_job():
    start = datetime.now()
    try:
        result = subprocess.run(
            ['python', 'manage.py', 'analyze_comments'],
            capture_output=True, text=True, timeout=300,
        )
        status = 'success' if result.returncode == 0 else 'error'
        output = (result.stdout or result.stderr or '')[:500]
    except Exception as e:
        status, output = 'error', str(e)

    with _lock:
        _history.append({
            'task': 'analyze_comments',
            'started_at': start.isoformat(),
            'status': status,
            'output': output,
        })
        if len(_history) > 50:
            _history.pop(0)


def start_jobs(interval_minutes=60):
    if not _scheduler.running:
        _scheduler.start()
    _scheduler.add_job(
        _run_analyze_job, 'interval',
        minutes=interval_minutes,
        id='analyze_job',
        replace_existing=True,
    )


def stop_jobs():
    if _scheduler.running:
        _scheduler.shutdown(wait=False)


def get_job_status():
    jobs = []
    if _scheduler.running:
        for job in _scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
            })
    return {'running': _scheduler.running, 'jobs': jobs}


def get_execution_history():
    with _lock:
        return {'history': list(reversed(_history))}
