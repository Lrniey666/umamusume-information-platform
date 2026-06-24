"""
D3: Discord 頻道歷史爬取（並行 + 增量 + Rate Limit 處理）

支援 GuildSetting.read_scope 四種模式：
  all           — 爬取 Bot 所在伺服器的所有可讀文字頻道
  announcements — 僅爬取公告頻道（ChannelType.news）
  single        — 僅爬取 GuildSetting.single_channel_id 指定頻道
  advanced      — 依 GuildChannelRule allow/deny 清單

並行設計：
  · crawl_guild 內以 asyncio.Semaphore 限制同時進行中的頻道數（預設 3）
  · 取消旗標透過共享 asyncio.Event 傳遞，保證並行時也能快速停止
  · crawl_limit / concurrency 優先從 DiscordCrawlSettings（DB）讀取，
    DB 不存在時 fallback 到 DISCORD_CRAWL_LIMIT 環境變數（預設 1000）

log_fn / progress_fn 為可選的 async callback：
  log_fn(msg: str)                   — 寫入一行日誌
  progress_fn(pct: int, summary: str) — 更新百分比與摘要
"""
import asyncio
import os
import logging
from typing import Callable, Awaitable, Optional

from asgiref.sync import sync_to_async

from .models import DiscordMessage, DiscordBotConfig

logger = logging.getLogger(__name__)

# 環境變數 fallback（當 DB 設定不存在時使用）
_ENV_CRAWL_LIMIT = int(os.getenv('DISCORD_CRAWL_LIMIT', '1000'))
_ENV_CONCURRENCY = 3

# async callback 型別別名
LogFn      = Optional[Callable[[str], Awaitable[None]]]
ProgressFn = Optional[Callable[[int, str], Awaitable[None]]]
CancelFn   = Optional[Callable[[], Awaitable[bool]]]


class CrawlCancelledError(Exception):
    """由使用者透過控制台請求取消爬取任務時拋出。"""


# ── 同步 ORM 輔助函式（由 sync_to_async 呼叫）──────────────────────────

def _get_last_msg_timestamp(channel_id: str):
    return (
        DiscordMessage.objects
        .filter(channel_id=channel_id)
        .order_by('-timestamp')
        .values_list('timestamp', flat=True)
        .first()
    )


def _bulk_create_messages(batch: list) -> int:
    if batch:
        DiscordMessage.objects.bulk_create(batch, ignore_conflicts=True)
    return len(batch)


def _get_guild_scope(guild_id: str):
    try:
        from app_uma_info_portal.models import DiscordGuild, GuildSetting, GuildChannelRule
        dg = DiscordGuild.objects.filter(guild_id=guild_id).first()
        if not dg:
            return 'all', None, set(), set()
        setting = GuildSetting.objects.filter(guild=dg).first()
        scope     = getattr(setting, 'read_scope', 'all') if setting else 'all'
        single_id = getattr(setting, 'single_channel_id', '') if setting else ''
        allow_ids: set = set()
        deny_ids:  set = set()
        if scope == 'advanced':
            allow_ids = set(
                GuildChannelRule.objects.filter(guild=dg, rule_type='allow')
                .values_list('channel_id', flat=True)
            )
            deny_ids = set(
                GuildChannelRule.objects.filter(guild=dg, rule_type='deny')
                .values_list('channel_id', flat=True)
            )
        return scope, single_id, allow_ids, deny_ids
    except Exception as e:
        logger.error(f'[Crawler] 載入伺服器設定失敗 ({guild_id}): {e}')
        return 'all', None, set(), set()


def _get_crawl_settings() -> tuple[int, int]:
    """從 DB 讀取爬取設定，fallback 到環境變數。回傳 (crawl_limit, concurrency)"""
    try:
        from .models import DiscordCrawlSettings
        s = DiscordCrawlSettings.objects.filter(pk=1).first()
        if s:
            limit = s.crawl_limit if s.crawl_limit > 0 else None  # 0 = 不限
            conc  = max(1, min(10, s.concurrency))
            return limit, conc
    except Exception as e:
        logger.warning(f'[Crawler] 讀取 DiscordCrawlSettings 失敗，使用預設值: {e}')
    return _ENV_CRAWL_LIMIT, _ENV_CONCURRENCY


