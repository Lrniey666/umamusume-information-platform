from django.db import models


class DiscordMessage(models.Model):
    """Discord 頻道訊息（爬取後存入）"""
    msg_id        = models.CharField(max_length=30, unique=True, verbose_name='訊息 ID')
    channel_id    = models.CharField(max_length=30, db_index=True, verbose_name='頻道 ID')
    channel_name  = models.CharField(max_length=200, blank=True, verbose_name='頻道名稱')
    author        = models.CharField(max_length=200, blank=True, verbose_name='作者')
    content       = models.TextField(verbose_name='訊息內容')
    timestamp     = models.DateTimeField(db_index=True, verbose_name='發送時間')
    is_umamusume  = models.BooleanField(null=True, db_index=True, verbose_name='是否馬娘相關')
    classified_by = models.CharField(
        max_length=20, blank=True,
        choices=[('keyword', '關鍵字'), ('gemini', 'Gemini AI'), ('', '未分類')],
        verbose_name='分類方式'
    )
    news_data_id  = models.CharField(max_length=50, blank=True, verbose_name='對應 NewsData ID')
    guild_id      = models.CharField(max_length=30, blank=True, db_index=True, verbose_name='伺服器 ID')
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Discord 訊息'
        verbose_name_plural = 'Discord 訊息'
        ordering = ['-timestamp']

    def __str__(self):
        return f'[{self.channel_name}] {self.content[:50]}'


class DiscordBotConfig(models.Model):
    """Discord Bot 設定（可在 Admin 後台管理）"""
    name         = models.CharField(max_length=100, unique=True, verbose_name='設定名稱')
    channel_id   = models.CharField(max_length=30, verbose_name='頻道 ID')
    channel_type = models.CharField(
        max_length=20, default='crawl',
        choices=[('crawl', '爬取頻道'), ('news', '新聞推播頻道')],
        verbose_name='頻道類型'
    )
    is_active    = models.BooleanField(default=True, verbose_name='啟用')
    note         = models.TextField(blank=True, verbose_name='備注')
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Discord Bot 設定'
        verbose_name_plural = 'Discord Bot 設定'

    def __str__(self):
        return f'{self.name} ({self.channel_id})'


class DiscordNewsLog(models.Model):
    """Discord 新聞推播紀錄"""
    channel_id  = models.CharField(max_length=30, verbose_name='推播頻道 ID')
    content     = models.TextField(verbose_name='推播內容')
    model_used  = models.CharField(max_length=50, verbose_name='使用的 AI 模型')
    message_ids = models.TextField(blank=True, verbose_name='Discord 訊息 ID 清單（逗號分隔）')
    guild_id    = models.CharField(max_length=30, blank=True, db_index=True, verbose_name='伺服器 ID')
    pinged_role_id = models.CharField(max_length=30, blank=True, verbose_name='Ping 的身分組 ID')
    status      = models.CharField(
        max_length=20, default='pending',
        choices=[('sent', '已推播'), ('failed', '失敗'), ('pending', '待推播')],
        verbose_name='狀態'
    )
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Discord 新聞推播紀錄'
        verbose_name_plural = 'Discord 新聞推播紀錄'
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.status}] {self.created_at.strftime("%Y-%m-%d %H:%M")} → #{self.channel_id}'


class DiscordCrawlSettings(models.Model):
    """爬取全域設定（單筆 singleton，pk=1）"""
    crawl_limit  = models.IntegerField(default=1000, verbose_name='每頻道訊息上限（0 = 不限）')
    concurrency  = models.IntegerField(default=3,    verbose_name='並行頻道數（1–10）')
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '爬取全域設定'
        verbose_name_plural = '爬取全域設定'

    def __str__(self):
        return f'爬取設定：上限={self.crawl_limit}, 並行={self.concurrency}'

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class DiscordTaskRun(models.Model):
    """Discord 控制台手動任務執行記錄（含進度與日誌）。"""
    TASK_CHOICES = [
        ('crawl', '爬取頻道訊息'),
        ('classify', '分類待分類訊息'),
        ('convert', '轉換至 NewsData'),
        ('news', '手動推播 AI 新聞'),
    ]
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('running', '執行中'),
        ('success', '成功'),
        ('failed', '失敗'),
        ('cancelled', '取消'),
    ]
    RUNNER_CHOICES = [
        ('bot',    '持久 Bot 行程'),
        ('thread', 'Django 執行緒'),
    ]

    task_type         = models.CharField(max_length=20, choices=TASK_CHOICES, db_index=True, verbose_name='任務類型')
    status            = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True, verbose_name='狀態')
    runner            = models.CharField(max_length=10, choices=RUNNER_CHOICES, default='thread', verbose_name='執行方式')
    cancel_requested  = models.BooleanField(default=False, db_index=True, verbose_name='已請求取消')
    progress_pct      = models.PositiveSmallIntegerField(default=0, verbose_name='進度百分比')
    estimated_seconds = models.PositiveIntegerField(default=0, verbose_name='預估秒數')
    started_at        = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name='開始時間')
    ended_at          = models.DateTimeField(null=True, blank=True, verbose_name='結束時間')
    triggered_by      = models.CharField(max_length=60, blank=True, default='admin-ui', verbose_name='觸發來源')
    summary           = models.CharField(max_length=255, blank=True, default='', verbose_name='摘要')
    error_message     = models.TextField(blank=True, default='', verbose_name='錯誤訊息')
    result_json       = models.JSONField(default=dict, blank=True, verbose_name='結果 JSON')
    log_text          = models.TextField(blank=True, default='', verbose_name='執行日誌')
    created_at        = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Discord 任務執行記錄'
        verbose_name_plural = 'Discord 任務執行記錄'
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.status}] {self.task_type} #{self.pk}'
