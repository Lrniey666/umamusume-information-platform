from django.contrib import admin
from .models import CrawlerRun, CrawlerSchedule, CrawlerConfig

@admin.register(CrawlerRun)
class CrawlerRunAdmin(admin.ModelAdmin):
    list_display = ('run_id', 'source', 'status', 'triggered_by', 'started_at', 'ended_at', 'articles_new', 'articles_err')
    list_filter = ('source', 'status')
    ordering = ('-started_at',)

@admin.register(CrawlerSchedule)
class CrawlerScheduleAdmin(admin.ModelAdmin):
    list_display = ('source', 'mode', 'cron_expr', 'enabled')

@admin.register(CrawlerConfig)
class CrawlerConfigAdmin(admin.ModelAdmin):
    list_display = ('source', 'max_pages', 'delay_min', 'delay_max', 'use_playwright')