def _get_fallback_channel_ids() -> list:
    configs = DiscordBotConfig.objects.filter(channel_type='crawl', is_active=True)
    ids = [int(c.channel_id) for c in configs if c.channel_id.isdigit()]
    if not ids:
        ids_raw = os.getenv('DISCORD_CRAWL_CHANNEL_IDS', '')
        ids = [int(x.strip()) for x in ids_raw.split(',') if x.strip().isdigit()]
    return ids


# ── 非同步爬取函式 ──────────────────────────────────────────────────────

async def crawl_channel(
    bot,
    channel_id: int,
    guild_id: str = '',
    log_fn: LogFn = None,
    crawl_limit: int | None = None,
) -> int:
    """
    爬取單一頻道歷史訊息（增量）。
    返回本次新增筆數。
    crawl_limit=None 代表不設上限。
    """
    try:
        import discord
        channel = bot.get_channel(channel_id)
        if not channel:
            msg = f'    ⚠ 頻道 {channel_id}：Bot 無法存取（缺少讀取權限或頻道不存在）'
            if log_fn:
                await log_fn(msg)
            return 0

        after_dt = await sync_to_async(_get_last_msg_timestamp)(str(channel_id))

        batch = []
        async for msg in channel.history(limit=crawl_limit, after=after_dt, oldest_first=True):
            if msg.author.bot or not msg.content.strip():
                continue
            batch.append(DiscordMessage(
                msg_id       = str(msg.id),
                channel_id   = str(channel_id),
                channel_name = channel.name,
                author       = str(msg.author),
                content      = msg.content,
                timestamp    = msg.created_at,
                is_umamusume = None,
                guild_id     = guild_id,
            ))

        new_count = await sync_to_async(_bulk_create_messages)(batch)
        status = f'+{new_count} 筆' if new_count else '無新訊息'
        if log_fn:
            await log_fn(f'    ✓ #{channel.name}：{status}')
        return new_count

    except Exception as e:
        err_str = str(e)
        if '50001' in err_str or '403' in err_str:
            if log_fn:
                await log_fn(f'    ✗ 頻道 {channel_id}：無讀取權限，略過')
        else:
            logger.error(f'[Crawler] 頻道 {channel_id} 爬取失敗: {e}')
            if log_fn:
                await log_fn(f'    ✗ 頻道 {channel_id}：{err_str[:80]}')
        return 0


async def crawl_guild(
    bot,
    guild,
    log_fn:      LogFn      = None,
    progress_fn: ProgressFn = None,
    cancel_fn:   CancelFn   = None,
    guild_index: int        = 0,
    guild_total: int        = 1,
) -> int:
    """依 GuildSetting.read_scope 並行爬取單一伺服器，逐頻道回報進度。"""
    import discord
    guild_id = str(guild.id)

    scope, single_id, allow_ids, deny_ids = await sync_to_async(_get_guild_scope)(guild_id)
    crawl_limit, concurrency = await sync_to_async(_get_crawl_settings)()

    target_channels = []
    if scope == 'all':
        target_channels = [
            ch for ch in guild.channels
            if ch.type in (discord.ChannelType.text, discord.ChannelType.news)
        ]
    elif scope == 'announcements':
        target_channels = [
            ch for ch in guild.channels
            if ch.type == discord.ChannelType.news
        ]
    elif scope == 'single':
        if single_id and single_id.isdigit():
            ch = guild.get_channel(int(single_id))
            if ch:
                target_channels = [ch]
    elif scope == 'advanced':
        for ch in guild.channels:
            if ch.type in (discord.ChannelType.text, discord.ChannelType.news):
                cid = str(ch.id)
                if allow_ids:
                    if cid in allow_ids and cid not in deny_ids:
                        target_channels.append(ch)
                else:
                    if cid not in deny_ids:
                        target_channels.append(ch)

    scope_label = {'all': '全部頻道', 'announcements': '公告頻道', 'single': '指定頻道', 'advanced': '進階規則'}.get(scope, scope)
    limit_label = str(crawl_limit) if crawl_limit else '不限'
    if log_fn:
        await log_fn(
            f'▶ [{guild_index + 1}/{guild_total}] {guild.name}  ·  '
            f'讀取範圍：{scope_label}  ·  目標頻道：{len(target_channels)} 個  ·  '
            f'每頻道上限：{limit_label}  ·  並行數：{concurrency}'
        )

    ch_total = len(target_channels)
    if not ch_total:
        return 0

    # 並行爬取：Semaphore 限制同時進行中的頻道數
    semaphore    = asyncio.Semaphore(concurrency)
    cancel_event = asyncio.Event()
    completed    = [0]                     # 已完成頻道數（在 lock 內修改）
    total_new    = [0]                     # 累積新增訊息數
    lock         = asyncio.Lock()

    async def _crawl_one(ch):
        # 尚未取得 semaphore 前先檢查取消
        if cancel_event.is_set():
            return 0
        async with semaphore:
            if cancel_event.is_set():
                return 0
            # 使用者取消旗標
            if cancel_fn and await cancel_fn():
                cancel_event.set()
                return 0
            count = await crawl_channel(
                bot, ch.id, guild_id=guild_id,
                log_fn=log_fn, crawl_limit=crawl_limit,
            )
            async with lock:
                completed[0] += 1
                total_new[0] += count
                done = completed[0]
                accum = total_new[0]
            # 進度回報
            if progress_fn and guild_total > 0 and ch_total > 0:
                per_guild_span = 70 / guild_total
                guild_base = 15 + guild_index * per_guild_span
                pct = int(guild_base + (done / ch_total) * per_guild_span)
                pct = min(pct, 85)
                await progress_fn(
                    pct,
                    f'[{guild_index + 1}/{guild_total}] {guild.name} '
                    f'— 頻道 {done}/{ch_total}，累計 +{accum} 筆',
                )
            return count

    tasks = [_crawl_one(ch) for ch in target_channels]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 若取消事件被觸發，向上拋出
    if cancel_event.is_set():
        done_so_far = completed[0]
        if log_fn:
            await log_fn(f'  ⛔ 偵測到取消請求，已完成 {done_so_far}/{ch_total} 個頻道')
        raise CrawlCancelledError('使用者取消')

    guild_new = sum(r for r in results if isinstance(r, int))
    if log_fn:
        await log_fn(f'  ↳ {guild.name} 完成，本次新增 {guild_new} 筆訊息')
    return guild_new


