"""
scheduler.py — APScheduler 整合

每個 CrawlerSchedule 記錄對應一個 APScheduler job。
AppConfig.ready() 呼叫 init_scheduler() 載入所有啟用的排程。
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(timezone='Asia/Taipei')
    return _scheduler


def _crawl_job(source: str):
    """APScheduler 呼叫此函式觸發爬蟲"""
    from . import runner
    logger.info('[Scheduler] 觸發爬蟲：%s', source)
    result = runner.trigger(source, triggered_by='schedule')
    if not result.get('ok'):
        logger.warning('[Scheduler] 觸發失敗：%s — %s', source, result.get('error'))


def _job_id(source: str) -> str:
    return f'crawl_{source}'


def add_or_update_job(schedule):
    """新增或更新 APScheduler job"""
    sched = get_scheduler()
    jid   = _job_id(schedule.source)

    # 移除舊 job（如果存在）
    if sched.get_job(jid):
        sched.remove_job(jid)

    if not schedule.enabled:
        return

    parts = schedule.cron_expr.split()
    if len(parts) == 5:
        minute, hour, day, month, day_of_week = parts
        trigger = CronTrigger(
            minute=minute, hour=hour,
            day=day, month=month, day_of_week=day_of_week,
            timezone='Asia/Taipei'
        )
    else:
        # 備用：每小時
        trigger = IntervalTrigger(hours=1)

    sched.add_job(_crawl_job, trigger, id=jid,
                  args=[schedule.source], replace_existing=True,
                  misfire_grace_time=300)
    logger.info('[Scheduler] 已排程 %s：%s', schedule.source, schedule.cron_expr)


def remove_job(source: str):
    sched = get_scheduler()
    jid   = _job_id(source)
    if sched.get_job(jid):
        sched.remove_job(jid)


def init_scheduler():
    """AppConfig.ready() 呼叫此函式，讀取 DB 並啟動排程器"""
    from .models import CrawlerSchedule
    sched = get_scheduler()
    if sched.running:
        return

    try:
        schedules = CrawlerSchedule.objects.filter(enabled=True)
        for s in schedules:
            add_or_update_job(s)
    except Exception as exc:
        logger.warning('[Scheduler] 初始化排程時發生錯誤（可能是首次啟動前尚未 migrate）：%s', exc)

    try:
        sched.start()
        logger.info('[Scheduler] APScheduler 已啟動')
    except Exception as exc:
        logger.warning('[Scheduler] APScheduler 啟動失敗：%s', exc)
