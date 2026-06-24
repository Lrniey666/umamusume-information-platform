from django.db import models
from app_uma_news.models import GameAnnouncement


class CommentSentiment(models.Model):
    announcement   = models.OneToOneField(
        GameAnnouncement,
        on_delete=models.CASCADE,
        related_name='sentiment',
        verbose_name='所屬公告',
    )
    positive_score = models.FloatField(null=True, blank=True, verbose_name='正面機率 (0~1)')
    negative_score = models.FloatField(null=True, blank=True, verbose_name='負面機率 (0~1)')
    neutral_score  = models.FloatField(null=True, blank=True, verbose_name='中立機率 (0~1)')

    excited      = models.FloatField(default=0.0, verbose_name='興奮 (%)')
    happy        = models.FloatField(default=0.0, verbose_name='開心 (%)')
    mixed        = models.FloatField(default=0.0, verbose_name='五味雜陳 (%)')
    disappointed = models.FloatField(default=0.0, verbose_name='失望 (%)')
    angry        = models.FloatField(default=0.0, verbose_name='生氣 (%)')
    sad          = models.FloatField(default=0.0, verbose_name='悲傷 (%)')

    ai_model    = models.CharField(max_length=100, null=True, blank=True, verbose_name='AI 模型')
    analyzed_at = models.DateTimeField(null=True, blank=True, verbose_name='分析時間')

    class Meta:
        verbose_name = '留言情緒分析'
        verbose_name_plural = '留言情緒分析'

    def __str__(self):
        return f'{self.announcement.title[:30]} - 情緒分析'


# ──────────────────────────────────────────────────────────────
# H2 修復：巴哈姆特哈啦板 Article / Comment / ArticleEmotion 模型
# ──────────────────────────────────────────────────────────────

class Article(models.Model):
    """巴哈姆特哈啦板貼文（由 scrape_bahamut management command 寫入）"""
    title          = models.CharField(max_length=500, verbose_name='標題')
    url            = models.URLField(max_length=500, unique=True, verbose_name='網址')
    category       = models.CharField(max_length=100, blank=True, verbose_name='分類')
    content        = models.TextField(blank=True, verbose_name='內容')
    published_date = models.DateField(null=True, blank=True, verbose_name='發佈日期')
    source         = models.CharField(max_length=100, default='bahamut', verbose_name='來源')

    positive_score = models.FloatField(null=True, blank=True, verbose_name='正面機率 (0~1)')
    negative_score = models.FloatField(null=True, blank=True, verbose_name='負面機率 (0~1)')
    neutral_score  = models.FloatField(null=True, blank=True, verbose_name='中立機率 (0~1)')
    analyzed_at    = models.DateTimeField(null=True, blank=True, verbose_name='情緒分析時間')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')

    class Meta:
        verbose_name = '哈啦板文章'
        verbose_name_plural = '哈啦板文章'
        ordering = ['-published_date', '-created_at']

    def __str__(self):
        return self.title[:50]


class Comment(models.Model):
    """哈啦板留言（由 scrape_bahamut 寫入，含 upvotes/downvotes）"""
    article    = models.ForeignKey(
        Article, on_delete=models.CASCADE,
        related_name='comments', verbose_name='所屬文章'
    )
    content    = models.TextField(verbose_name='留言內容')
    author     = models.CharField(max_length=200, blank=True, verbose_name='作者')
    upvotes    = models.IntegerField(default=0, verbose_name='讚數')
    downvotes  = models.IntegerField(default=0, verbose_name='噓數')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')

    class Meta:
        verbose_name = '哈啦板留言'
        verbose_name_plural = '哈啦板留言'

    def __str__(self):
        return f'[{self.article.title[:20]}] {self.content[:30]}'


class ArticleEmotion(models.Model):
    """文章情緒六維度（由 analyze_comments 寫入）"""
    article     = models.OneToOneField(
        Article, on_delete=models.CASCADE,
        related_name='emotion', verbose_name='所屬文章'
    )
    cheer_up    = models.FloatField(default=0.0, verbose_name='加油 (%)')
    happy       = models.FloatField(default=0.0, verbose_name='開心 (%)')
    mixed       = models.FloatField(default=0.0, verbose_name='五味雜陳 (%)')
    dumbfounded = models.FloatField(default=0.0, verbose_name='傻眼 (%)')
    angry       = models.FloatField(default=0.0, verbose_name='生氣 (%)')
    sad         = models.FloatField(default=0.0, verbose_name='悲傷 (%)')

    class Meta:
        verbose_name = '文章情緒六維度'
        verbose_name_plural = '文章情緒六維度'

    def __str__(self):
        return f'{self.article.title[:30]} - 情緒六維度'
