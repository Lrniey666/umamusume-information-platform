from django.contrib import admin
from .models import DiscordMessage, DiscordBotConfig, DiscordNewsLog, DiscordTaskRun


@admin.register(DiscordMessage)
class DiscordMessageAdmin(admin.ModelAdmin):
    list_display = ('msg_id', 'channel_name', 'author', 'content_preview',
                    'timestamp', 'is_umamusume', 'classified_by', 'guild_id')
    list_filter = ('is_umamusume', 'classified_by', 'channel_name', 'guild_id')
    search_fields = ('content', 'author', 'channel_name', 'guild_id', 'msg_id')
    readonly_fields = ('msg_id', 'created_at')

    def content_preview(self, obj):
        return obj.content[:60]
    content_preview.short_description = '內容預覽'


@admin.register(DiscordBotConfig)
class DiscordBotConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'channel_id', 'channel_type', 'is_active')
    list_filter = ('channel_type', 'is_active')
    search_fields = ('name', 'channel_id')


@admin.register(DiscordNewsLog)
class DiscordNewsLogAdmin(admin.ModelAdmin):
    list_display = ('channel_id', 'guild_id', 'model_used', 'status', 'created_at', 'content_preview')
    list_filter = ('status', 'model_used', 'guild_id')
    readonly_fields = ('created_at',)

    def content_preview(self, obj):
        return obj.content[:80]
    content_preview.short_description = '內容預覽'


@admin.register(DiscordTaskRun)
class DiscordTaskRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'task_type', 'status', 'progress_pct', 'triggered_by', 'started_at', 'ended_at')
    list_filter = ('task_type', 'status', 'triggered_by')
    search_fields = ('summary', 'error_message', 'triggered_by')
    readonly_fields = ('created_at', 'updated_at')
