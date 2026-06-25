from django.urls import path
from . import views, api_views

app_name = 'app_crawler_admin'

urlpatterns = [
    # ── 頁面 ──────────────────────────────────────
    path('',                           views.dashboard,            name='dashboard'),
    path('monitor/<str:source>/',      views.live_monitor,         name='live_monitor'),
    path('schedule/',                  views.schedule_page,        name='schedule'),
    path('history/',                   views.history_page,         name='history'),
    path('stats/',                     views.stats_page,           name='stats'),
    path('settings/',                  views.settings_page,        name='settings'),
    # ── 新增管理頁面 ──────────────────────────────
    path('youtube/',                   views.youtube_management,   name='youtube_management'),
    path('discord/',                   views.discord_management,   name='discord_management'),
    path('rag/',                       views.rag_management,       name='rag_management'),
    path('pipeline/',                  views.pipeline_page,        name='pipeline'),
    path('ai-news/',                   views.ai_news_management,   name='ai_news_management'),
    path('data-manager/',              views.data_manager,         name='data_manager'),

    # ── REST API（原有）──────────────────────────
    path('api/status/',                      api_views.api_status_all,       name='api_status_all'),
    path('api/status/<str:source>/',         api_views.api_status_one,       name='api_status_one'),
    path('api/trigger/<str:source>/',        api_views.api_trigger,          name='api_trigger'),
    path('api/stop/<str:source>/',           api_views.api_stop,             name='api_stop'),
    path('api/log/<str:source>/',            api_views.api_log,              name='api_log'),
    path('api/history/',                     api_views.api_history,          name='api_history'),
    path('api/history/<str:run_id>/',        api_views.api_history_detail,   name='api_history_detail'),
    path('api/schedule/',                    api_views.api_schedule_list,    name='api_schedule_list'),
    path('api/schedule/save/',               api_views.api_schedule_save,    name='api_schedule_save'),
    path('api/schedule/delete/<str:source>/',api_views.api_schedule_delete,  name='api_schedule_delete'),
    path('api/config/<str:source>/',         api_views.api_config_get,       name='api_config_get'),
    path('api/config/<str:source>/save/',    api_views.api_config_save,      name='api_config_save'),
    path('api/stats/',                       api_views.api_stats,            name='api_stats'),
    # ── 新增 API（C-AD、E1-E2、F1）──────────────
    path('api/source_stats/',                api_views.api_source_stats,     name='api_source_stats'),
    path('api/sentiment_stats/',             api_views.api_sentiment_stats,  name='api_sentiment_stats'),
    path('api/rag_status/',                  api_views.api_rag_status,       name='api_rag_status'),
    path('api/rebuild_rag/',                 api_views.api_rebuild_rag,      name='api_rebuild_rag'),
    path('api/youtube_quota/',               api_views.api_youtube_quota,          name='api_youtube_quota'),
    path('api/youtube_crawl/',               api_views.api_youtube_crawl,          name='api_youtube_crawl'),
    path('api/youtube-sentiment-stats/',     api_views.api_youtube_sentiment_stats, name='api_youtube_sentiment_stats'),
    path('api/youtube-analyze/',             api_views.api_youtube_analyze,         name='api_youtube_analyze'),
    path('api/import_bahamut/',              api_views.api_import_bahamut_articles, name='api_import_bahamut'),
    path('api/run_pipeline/',                api_views.api_run_pipeline,     name='api_run_pipeline'),
    path('api/pipeline_status/',             api_views.api_pipeline_status,  name='api_pipeline_status'),
    path('api/platform_stats/',              api_views.api_platform_stats,   name='api_platform_stats'),
    path('api/upload_kb/',                   api_views.api_upload_kb,        name='api_upload_kb'),
    # ── 留言情感排程控制（移轉自前台）──────────────────────
    path('api/comment_sentiment/status/',    api_views.api_comment_scheduler_status,   name='api_comment_scheduler_status'),
    path('api/comment_sentiment/start/',     api_views.api_comment_scheduler_start,    name='api_comment_scheduler_start'),
    path('api/comment_sentiment/stop/',      api_views.api_comment_scheduler_stop,     name='api_comment_scheduler_stop'),
    path('api/comment_sentiment/run_task/',  api_views.api_comment_scheduler_run_task, name='api_comment_scheduler_run_task'),
    path('api/comment_sentiment/history/',   api_views.api_comment_scheduler_history,  name='api_comment_scheduler_history'),
    # ── 資料清理 API（G1）────────────────────────
    path('api/data_inventory/',              api_views.api_data_inventory,   name='api_data_inventory'),
    path('api/cleanup_files/',               api_views.api_cleanup_files,    name='api_cleanup_files'),
    path('api/clear_db/',                    api_views.api_clear_db,         name='api_clear_db'),
    # ── 資料管理 API（Phase 1）──────────────────
    path('api/data-manager/stats/',         api_views.api_data_manager_stats,         name='api_data_manager_stats'),
    path('api/data-manager/clear-source/',  api_views.api_data_manager_clear_source,  name='api_data_manager_clear_source'),
    path('api/data-manager/clear-date/',    api_views.api_data_manager_clear_date,    name='api_data_manager_clear_date'),
    path('api/data-manager/delete-item/',   api_views.api_data_manager_delete_item,   name='api_data_manager_delete_item'),
    path('api/data-manager/reset-status/', api_views.api_data_manager_reset_status,  name='api_data_manager_reset_status'),
    path('api/data-manager/scan/',          api_views.api_data_manager_scan,          name='api_data_manager_scan'),
    # ── Discord Bot 行程開關 ─────────────────────
    path('api/discord/bot/status/',                  api_views.api_discord_bot_status,       name='api_discord_bot_status'),
    path('api/discord/bot/start/',                   api_views.api_discord_bot_start,        name='api_discord_bot_start'),
    path('api/discord/bot/stop/',                    api_views.api_discord_bot_stop,         name='api_discord_bot_stop'),
    # ── Discord Bot 管理 API（整合至控制台）──────
    path('api/discord/stats/',                       api_views.api_discord_stats,            name='api_discord_stats'),
    path('api/discord/channels/add/',                api_views.api_discord_channel_add,      name='api_discord_channel_add'),
    path('api/discord/channels/<int:pk>/delete/',    api_views.api_discord_channel_delete,   name='api_discord_channel_delete'),
    path('api/discord/channels/<int:pk>/toggle/',    api_views.api_discord_channel_toggle,   name='api_discord_channel_toggle'),
    path('api/discord/run_classify/',                api_views.api_discord_run_classify,     name='api_discord_run_classify'),
    path('api/discord/run_crawl/',                   api_views.api_discord_run_crawl,        name='api_discord_run_crawl'),
    path('api/discord/run_convert/',                 api_views.api_discord_run_convert,      name='api_discord_run_convert'),
    path('api/discord/trigger_news/',                api_views.api_discord_trigger_news,     name='api_discord_trigger_news'),
    path('api/discord/task/start/',                  api_views.api_discord_task_start,       name='api_discord_task_start'),
    path('api/discord/task/status/',                 api_views.api_discord_task_status,      name='api_discord_task_status'),
    path('api/discord/task/<int:run_id>/log/',       api_views.api_discord_task_log,         name='api_discord_task_log'),
    path('api/discord/task/<int:run_id>/cancel/',    api_views.api_discord_task_cancel,      name='api_discord_task_cancel'),
    path('api/discord/recent_messages/',             api_views.api_discord_recent_messages,  name='api_discord_recent_messages'),
    path('api/discord/messages/delete/',             api_views.api_discord_delete_messages,  name='api_discord_delete_messages'),
    # ── 爬取全域設定 ──────────────────────────────────
    path('api/discord/crawl-settings/',              api_views.api_discord_crawl_settings_get,   name='api_discord_crawl_settings_get'),
    path('api/discord/crawl-settings/save/',         api_views.api_discord_crawl_settings_save,  name='api_discord_crawl_settings_save'),
    # ── AI 新聞頁 Discord 推播 ─────────────────────
    path('api/ai-news/discord-status/',              api_views.api_ai_news_discord_status,       name='api_ai_news_discord_status'),
    path('api/ai-news/discord-push-weekly/',         api_views.api_ai_news_discord_push_weekly,  name='api_ai_news_discord_push_weekly'),
    path('api/ai-news/discord-push-article/',        api_views.api_ai_news_discord_push_article, name='api_ai_news_discord_push_article'),
    path('api/ai-news/discord-push-articles/',       api_views.api_ai_news_discord_push_articles, name='api_ai_news_discord_push_articles'),
]
