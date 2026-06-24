from django.db import models


class UmaCharacter(models.Model):
    """賽馬娘角色靜態參考資料（Phase 2d）。"""
    name_tw    = models.CharField(max_length=100, unique=True)   # 繁體中文名
    name_jp    = models.CharField(max_length=100, blank=True)    # 日文原名
    name_en    = models.CharField(max_length=100, blank=True)    # 英文名（可選）
    icon_url   = models.URLField(max_length=600, blank=True)     # 角色圖示 URL
    is_active  = models.BooleanField(default=True)               # 軟刪除
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'app_user_keyword_db'
        ordering  = ['name_tw']
        verbose_name      = '賽馬娘角色'
        verbose_name_plural = '賽馬娘角色'

    def __str__(self):
        return self.name_tw


class NewsData(models.Model):
    item_id         = models.CharField(max_length=255, primary_key=True)
    date            = models.DateField(null=True, blank=True)
    category        = models.CharField(max_length=255)
    title           = models.TextField()
    content         = models.TextField()
    link            = models.URLField(null=True, blank=True, max_length=500)
    photo_link      = models.URLField(null=True, blank=True, max_length=500)
    tokens_filtered = models.TextField(null=True, blank=True)
    token_pos       = models.TextField(null=True, blank=True)
    top_key_freq    = models.TextField(null=True, blank=True)
    sentiment       = models.FloatField(null=True, blank=True)
    source          = models.CharField(max_length=20, default='bilibili')
    status          = models.CharField(
        max_length=20,
        default='raw',
        choices=[
            ('raw',       '已爬取'),
            ('tokenized', '已斷詞'),
            ('labeled',   '已情感標記'),
        ],
        db_index=True,
    )

    class Meta:
        app_label = 'app_user_keyword_db'

    def __str__(self):
        return f"{self.item_id} | {self.category} | {self.date}"
