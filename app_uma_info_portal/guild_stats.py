"""
UMA Info Portal — 伺服器統計計算（總覽頁與 API 共用）
"""
from django.db.models import Max
from django.utils import timezone


def compute_guild_stats(guild_id: str, channel_count: int | None = None) -> dict:
    """
    依 guild_id 彙整 Discord 訊息與推播統計。
    channel_count 可從外部傳入（避免重複查詢 GuildChannelCache）。
    """
    try:
        from app_discord_bot.models import DiscordMessage, DiscordNewsLog
    except Exception:
        return _empty_stats(channel_count or 0)

    qs = DiscordMessage.objects.filter(guild_id=guild_id)
    msg_count = qs.count()
    uma_count = qs.filter(is_umamusume=True).count()
    pending_count = qs.filter(is_umamusume=None).count()
    nonuma_count = qs.filter(is_umamusume=False).count()
    news_count = DiscordNewsLog.objects.filter(guild_id=guild_id).count()
    converted_count = qs.exclude(news_data_id='').count()

    last_msg = qs.aggregate(last=Max('timestamp'))['last']
    uma_pct = round(uma_count / msg_count * 100, 1) if msg_count > 0 else 0.0

    if channel_count is None:
        from .models import DiscordGuild, GuildChannelCache
        guild = DiscordGuild.objects.filter(guild_id=guild_id).first()
        channel_count = (
            GuildChannelCache.objects.filter(guild=guild).count() if guild else 0
        )

    return {
        'msg_count':       msg_count,
        'uma_count':       uma_count,
        'pending_count':   pending_count,
        'nonuma_count':    nonuma_count,
        'news_count':      news_count,
        'converted_count': converted_count,
        'channel_count':   channel_count,
        'uma_pct':         uma_pct,
        'last_message_at': last_msg.strftime('%Y-%m-%d %H:%M') if last_msg else None,
        'refreshed_at':    timezone.localtime().strftime('%Y-%m-%d %H:%M:%S'),
    }


def _empty_stats(channel_count: int = 0) -> dict:
    return {
        'msg_count': 0, 'uma_count': 0, 'pending_count': 0, 'nonuma_count': 0,
        'news_count': 0, 'converted_count': 0, 'channel_count': channel_count,
        'uma_pct': 0.0, 'last_message_at': None,
        'refreshed_at': timezone.localtime().strftime('%Y-%m-%d %H:%M:%S'),
    }
