from django.db import models
from uuid import uuid4


def _default_run_id():
    return uuid4().hex


SOURCES = ['bilibili', 'bahamut', 'udn', 'ettoday', 'gamme']
SOURCE_CHOICES = [(s, s) for s in SOURCES]

STATUS_CHOICES = [
    ('running',   '運行中'),
    ('success',   '成功'),
    ('failed',    '失敗'),
    ('cancelled', '已取消'),
]

TRIGGER_CHOICES = [
    ('manual',   '手動觸發'),
    ('schedule', '排程觸發'),
]

MODE_CHOICES = [
    ('daily',    '每日'),
    ('weekly',   '每週'),
    ('interval', '固定間隔'),
]


class CrawlerRun(models.Model):
    run_id       = models.CharField(max_length=64, primary_key=True, default=_default_run_id)
    source       = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    triggered_by = models.CharField(max_length=20, choices=TRIGGER_CHOICES, default='manual')
    started_at   = models.DateTimeField(auto_now_add=True)
    ended_at     = models.DateTimeField(null=True, blank=True)
    articles_new = models.IntegerField(default=0)
    articles_skip= models.IntegerField(default=0)
    articles_err = models.IntegerField(default=0)
    log_text     = models.TextField(blank=True, default='')

    class Meta:
        app_label = 'app_crawler_admin'
        ordering  = ['-started_at']

    def __str__(self):
        return f"[{self.source}] {self.status} @ {self.started_at:%Y-%m-%d %H:%M}"

    def duration_seconds(self):
        if self.ended_at and self.started_at:
            return int((self.ended_at - self.started_at).total_seconds())
        return None


class CrawlerSchedule(models.Model):
    source     = models.CharField(max_length=20, choices=SOURCE_CHOICES, unique=True)
    mode       = models.CharField(max_length=20, choices=MODE_CHOICES, default='daily')
    cron_expr  = models.CharField(max_length=60, default='0 2 * * *')
    enabled    = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'app_crawler_admin'

    def __str__(self):
        return f"[{self.source}] {self.cron_expr} ({'啟用' if self.enabled else '停用'})"


class CrawlerConfig(models.Model):
    source         = models.CharField(max_length=20, choices=SOURCE_CHOICES, unique=True)
    max_pages      = models.IntegerField(default=50)
    delay_min      = models.FloatField(default=0.8)
    delay_max      = models.FloatField(default=1.5)
    use_playwright = models.BooleanField(default=False)
    user_agent     = models.TextField(
        blank=True,
        default='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    extra_notes    = models.TextField(blank=True, default='')

    class Meta:
        app_label = 'app_crawler_admin'

    def __str__(self):
        return f"Config:{self.source}"
