from django.contrib import admin
from .models import GameAnnouncement


@admin.register(GameAnnouncement)
class GameAnnouncementAdmin(admin.ModelAdmin):
    list_display  = ('title', 'category', 'published_date', 'source', 'comment_count_display', 'is_analyzed_display')
    list_filter   = ('category', 'source')
    search_fields = ('title', 'content')
    ordering      = ('-published_date',)

    def comment_count_display(self, obj):
        return obj.comments_count
    comment_count_display.short_description = '留言數'

    def is_analyzed_display(self, obj):
        return '✅' if obj.is_analyzed else '⏳'
    is_analyzed_display.short_description = '已分析'
