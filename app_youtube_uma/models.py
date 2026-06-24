from django.db import models


class YouTubeQuotaLog(models.Model):
    """每日 YouTube Data API v3 配額使用記錄"""
    date          = models.DateField(unique=True, verbose_name='日期')
    units_used    = models.IntegerField(default=0, verbose_name='已用配額')
    units_limit   = models.IntegerField(default=10000, verbose_name='配額上限')
    last_crawl_at = models.DateTimeField(null=True, blank=True, verbose_name='最後爬取時間')
    videos_added  = models.IntegerField(default=0, verbose_name='本次新增影片數')

    class Meta:
        ordering = ['-date']
        verbose_name = 'YouTube 配額記錄'
        verbose_name_plural = 'YouTube 配額記錄'

    def __str__(self):
        return f'{self.date} — {self.units_used}/{self.units_limit} units'

    @property
    def percent(self):
        if self.units_limit:
            return round(self.units_used / self.units_limit * 100, 1)
        return 0


class YouTubeVideo(models.Model):
    video_id      = models.CharField(max_length=20, primary_key=True)
    title         = models.TextField()
    channel_name  = models.CharField(max_length=200, blank=True)
    channel_id    = models.CharField(max_length=50, blank=True)
    published_at  = models.DateTimeField(null=True, blank=True)
    view_count    = models.BigIntegerField(default=0)
    like_count    = models.BigIntegerField(default=0)
    comment_count = models.BigIntegerField(default=0)
    thumbnail_url = models.URLField(max_length=500, blank=True)
    description   = models.TextField(blank=True)
    tags          = models.TextField(blank=True)
    sentiment     = models.FloatField(null=True, blank=True)
    crawled_at    = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['published_at']),
            models.Index(fields=['view_count']),
        ]
        ordering = ['-published_at']
        verbose_name = 'YouTube 影片'
        verbose_name_plural = 'YouTube 影片'

    def __str__(self):
        return self.title[:60]


class YouTubeComment(models.Model):
    comment_id   = models.CharField(max_length=100, primary_key=True)
    video        = models.ForeignKey(
        YouTubeVideo, on_delete=models.CASCADE, related_name='comments'
    )
    text         = models.TextField()
    author       = models.CharField(max_length=200, blank=True)
    like_count   = models.IntegerField(default=0)
    published_at = models.DateTimeField(null=True, blank=True)
    sentiment    = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ['-like_count']
        verbose_name = 'YouTube 留言'
        verbose_name_plural = 'YouTube 留言'

    def __str__(self):
        return f'[{self.video_id}] {self.text[:40]}'
