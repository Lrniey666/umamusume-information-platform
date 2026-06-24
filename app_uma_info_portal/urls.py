from django.urls import path
from . import views, api_views

app_name = 'app_uma_info_portal'

urlpatterns = [
    # ── 公開頁面 ──────────────────────────────────
    path('',                views.home,         name='home'),
    path('servers/',        views.servers,      name='servers'),
    path('servers/<str:guild_id>/manage/', views.server_manage, name='server_manage'),

    # ── Discord OAuth ─────────────────────────────
    path('auth/login/',     views.auth_login,    name='auth_login'),
    path('auth/callback/',  views.auth_callback, name='auth_callback'),
    path('auth/logout/',    views.auth_logout,   name='auth_logout'),

    # ── 伺服器設定 API ────────────────────────────
    path('api/guilds/<str:guild_id>/channels/',
         api_views.api_guild_channels,       name='api_guild_channels'),
    path('api/guilds/<str:guild_id>/roles/',
         api_views.api_guild_roles,          name='api_guild_roles'),
    path('api/guilds/<str:guild_id>/stats/',
         api_views.api_guild_stats,          name='api_guild_stats'),
    path('api/guilds/<str:guild_id>/settings/save/',
         api_views.api_guild_settings_save,  name='api_guild_settings_save'),
    path('api/guilds/<str:guild_id>/rules/add/',
         api_views.api_channel_rule_add,     name='api_channel_rule_add'),
    path('api/guilds/<str:guild_id>/rules/<int:pk>/delete/',
         api_views.api_channel_rule_delete,  name='api_channel_rule_delete'),
    path('api/guilds/<str:guild_id>/sync-cache/',
         api_views.api_sync_cache,              name='api_sync_cache'),
    path('api/guilds/<str:guild_id>/audits/',
         api_views.api_guild_audits,            name='api_guild_audits'),
    path('api/guilds/<str:guild_id>/confirm-news-channel/',
         api_views.api_confirm_news_channel,    name='api_confirm_news_channel'),
]
