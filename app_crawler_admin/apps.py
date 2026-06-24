import os
import sys
from django.apps import AppConfig

# manage.py commands that should NOT start the scheduler
_NO_SCHEDULER_CMDS = {'migrate', 'makemigrations', 'collectstatic', 'shell',
                      'test', 'check', 'dbshell', 'showmigrations'}


class AppCrawlerAdminConfig(AppConfig):
    name            = 'app_crawler_admin'
    verbose_name    = '情報站控制台'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        # Skip during management commands (migrate, etc.)
        argv1 = sys.argv[1] if len(sys.argv) > 1 else ''
        if argv1 in _NO_SCHEDULER_CMDS:
            return

        # 清理上次伺服器中途停止／autoreload 時遺留的 'running' 孤兒記錄。
        # 須在 RUN_MAIN 判斷「之前」執行，因為真正處理請求並啟動爬蟲的 worker
        # 子行程帶有 RUN_MAIN=='true'；若放在 return 之後，worker 重載後永遠不會清理。
        try:
            from .models import CrawlerRun
            from django.utils import timezone
            orphans = CrawlerRun.objects.filter(status='running')
            count = orphans.count()
            if count:
                orphans.update(status='failed', ended_at=timezone.now())
                import logging
                logging.getLogger(__name__).warning(
                    '[CrawlerAdmin] 啟動清理：%d 筆孤兒 running 記錄已標記為 failed', count
                )
        except Exception:
            pass

        # scheduler 僅在 reloader 父行程啟動一次（維持原行為）
        if os.environ.get('RUN_MAIN') == 'true':
            return

        from .scheduler import init_scheduler
        try:
            init_scheduler()
        except Exception:
            pass
