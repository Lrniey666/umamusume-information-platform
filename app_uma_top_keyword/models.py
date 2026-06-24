from django.db import models


class TopKeyword(models.Model):
    keyword       = models.CharField(max_length=100)
    category      = models.CharField(max_length=50)
    freq          = models.IntegerField()
    source        = models.CharField(max_length=50, blank=True, default='')
    window_days   = models.IntegerField(default=0)
    computed_date = models.DateField()

    class Meta:
        app_label = 'app_uma_top_keyword'
        unique_together = ('keyword', 'category', 'source', 'window_days', 'computed_date')
        indexes = [
            models.Index(fields=['category', '-freq']),
            models.Index(fields=['computed_date', 'window_days']),
        ]

    def __str__(self):
        return f"{self.keyword} | {self.category} | {self.freq}"
