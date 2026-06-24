"""
D7: Discord Bot APScheduler 排程
新架構：
  · 爬取任務：每 60 分鐘，依 GuildSetting.read_scope 逐伺服器執行
  · 分類/轉換：不變
  · 推播任務：每小時執行一次，依 GuildSetting.news_hour 匹配當前小時，
              每個伺服器可有各自的推播時間（台北時區）
"""
import asyncio
import os
import logging
from asgiref.sync import sync_to_async

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)


def start_discord_scheduler(bot):
    """啟動 Discord Bot 排程器"""
    scheduler = AsyncIOScheduler(timezone='Asia/Taipei')

    # ── 爬取（每 60 分鐘）──────────────────────────────────
    from .crawler import crawl_all_channels
    scheduler.add_job(
        lambda: asyncio.ensure_future(crawl_all_channels(bot)),
        'interval', minutes=60, id='discord_crawl',
    )

    # ── 分類（每 2 小時）───────────────────────────────────
    from .classifier import run_classifier
    scheduler.add_job(run_classifier, 'interval', hours=2, id='discord_classify')

    # ── 每日 01:00 轉換 ────────────────────────────────────
    from .converter import convert_discord_to_newsdata
    scheduler.add_job(
        convert_discord_to_newsdata, 'cron', hour=1, minute=0, id='discord_convert',
    )

    # ── 每小時整點：依 GuildSetting.news_hour 推播 ─────────
    async def post_news_job():
        """每小時執行，只推播 news_hour == 當前小時 的伺服器"""
        import pytz
        from datetime import datetime
        tz = pytz.timezone('Asia/Taipei')
        now_hour = datetime.now(tz).hour

        await _run_per_guild_news(bot, now_hour)

    scheduler.add_job(
        lambda: asyncio.ensure_future(post_news_job()),
        'cron', minute=0, id='discord_news_per_guild',
    )

    scheduler.start()
    logger.info('[Scheduler] Discord Bot 排程已啟動')


