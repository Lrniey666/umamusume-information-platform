"""
AI 新聞 → Discord 推播服務（crawler-admin / ai-news 頁使用）

支援兩種模式：
  weekly  — 呼叫 news_generator.generate_news() 產生週報摘要後推播
  article — 將指定 GeneratedNewsArticle 內容推播至各伺服器推播頻道
"""
import logging
import os
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


def get_discord_push_status() -> dict:
    """彙整 Bot 狀態、推播目標伺服器、近期推播紀錄、進行中推播任務"""
    from app_discord_bot.bot_manager import get_bot_status
    from app_discord_bot.models import DiscordNewsLog, DiscordTaskRun
    from app_uma_info_portal.models import DiscordGuild, GuildSetting

    bot = get_bot_status()
    targets = []
    try:
        qs = (
            GuildSetting.objects
            .filter(news_enabled=True, guild__is_bot_present=True)
            .select_related('guild')
            .order_by('guild__name')
        )
        for s in qs:
            if not s.news_channel_id:
                continue
            targets.append({
                'guild_id': s.guild.guild_id,
                'guild_name': s.guild.name,
                'channel_id': s.news_channel_id,
                'news_hour': s.news_hour,
                'news_tone': s.news_tone or 'lively',
            })
    except Exception as e:
        logger.warning('載入推播目標失敗: %s', e)

    guild_names = dict(DiscordGuild.objects.values_list('guild_id', 'name'))
    logs = []
    for log in DiscordNewsLog.objects.order_by('-created_at')[:12]:
        logs.append({
            'id': log.id,
            'guild_id': log.guild_id,
            'guild_name': guild_names.get(log.guild_id, log.guild_id or '—'),
            'channel_id': log.channel_id,
            'status': log.status,
            'model_used': log.model_used,
            'created_at': log.created_at.strftime('%Y-%m-%d %H:%M'),
            'preview': (log.content or '')[:80],
        })

    active_task = DiscordTaskRun.objects.filter(
        task_type='news', status__in=['pending', 'running']
    ).first()

    return {
        'bot': bot,
        'targets': targets,
        'target_count': len(targets),
        'recent_logs': logs,
        'active_news_task': {
            'id': active_task.id,
            'status': active_task.status,
            'summary': active_task.summary,
            'progress_pct': active_task.progress_pct,
        } if active_task else None,
        'news_model': os.getenv('DISCORD_NEWS_MODEL', 'gemini'),
    }


def format_article_for_discord(article) -> str:
    """將 GeneratedNewsArticle 格式化為 Discord 訊息文字"""
    lines = [f'**{article.title}**']
    if article.subtitle:
        lines.append(f'_{article.subtitle}_')
    if article.summary:
        lines.append('')
        lines.append(article.summary)
    lines.append('')
    lines.append(article.content or '')
    links = article.source_links or []
    if links:
        lines.append('')
        lines.append('**參考來源**')
        for ref in links[:5]:
            title = (ref.get('title') or '連結')[:60]
            link = ref.get('link') or ''
            if link:
                lines.append(f'• [{title}]({link})')
            else:
                lines.append(f'• {title}')
    return '\n'.join(lines)


