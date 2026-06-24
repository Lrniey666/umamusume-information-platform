"""
Discord Bot Management Command — UMA Info Bot
整合了：
  · 基礎 !channel 頻道設定指令（相容舊版）
  · Guild 生命週期（on_guild_join / on_guild_remove / on_ready 同步）
  · @UMA Info AI 問答（Gemini 3.1 Flash Lite）
  · GuildChannelCache / GuildRoleCache 同步

啟動方式：
    python manage.py run_discord_bot
"""
import os
import asyncio
import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

HELP_TEXT = """**📡 UMA Info Bot 管理指令**

**斜線指令（需伺服器管理員）**
`/read-scope view` — 查看頻道讀取範圍
`/read-scope set` — 設定讀取範圍（全部 / 公告 / 單一頻道 / 進階）
`/read-scope rule-add` / `rule-remove` / `rule-list` — 進階 Allow/Deny 規則
`/news-target view` — 查看推播目標
`/news-target set` — 設定推播頻道、開關、語氣、Ping 身分組
`/news-target clear` — 清除推播頻道

**舊版文字指令（相容）**
`!channel set crawl [名稱]`　將此頻道設為 **爬取頻道**
`!channel set news [名稱]`　 將此頻道設為 **推播頻道**
`!channel list` / `!channel remove`

> 💡 也可至 UMA Info 官網 (`/uma-info/`) 視覺化管理
"""

# 全域 bot 實例（供 API 觸發快取同步使用）
_bot_instance = None


def get_bot_instance():
    return _bot_instance