async def crawl_all_channels(
    bot,
    log_fn:      LogFn      = None,
    progress_fn: ProgressFn = None,
    cancel_fn:   CancelFn   = None,
) -> int:
    """
    全面爬取：
    1. 優先依 GuildSetting.read_scope 逐伺服器爬取（每個伺服器內部並行）
    2. Fallback：DiscordBotConfig（舊版相容）
    """
    total = 0

    if bot.guilds:
        guild_total = len(bot.guilds)
        if log_fn:
            await log_fn(f'Bot 已連線 · 加入 {guild_total} 個伺服器')
        if progress_fn:
            await progress_fn(18, f'準備爬取 {guild_total} 個伺服器')

        for idx, guild in enumerate(bot.guilds):
            # 伺服器層取消檢查
            if cancel_fn and await cancel_fn():
                if log_fn:
                    await log_fn(f'⛔ 偵測到取消請求，已在第 {idx + 1}/{guild_total} 個伺服器前停止（已新增 {total} 筆）')
                raise CrawlCancelledError('使用者取消')
            try:
                count = await crawl_guild(
                    bot, guild,
                    log_fn=log_fn, progress_fn=progress_fn, cancel_fn=cancel_fn,
                    guild_index=idx, guild_total=guild_total,
                )
                total += count
            except CrawlCancelledError:
                raise
            except Exception as e:
                logger.error(f'[Crawler] 伺服器 {guild.id} 爬取失敗: {e}')
                if log_fn:
                    await log_fn(f'  ❌ 伺服器 {guild.name} 爬取失敗：{e}')

        if log_fn:
            await log_fn(f'✅ 所有伺服器爬取完成，共新增 {total} 筆訊息')
        logger.info(f'[Crawler] 完成（Guild 模式），共新增 {total} 筆')
        return total

    # Fallback：舊版 DiscordBotConfig
    crawl_limit, _ = await sync_to_async(_get_crawl_settings)()
    channel_ids = await sync_to_async(_get_fallback_channel_ids)()
    if log_fn:
        await log_fn(f'Fallback 模式：共 {len(channel_ids)} 個頻道')
    for cid in channel_ids:
        count = await crawl_channel(bot, cid, log_fn=log_fn, crawl_limit=crawl_limit)
        total += count
        if progress_fn:
            await progress_fn(50, f'Fallback 爬取中，目前累計 {total} 筆')
        await asyncio.sleep(0.5)

    if log_fn:
        await log_fn(f'✅ Fallback 爬取完成，共新增 {total} 筆')
    logger.info(f'[Crawler] 完成（Fallback 模式），共新增 {total} 筆')
    return total
