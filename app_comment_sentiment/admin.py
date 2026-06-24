from django.contrib import admin
from .models import CommentSentiment


@admin.register(CommentSentiment)
class CommentSentimentAdmin(admin.ModelAdmin):
    list_display = ('announcement', 'positive_score', 'negative_score', 'neutral_score', 'ai_model', 'analyzed_at')
    list_filter  = ('ai_model',)
    ordering     = ('-analyzed_at',)
    readonly_fields = ('analyzed_at',)