class Command(BaseCommand):
    help = '啟動 UMA Info Discord Bot（持續運行）'

    def handle(self, *args, **options):
        token = os.getenv('DISCORD_BOT_TOKEN')
        if not token or token == '你的Bot Token':
            self.stderr.write('ERROR: DISCORD_BOT_TOKEN 未設定，請在 .env 中填入真實 Token')
            return

        try:
            import discord
            from discord import app_commands
        except ImportError:
            self.stderr.write('ERROR: discord.py 未安裝，請執行: pip install "discord.py>=2.4.0"')
            return

        class UmaBot(discord.Client):
            def __init__(self_bot, *args, **kwargs):
                intents = discord.Intents.default()
                intents.message_content = True
                intents.guilds           = True
                intents.members          = False
                super().__init__(intents=intents, **kwargs)
                self_bot.tree = app_commands.CommandTree(self_bot)

            # ── on_ready ──────────────────────────────────────
            async def on_ready(self_bot):
                global _bot_instance
                _bot_instance = self_bot
                print(f'[UMAInfo] Bot 上線：{self_bot.user} (ID: {self_bot.user.id})')
                print(f'[UMAInfo] 已加入 {len(self_bot.guilds)} 個伺服器')

                # 啟動排程
                from app_discord_bot.scheduler import start_discord_scheduler
                start_discord_scheduler(self_bot)

                # 同步所有伺服器至 DB（背景執行）
                asyncio.ensure_future(self_bot._sync_all_guilds())

                # 啟動任務輪詢器（crawl/news 任務由持久 Bot 執行）
                asyncio.ensure_future(self_bot._task_poller())

                # 同步斜線指令（/read-scope、/news-target）
                # 使用 guild 級別同步（立即生效），同時保留全域同步作為備援
                try:
                    from app_discord_bot.slash_commands import setup_slash_commands
                    setup_slash_commands(self_bot.tree)
                    total = 0
                    for guild in self_bot.guilds:
                        try:
                            synced = await self_bot.tree.sync(guild=guild)
                            total += len(synced)
                        except Exception as ge:
                            logger.warning(f'[UMAInfo] 伺服器 {guild.id} 斜線指令同步失敗：{ge}')
                    print(f'[UMAInfo] 斜線指令已同步至 {len(self_bot.guilds)} 個伺服器，共 {total} 個指令')
                except Exception as exc:
                    logger.error(f'[UMAInfo] 斜線指令同步失敗：{exc}')

            # ── on_guild_join ──────────────────────────────────
            async def on_guild_join(self_bot, guild):
                print(f'[UMAInfo] 加入新伺服器：{guild.name} ({guild.id})')
                asyncio.ensure_future(self_bot._sync_single_guild(guild))

            # ── on_guild_remove ────────────────────────────────
            async def on_guild_remove(self_bot, guild):
                print(f'[UMAInfo] 離開伺服器：{guild.name} ({guild.id})')
                loop = asyncio.get_event_loop()
                loop.run_in_executor(None, _mark_guild_offline, str(guild.id))

            # ── on_message ─────────────────────────────────────
            async def on_message(self_bot, message):
                if message.author == self_bot.user:
                    return

                # !channel 指令（需要伺服器管理員權限或管理頻道權限）
                if message.content.startswith('!channel'):
                    await handle_channel_command(self_bot, message)
                    return

                # @UMA Info AI 問答（文字或附圖）
                if self_bot.user.mentioned_in(message) and message.guild:
                    content = message.content.replace(f'<@{self_bot.user.id}>', '').strip()
                    content = content.replace(f'<@!{self_bot.user.id}>', '').strip()
                    has_image = any(
                        (a.content_type or '').startswith('image/')
                        for a in message.attachments
                    )
                    if content or has_image:
                        await handle_ai_chat(self_bot, message, content)

            # ── 同步所有已加入的伺服器 ─────────────────────────
            async def _sync_all_guilds(self_bot):
                for guild in self_bot.guilds:
                    try:
                        await self_bot._sync_single_guild(guild)
                    except Exception as e:
                        logger.warning(f'[UMAInfo] 同步伺服器 {guild.id} 失敗：{e}')

            async def _sync_single_guild(self_bot, guild):
                """將伺服器頻道與身分組同步至快取 DB"""
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, _sync_guild_to_db, guild)

            async def sync_guild_cache(self_bot, guild_id: str):
                """供 API 觸發：指定伺服器重新同步快取"""
                guild = self_bot.get_guild(int(guild_id))
                if guild:
                    await self_bot._sync_single_guild(guild)

            # ── 任務輪詢器（crawler-admin 手動任務）──────────────
            async def _task_poller(self_bot):
                """每 2 秒檢查 DB 是否有待執行的 crawl / news 任務。"""
                from asgiref.sync import sync_to_async
                print('[UMAInfo] 任務輪詢器已啟動')
                while not self_bot.is_closed():
                    await asyncio.sleep(2)
                    try:
                        task = await sync_to_async(_claim_pending_task)()
                        if task:
                            await self_bot._execute_task(task)
                    except Exception as exc:
                        logger.error(f'[TaskPoller] 輪詢發生例外：{exc}')

            async def _execute_task(self_bot, run):
                """使用持久 Bot 連線執行 crawl / news 任務。"""
                from asgiref.sync import sync_to_async
                from app_discord_bot.models import DiscordTaskRun

                run_id = run.id
                print(f'[TaskPoller] 開始執行 #{run_id} {run.task_type}')

                def _log(msg: str):
                    obj = DiscordTaskRun.objects.filter(pk=run_id).first()
                    if obj:
                        merged = (obj.log_text or '') + ('\n' if obj.log_text else '') + str(msg).rstrip('\r\n')
                        if len(merged) > 50000:
                            merged = merged[-50000:]
                        obj.log_text = merged
                        obj.save(update_fields=['log_text', 'updated_at'])

                def _update(*, status=None, progress_pct=None, summary=None, ended=False):
                    from django.utils import timezone as _tz
                    obj = DiscordTaskRun.objects.filter(pk=run_id).first()
                    if not obj:
                        return
                    fields = ['updated_at']
                    if status is not None:
                        obj.status = status; fields.append('status')
                    if progress_pct is not None:
                        obj.progress_pct = max(0, min(100, int(progress_pct))); fields.append('progress_pct')
                    if summary is not None:
                        obj.summary = summary; fields.append('summary')
                    if ended:
                        obj.ended_at = _tz.now(); fields.append('ended_at')
                    obj.save(update_fields=fields)

                def _cancel_requested() -> bool:
                    obj = DiscordTaskRun.objects.filter(pk=run_id).values_list('cancel_requested', flat=True).first()
                    return bool(obj)

                alog      = sync_to_async(_log)
                aupdate   = sync_to_async(_update)
                acancel   = sync_to_async(_cancel_requested)

                async def log_fn(msg):      await alog(msg)
                async def progress_fn(p, s): await aupdate(progress_pct=p, summary=s)
                async def cancel_fn():       return await acancel()

                await alog(f'▶ 任務開始：{run.task_type}（持久 Bot）')

                try:
                    if run.task_type == 'crawl':
                        from app_discord_bot.crawler import crawl_all_channels, CrawlCancelledError
                        await aupdate(progress_pct=10, summary='準備爬取')
                        try:
                            count = await crawl_all_channels(
                                self_bot, log_fn=log_fn, progress_fn=progress_fn, cancel_fn=cancel_fn,
                            )
                            if await cancel_fn():
                                await sync_to_async(_finalize_cancelled_db)(run_id, '已被使用者取消')
                            else:
                                await aupdate(status='success', progress_pct=100,
                                              summary=f'爬取完成，共新增 {count} 筆', ended=True)
                                await alog(f'✅ 爬取完成，共新增 {count} 筆訊息')
                        except CrawlCancelledError:
                            await sync_to_async(_finalize_cancelled_db)(run_id, '已被使用者取消')

                    elif run.task_type == 'news':
                        from app_discord_bot.crawler import CrawlCancelledError
                        await aupdate(progress_pct=15, summary='準備推播')
                        try:
                            # 讀取 news_opts 從 result_json（由 _launch_discord_task 寫入）
                            opts = run.result_json or {}
                            push_mode = opts.get('news_mode', 'weekly')
                            if push_mode == 'article':
                                from app_crawler_admin.discord_push import push_article
                                result = await push_article(
                                    self_bot, opts['article_id'],
                                    guild_ids=opts.get('guild_ids'),
                                )
                            else:
                                from app_discord_bot.scheduler import _run_per_guild_news
                                from datetime import datetime as _dt
                                import pytz
                                now_hour = _dt.now(pytz.timezone('Asia/Taipei')).hour
                                result = await _run_per_guild_news(self_bot, current_hour=now_hour, force_send=True)
                            sent   = int(result.get('sent', 0))
                            failed = int(result.get('failed', 0))
                            if result.get('error') and not sent:
                                raise RuntimeError(result['error'])
                            await aupdate(status='success', progress_pct=100,
                                          summary=f'推播完成（成功 {sent}、失敗 {failed}）', ended=True)
                            await alog(f'✅ 推播完成：成功 {sent}、失敗 {failed}')
                        except CrawlCancelledError:
                            await sync_to_async(_finalize_cancelled_db)(run_id, '已被使用者取消')

                except Exception as exc:
                    logger.error(f'[TaskPoller] 任務 #{run_id} 失敗：{exc}')
                    await sync_to_async(_fail_task_db)(run_id, str(exc))
                    await alog(f'❌ 任務失敗：{exc}')
                finally:
                    print(f'[TaskPoller] 任務 #{run_id} 結束')

        # ── Guild DB 操作（在執行緒中執行，避免阻塞事件迴圈）──────

        def _sync_guild_to_db(guild):
            """同步 guild 資料至 DiscordGuild + GuildSetting + Cache"""
            try:
                from django.utils import timezone
                from app_uma_info_portal.models import (
                    DiscordGuild, GuildSetting,
                    GuildChannelCache, GuildRoleCache,
                )

                # guild.icon 在 discord.py 2.x 為 Asset 物件
                # 使用 .key 取得純 hash（如 "a_abc123" 或 "abc123"）
                # 避免用 str(guild.icon) 它會回傳完整 CDN URL 導致 icon_url 組出破損網址
                icon_hash = guild.icon.key if guild.icon else ''

                dg, _ = DiscordGuild.objects.update_or_create(
                    guild_id=str(guild.id),
                    defaults={
                        'name':           guild.name,
                        'icon_hash':      icon_hash,
                        'is_bot_present': True,
                        'joined_at':      guild.me.joined_at if guild.me else timezone.now(),
                        'member_count':   guild.member_count or 0,
                    }
                )
                GuildSetting.objects.get_or_create(guild=dg)

                # 頻道快取（文字/公告/論壇/語音），同時記錄 Bot 在該頻道的實際權限
                import discord
                type_map = {
                    discord.ChannelType.text:  'text',
                    discord.ChannelType.news:  'news',
                    discord.ChannelType.forum: 'forum',
                    discord.ChannelType.voice: 'voice',
                }
                bot_member = guild.me
                GuildChannelCache.objects.filter(guild=dg).delete()
                for ch in guild.channels:
                    ch_type = type_map.get(ch.type, 'other')
                    # 計算 Bot 對此頻道的實際權限
                    bot_can_read = False
                    bot_can_send = False
                    if bot_member:
                        try:
                            perms = ch.permissions_for(bot_member)
                            bot_can_read = bool(perms.view_channel and perms.read_message_history)
                            bot_can_send = bool(perms.view_channel and perms.send_messages and perms.embed_links)
                        except Exception:
                            bot_can_read = True
                            bot_can_send = True
                    GuildChannelCache.objects.update_or_create(
                        guild=dg, channel_id=str(ch.id),
                        defaults={
                            'channel_name': ch.name,
                            'channel_type': ch_type,
                            'position':     getattr(ch, 'position', 0),
                            'bot_can_read': bot_can_read,
                            'bot_can_send': bot_can_send,
                        }
                    )

                # 身分組快取（排除 @everyone）
                GuildRoleCache.objects.filter(guild=dg).delete()
                for role in guild.roles:
                    if role.is_default():
                        continue
                    GuildRoleCache.objects.update_or_create(
                        guild=dg, role_id=str(role.id),
                        defaults={
                            'role_name':  role.name,
                            'role_color': str(role.color) if str(role.color) != '#000000' else '',
                            'position':   role.position,
                        }
                    )

                logger.info(f'[UMAInfo] 已同步伺服器快取：{guild.name} ({guild.id})')
            except Exception as e:
                logger.error(f'[UMAInfo] _sync_guild_to_db 失敗 ({guild.id})：{e}')

        def _mark_guild_offline(guild_id: str):
            try:
                from app_uma_info_portal.models import DiscordGuild
                DiscordGuild.objects.filter(guild_id=guild_id).update(is_bot_present=False)
            except Exception as e:
                logger.error(f'[UMAInfo] _mark_guild_offline 失敗 ({guild_id})：{e}')

        # ── 頻道指令處理 ────────────────────────────────────────

        async def handle_channel_command(bot, message):
            """處理 !channel 系列指令（相容舊版 DiscordBotConfig）"""
            from app_discord_bot.models import DiscordBotConfig
            loop = asyncio.get_event_loop()

            parts = message.content.strip().split(None, 3)
            sub = parts[1].lower() if len(parts) > 1 else 'help'

            if sub == 'help':
                await message.channel.send(HELP_TEXT)
                return

            if sub == 'list':
                def _list():
                    return list(DiscordBotConfig.objects.all().order_by('channel_type', 'name'))
                configs = await loop.run_in_executor(None, _list)
                if not configs:
                    await message.channel.send('⚠️ 目前沒有任何頻道設定。')
                    return
                lines = ['**📋 目前頻道設定：**']
                for cfg in configs:
                    status = '✅' if cfg.is_active else '⏸️'
                    type_label = '爬取' if cfg.channel_type == 'crawl' else '推播'
                    lines.append(f'{status} `{cfg.channel_id}` — **{cfg.name}** [{type_label}]')
                await message.channel.send('\n'.join(lines))
                return

            if sub == 'set':
                if len(parts) < 3 or parts[2].lower() not in ('crawl', 'news'):
                    await message.channel.send('❌ 用法：`!channel set crawl [名稱]` 或 `!channel set news [名稱]`')
                    return
                channel_type = parts[2].lower()
                name = parts[3].strip() if len(parts) > 3 else message.channel.name
                channel_id = str(message.channel.id)

                def _set():
                    return DiscordBotConfig.objects.update_or_create(
                        channel_id=channel_id,
                        defaults={
                            'name': name,
                            'channel_type': channel_type,
                            'is_active': True,
                            'note': f'由 {message.author} 於 Discord 設定',
                        }
                    )
                _, created = await loop.run_in_executor(None, _set)
                type_label = '爬取頻道' if channel_type == 'crawl' else '推播頻道'
                action = '新增' if created else '更新'
                await message.channel.send(
                    f'✅ 已{action}設定：此頻道（`{channel_id}`）為 **{type_label}**，名稱：**{name}**\n'
                    f'💡 建議改用 UMA Info 官網進行視覺化管理：`/uma-info/`'
                )
                return

            if sub == 'remove':
                channel_id = str(message.channel.id)
                def _del():
                    return DiscordBotConfig.objects.filter(channel_id=channel_id).delete()
                deleted, _ = await loop.run_in_executor(None, _del)
                if deleted:
                    await message.channel.send(f'🗑️ 已移除此頻道（`{channel_id}`）的所有設定。')
                else:
                    await message.channel.send(f'⚠️ 此頻道（`{channel_id}`）沒有設定紀錄。')
                return

            await message.channel.send(f'❓ 未知指令 `{sub}`，輸入 `!channel help` 查看說明。')

        # ── AI 問答處理 ────────────────────────────────────────

        async def handle_ai_chat(bot, message, question: str):
            """@UMA Info 觸發的 AI 問答（支援圖片附件）"""
            from app_discord_bot.ai_chat import (
                DEFAULT_IMAGE_PROMPT,
                collect_message_images,
                generate_ai_answer,
                split_text,
            )

            guild_id = str(message.guild.id) if message.guild else None
            loop = asyncio.get_event_loop()

            def _check_ai_enabled():
                try:
                    from app_uma_info_portal.models import DiscordGuild, GuildSetting
                    guild = DiscordGuild.objects.filter(guild_id=guild_id).first()
                    if not guild:
                        return True
                    setting = GuildSetting.objects.filter(guild=guild).first()
                    return setting.ai_chat_enabled if setting else True
                except Exception:
                    return True

            enabled = await loop.run_in_executor(None, _check_ai_enabled)
            if not enabled:
                await message.reply('⚠️ 此伺服器已停用 AI 問答功能。管理員可至官網重新啟用。')
                return

            images = await collect_message_images(message)
            prompt = question.strip() if question.strip() else DEFAULT_IMAGE_PROMPT

            async with message.channel.typing():
                answer = await loop.run_in_executor(
                    None, generate_ai_answer, prompt, guild_id, images,
                )

            if not answer:
                await message.reply('😅 AI 回答失敗，請稍後再試。')
                return

            chunks = split_text(answer, 1900)
            await message.reply(chunks[0])
            for chunk in chunks[1:]:
                await message.channel.send(chunk)

        def _split_text(text: str, max_len: int) -> list:
            """向後相容：委派至 app_discord_bot.ai_chat.split_text"""
            from app_discord_bot.ai_chat import split_text
            return split_text(text, max_len)

        # ── DB 任務輔助函式（同步，供 sync_to_async 包裝）────────

        def _claim_pending_task():
            """原子地取得並標記一筆 pending bot 任務為 running。"""
            from app_discord_bot.models import DiscordTaskRun
            from django.utils import timezone as _tz
            from django.db import transaction
            with transaction.atomic():
                task = DiscordTaskRun.objects.filter(
                    status='pending', runner='bot',
                    task_type__in=['crawl', 'news'],
                ).order_by('created_at').first()
                if task:
                    task.status = 'running'
                    task.started_at = _tz.now()
                    task.summary = '持久 Bot 執行中'
                    task.save(update_fields=['status', 'started_at', 'summary', 'updated_at'])
            return task

        def _finalize_cancelled_db(run_id: int, summary: str = '已被使用者取消'):
            from app_discord_bot.models import DiscordTaskRun
            from django.utils import timezone as _tz
            DiscordTaskRun.objects.filter(pk=run_id).update(
                status='cancelled', summary=summary, ended_at=_tz.now(),
            )

        def _fail_task_db(run_id: int, error: str):
            from app_discord_bot.models import DiscordTaskRun
            from django.utils import timezone as _tz
            DiscordTaskRun.objects.filter(pk=run_id).update(
                status='failed', summary='任務失敗',
                error_message=error[:500], ended_at=_tz.now(),
            )

        # Bot 自行管理 PID 檔，不依賴 bot_manager.start_bot() 才寫入
        from pathlib import Path
        _pid_file = Path(__file__).resolve().parents[3] / 'discord_bot.pid'

        def _write_pid():
            try:
                _pid_file.write_text(str(os.getpid()), encoding='utf-8')
                print(f'[UMAInfo] PID 檔已寫入：{_pid_file} (pid={os.getpid()})')
            except Exception as e:
                logger.warning(f'[UMAInfo] 無法寫入 PID 檔：{e}')

        def _remove_pid():
            try:
                if _pid_file.exists():
                    stored = _pid_file.read_text(encoding='utf-8').strip()
                    if stored == str(os.getpid()):
                        _pid_file.unlink()
                        print(f'[UMAInfo] PID 檔已清除：{_pid_file}')
            except Exception:
                pass

        _write_pid()
        bot = UmaBot()
        self.stdout.write('[UMAInfo] Discord Bot 啟動中...')
        try:
            bot.run(token)
        finally:
            _remove_pid()
