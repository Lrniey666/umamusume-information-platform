from django.conf import settings
from django.db import models


class GeneratedNewsArticle(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_CHOICES = (
        (STATUS_DRAFT, '草稿'),
        (STATUS_PUBLISHED, '已發布'),
    )

    query = models.CharField(max_length=200)
    category = models.CharField(max_length=50, default='全部')
    source = models.CharField(max_length=20, default='all')
    weeks = models.PositiveSmallIntegerField(default=4)
    topk = models.PositiveSmallIntegerField(default=8)

    title = models.CharField(max_length=220)
    subtitle = models.CharField(max_length=320, blank=True)
    content = models.TextField()
    summary = models.TextField(blank=True)
    cover_image_url = models.URLField(max_length=600, blank=True)
    source_chunks = models.JSONField(default=list, blank=True)
    source_links = models.JSONField(default=list, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PUBLISHED,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'AI 生成新聞'
        verbose_name_plural = 'AI 生成新聞'

    def __str__(self):
        return f'{self.title} ({self.status})'
