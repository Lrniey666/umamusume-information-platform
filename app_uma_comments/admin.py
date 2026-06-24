from django.contrib import admin
from .models import PlayerComment


@admin.register(PlayerComment)
class PlayerCommentAdmin(admin.ModelAdmin):
    list_display  = ('floor', 'announcement', 'author', 'upvotes', 'content_preview')
    list_filter   = ('announcement__category',)
    search_fields = ('content', 'author')
    ordering      = ('-upvotes',)

    def content_preview(self, obj):
        return obj.content[:50]
    content_preview.short_description = '留言內容'
