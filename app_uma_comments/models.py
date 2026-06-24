from django.db import models
from app_uma_news.models import GameAnnouncement


class PlayerComment(models.Model):
    announcement = models.ForeignKey(
        GameAnnouncement,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='所屬公告',
    )
    content    = models.TextField(verbose_name='留言內容')
    author     = models.CharField(max_length=100, null=True, blank=True, verbose_name='留言者')
    upvotes    = models.IntegerField(default=0, verbose_name='讚數')
    downvotes  = models.IntegerField(default=0, verbose_name='倒讚數')
    floor      = models.IntegerField(default=0, verbose_name='樓層')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='爬取時間')

    class Meta:
        ordering = ['-upvotes', 'floor']
        verbose_name = '玩家留言'
        verbose_name_plural = '玩家留言'

    def __str__(self):
        return f'#{self.floor} {self.content[:30]}'
