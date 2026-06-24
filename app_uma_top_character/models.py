from django.db import models


class TopCharacter(models.Model):
    character     = models.CharField(max_length=100)
    category      = models.CharField(max_length=50)
    mention_count = models.IntegerField()
    source        = models.CharField(max_length=50, blank=True, default='')
    window_days   = models.IntegerField(default=0)
    computed_date = models.DateField()

    class Meta:
        app_label = 'app_uma_top_character'
        unique_together = ('character', 'category', 'source', 'window_days', 'computed_date')
        indexes = [
            models.Index(fields=['category', '-mention_count']),
            models.Index(fields=['computed_date', 'window_days']),
        ]

    def __str__(self):
        return f"{self.character} | {self.category} | {self.mention_count}"
