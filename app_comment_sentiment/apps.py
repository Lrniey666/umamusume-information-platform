import os
from django.apps import AppConfig


class AppCommentSentimentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app_comment_sentiment'
    verbose_name = '留言情緒分析'

    def ready(self):
        # 防止 autoreload 重複啟動、也防止 management commands（migrate 等）觸發排程
        import sys
        is_management_cmd = len(sys.argv) > 1 and sys.argv[1] in (
            'migrate', 'makemigrations', 'check', 'shell',
            'collectstatic', 'createsuperuser', 'dbshell',
        )
        if is_management_cmd:
            return
        if os.environ.get('RUN_MAIN') == 'true':
            from . import scheduler_manager
            try:
                scheduler_manager.start_jobs()
                print('[Scheduler] 背景排程已啟動')
            except Exception as e:
                print(f'[Scheduler] 啟動失敗：{e}')