async def _run_per_guild_news(bot, current_hour: int, force_send: bool = False):
    """
    依 GuildSetting 逐伺服器推播新聞摘要。
    支援雙管齊下：GuildSetting（新） + DiscordBotConfig（舊 fallback）。
    """
    from .news_generator import generate_news, split_for_discord
    from .models import DiscordBotConfig, DiscordNewsLog

    sent_guild_ids = set()
    sent_count = 0
    failed_count = 0

    # ── 新版：GuildSetting 逐伺服器 ─────────────────────────
    try:
        from app_uma_info_portal.models import GuildSetting

        def _load_guild_settings():
            settings_qs = GuildSetting.objects.filter(news_enabled=True).select_related('guild')
            if not force_send:
                settings_qs = settings_qs.filter(news_hour=current_hour)
            return list(settings_qs)

        guild_settings = await sync_to_async(_load_guild_settings, thread_sensitive=True)()

        for setting in guild_settings:
            if not setting.news_channel_id:
                continue

            raw_channel_id = (setting.news_channel_id or '').strip()
            if not raw_channel_id.isdigit():
                logger.warning(f'[NewsBot] 無效推播頻道 ID {raw_channel_id}（{setting.guild.name}），跳過')
                failed_count += 1
                continue

            channel_id = int(raw_channel_id)
            channel = bot.get_channel(channel_id)
            if channel is None:
                # get_channel 只搜本地快取；改用 fetch_channel 直接查詢 Discord API
                try:
                    channel = await bot.fetch_channel(channel_id)
                except Exception as fe:
                    logger.warning(f'[NewsBot] 找不到推播頻道 {channel_id}（{setting.guild.name}）：{fe}，跳過')
                    failed_count += 1
                    continue
            if not hasattr(channel, 'send'):
                logger.warning(f'[NewsBot] 頻道 {channel_id}（{setting.guild.name}）不支援直接發送訊息，跳過')
                failed_count += 1
                continue

            model_env  = os.getenv('DISCORD_NEWS_MODEL', 'gemini')
            tone       = setting.news_tone or 'lively'
            text       = generate_news(model=model_env, tone=tone)
            model_name = 'claude-sonnet-4-6' if model_env == 'claude' else 'gemini-3.5-flash'

            # Ping 身分組
            ping_prefix = ''
            if setting.ping_role_id:
                ping_prefix = f'<@&{setting.ping_role_id}> '

            msg_ids = []
            try:
                parts = split_for_discord(text)
                for i, part in enumerate(parts):
                    content = (ping_prefix + part) if i == 0 else part
                    sent = await channel.send(content)
                    msg_ids.append(str(sent.id))

                await sync_to_async(DiscordNewsLog.objects.create, thread_sensitive=True)(
                    channel_id   = str(channel_id),
                    guild_id     = setting.guild.guild_id,
                    content      = text,
                    model_used   = model_name,
                    message_ids  = ','.join(msg_ids),
                    pinged_role_id = setting.ping_role_id or '',
                    status       = 'sent',
                )
                sent_guild_ids.add(setting.guild.guild_id)
                sent_count += 1
                logger.info(f'[NewsBot] 推播完成 → {setting.guild.name}（{len(msg_ids)} 則）')
            except Exception as e:
                await sync_to_async(DiscordNewsLog.objects.create, thread_sensitive=True)(
                    channel_id = str(channel_id),
                    guild_id   = setting.guild.guild_id,
                    content    = text,
                    model_used = model_name,
                    status     = 'failed',
                )
                failed_count += 1
                logger.error(f'[NewsBot] 推播失敗 → {setting.guild.name}: {e}')
    except Exception as e:
        logger.error(f'[NewsBot] GuildSetting 推播流程失敗：{e}')

    # ── Fallback：DiscordBotConfig（舊版相容，每日 20:00）──
    if (force_send or current_hour == 20) and not sent_guild_ids:
        news_configs = await sync_to_async(
            lambda: list(DiscordBotConfig.objects.filter(channel_type='news', is_active=True)),
            thread_sensitive=True,
        )()
        if not news_configs:
            logger.info('[NewsBot] 無啟用的推播頻道（舊版），跳過')
            return {'sent': sent_count, 'failed': failed_count}

        model_env  = os.getenv('DISCORD_NEWS_MODEL', 'gemini')
        text       = generate_news(model=model_env)
        model_name = 'claude-sonnet-4-6' if model_env == 'claude' else 'gemini-3.5-flash'

        from .news_generator import split_for_discord

        for cfg in news_configs:
            raw_channel_id = (cfg.channel_id or '').strip()
            if not raw_channel_id.isdigit():
                logger.warning(f'[NewsBot] 無效頻道 ID {raw_channel_id}（{cfg.name}），跳過')
                failed_count += 1
                continue
            channel_id = int(raw_channel_id)
            channel = bot.get_channel(channel_id)
            if channel is None:
                try:
                    channel = await bot.fetch_channel(channel_id)
                except Exception as fe:
                    logger.warning(f'[NewsBot] 找不到頻道 {channel_id}（{cfg.name}）：{fe}，跳過')
                    failed_count += 1
                    continue
            if not hasattr(channel, 'send'):
                logger.warning(f'[NewsBot] 頻道 {channel_id}（{cfg.name}）不支援直接發送訊息，跳過')
                failed_count += 1
                continue
            msg_ids = []
            try:
                for part in split_for_discord(text):
                    sent = await channel.send(part)
                    msg_ids.append(str(sent.id))
                await sync_to_async(DiscordNewsLog.objects.create, thread_sensitive=True)(
                    channel_id = str(channel_id),
                    content    = text,
                    model_used = model_name,
                    message_ids = ','.join(msg_ids),
                    status     = 'sent',
                )
                sent_count += 1
                logger.info(f'[NewsBot] Fallback 推播完成 → {cfg.name}')
            except Exception as e:
                await sync_to_async(DiscordNewsLog.objects.create, thread_sensitive=True)(
                    channel_id = str(channel_id),
                    content    = text,
                    model_used = model_name,
                    status     = 'failed',
                )
                failed_count += 1
                logger.error(f'[NewsBot] Fallback 推播失敗 → {cfg.name}: {e}')

    return {'sent': sent_count, 'failed': failed_count}
