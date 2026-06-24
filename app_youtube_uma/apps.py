import os
from django.apps import AppConfig


class AppYoutubeUmaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app_youtube_uma'
    verbose_name = 'YouTube 賽馬娘影片'

    def ready(self):
        if os.environ.get('RUN_MAIN') == 'true':
            return
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from django_apscheduler.jobstores import DjangoJobStore
            from .jobs import crawl_youtube_job, analyze_youtube_sentiment_job

            scheduler = BackgroundScheduler()
            scheduler.add_jobstore(DjangoJobStore(), 'youtube')
            scheduler.add_job(
                crawl_youtube_job, 'interval', hours=6,
                id='crawl_youtube', replace_existing=True
            )
            scheduler.add_job(
                analyze_youtube_sentiment_job, 'cron',
                hour=3, id='analyze_youtube_sentiment', replace_existing=True
            )
            scheduler.start()
        except Exception as e:
            print(f'[app_youtube_uma] Scheduler 啟動失敗: {e}')
