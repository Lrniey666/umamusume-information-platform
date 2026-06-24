from django.db import models


class GameAnnouncement(models.Model):
    CATEGORY_CHOICES = [
        ('活動', '活動'),
        ('卡池', '卡池'),
        ('競賽', '競賽'),
        ('系統', '系統'),
        ('其他', '其他'),
    ]

    title          = models.CharField(max_length=255, verbose_name='公告標題')
    content        = models.TextField(verbose_name='公告內文')
    category       = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='其他', verbose_name='類別')
    source_url     = models.URLField(null=True, blank=True, max_length=500, verbose_name='來源連結')
    published_date = models.DateField(null=True, blank=True, verbose_name='發布日期')
    source         = models.CharField(max_length=20, default='bilibili', verbose_name='資料來源')
    created_at     = models.DateTimeField(auto_now_add=True, verbose_name='匯入時間')

    class Meta:
        ordering = ['-published_date', '-created_at']
        verbose_name = '遊戲公告'
        verbose_name_plural = '遊戲公告'

    def __str__(self):
        return f'[{self.category}] {self.title[:40]}'

    @property
    def comments_count(self):
        return self.comments.count()

    @property
    def is_analyzed(self):
        return hasattr(self, 'sentiment') and self.sentiment.analyzed_at is not None