async def push_text_to_guilds(
    bot,
    text: str,
    *,
    model_used: str = 'manual',
    guild_ids: list[str] | None = None,
    article_id: int | None = None,
) -> dict:
    """
    將文字推播至 GuildSetting 已啟用的推播頻道。
    guild_ids 為 None 時推播至所有目標；否則僅限指定伺服器。
    """
    from app_discord_bot.models import DiscordNewsLog
    from app_discord_bot.news_generator import split_for_discord
    from app_uma_info_portal.models import GuildSetting

    if not text or not text.strip():
        return {'sent': 0, 'failed': 0, 'error': '推播內容為空'}

    parts = split_for_discord(text.strip())
    sent = failed = 0
    details = []

    def _load_settings():
        qs = GuildSetting.objects.filter(
            news_enabled=True,
            guild__is_bot_present=True,
        ).exclude(news_channel_id='').select_related('guild')
        if guild_ids:
            qs = qs.filter(guild__guild_id__in=guild_ids)
        return list(qs)

    settings = await sync_to_async(_load_settings, thread_sensitive=True)()
    if not settings:
        return {'sent': 0, 'failed': 0, 'error': '沒有可推播的伺服器（請確認 Portal 已設定推播頻道）'}

    for setting in settings:
        guild_name = setting.guild.name
        raw_channel_id = (setting.news_channel_id or '').strip()
        if not raw_channel_id.isdigit():
            failed += 1
            await sync_to_async(DiscordNewsLog.objects.create, thread_sensitive=True)(
                channel_id=raw_channel_id,
                guild_id=setting.guild.guild_id,
                content=text[:2000],
                model_used=model_used,
                status='failed',
            )
            details.append({'guild': guild_name, 'status': 'failed', 'reason': f'無效頻道 ID: {raw_channel_id}'})
            logger.warning('[DiscordPush] 無效頻道 ID %s（%s）', raw_channel_id, guild_name)
            continue

        channel_id = int(raw_channel_id)
        channel = bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await bot.fetch_channel(channel_id)
            except Exception as fe:
                failed += 1
                await sync_to_async(DiscordNewsLog.objects.create, thread_sensitive=True)(
                    channel_id=str(channel_id),
                    guild_id=setting.guild.guild_id,
                    content=text[:2000],
                    model_used=model_used,
                    status='failed',
                )
                details.append({'guild': guild_name, 'status': 'failed', 'reason': f'找不到頻道：{fe}'})
                logger.warning('[DiscordPush] 找不到頻道 %s（%s）：%s', channel_id, guild_name, fe)
                continue
        if not hasattr(channel, 'send'):
            failed += 1
            await sync_to_async(DiscordNewsLog.objects.create, thread_sensitive=True)(
                channel_id=str(channel_id),
                guild_id=setting.guild.guild_id,
                content=text[:2000],
                model_used=model_used,
                status='failed',
            )
            details.append({'guild': guild_name, 'status': 'failed', 'reason': '此頻道類型不支援直接發送訊息'})
            logger.warning('[DiscordPush] 頻道 %s（%s）不支援 send()', channel_id, guild_name)
            continue

        ping_prefix = f'<@&{setting.ping_role_id}> ' if setting.ping_role_id else ''
        msg_ids = []
        try:
            for i, part in enumerate(parts):
                content = (ping_prefix + part) if i == 0 else part
                sent_msg = await channel.send(content)
                msg_ids.append(str(sent_msg.id))
            await sync_to_async(DiscordNewsLog.objects.create, thread_sensitive=True)(
                channel_id=str(channel_id),
                guild_id=setting.guild.guild_id,
                content=text[:4000],
                model_used=model_used,
                message_ids=','.join(msg_ids),
                pinged_role_id=setting.ping_role_id or '',
                status='sent',
            )
            sent += 1
            details.append({'guild': guild_name, 'status': 'sent', 'messages': len(msg_ids)})
            logger.info('[DiscordPush] 推播完成 → %s', guild_name)
        except Exception as e:
            failed += 1
            await sync_to_async(DiscordNewsLog.objects.create, thread_sensitive=True)(
                channel_id=str(channel_id),
                guild_id=setting.guild.guild_id,
                content=text[:2000],
                model_used=model_used,
                status='failed',
            )
            details.append({'guild': guild_name, 'status': 'failed', 'reason': str(e)[:120]})
            logger.error('[DiscordPush] 推播失敗 → %s: %s', guild_name, e)

    result = {'sent': sent, 'failed': failed, 'details': details}
    if article_id:
        result['article_id'] = article_id
    return result


async def push_weekly_summary(bot, *, model: str | None = None) -> dict:
    """產生週報摘要並推播（與 scheduler 手動推播相同內容來源）"""
    from app_discord_bot.news_generator import generate_news

    model_env = model or os.getenv('DISCORD_NEWS_MODEL', 'gemini')
    text = generate_news(model=model_env)
    model_name = 'claude-sonnet-4-6' if model_env == 'claude' else 'gemini-3.5-flash'
    return await push_text_to_guilds(bot, text, model_used=model_name)


async def push_article(bot, article_id: int, guild_ids: list[str] | None = None) -> dict:
    """推播指定 GeneratedNewsArticle"""
    from app_user_keyword_llm_report.models import GeneratedNewsArticle

    article = await sync_to_async(
        lambda: GeneratedNewsArticle.objects.filter(pk=article_id).first(),
        thread_sensitive=True,
    )()
    if not article:
        return {'sent': 0, 'failed': 0, 'error': f'找不到新聞 #{article_id}'}
    text = format_article_for_discord(article)
    model_used = f'ai-article#{article_id}'
    return await push_text_to_guilds(
        bot, text, model_used=model_used, guild_ids=guild_ids, article_id=article_id,
    )
