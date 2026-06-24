from django.contrib import admin
from .models import YouTubeVideo, YouTubeComment


class YouTubeCommentInline(admin.TabularInline):
    model = YouTubeComment
    extra = 0
    fields = ('comment_id', 'author', 'text', 'like_count', 'sentiment')
    readonly_fields = ('comment_id',)


@admin.register(YouTubeVideo)
class YouTubeVideoAdmin(admin.ModelAdmin):
    list_display = ('video_id', 'title', 'channel_name', 'published_at', 'view_count', 'sentiment')
    list_filter = ('channel_name',)
    search_fields = ('title', 'channel_name', 'description')
    readonly_fields = ('crawled_at',)
    inlines = [YouTubeCommentInline]


@admin.register(YouTubeComment)
class YouTubeCommentAdmin(admin.ModelAdmin):
    list_display = ('comment_id', 'video', 'author', 'like_count', 'sentiment')
    search_fields = ('text', 'author')
