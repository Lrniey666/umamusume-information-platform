"""
UMA Info Bot Discord 斜線指令（/read-scope、/news-target）
需伺服器管理員權限。
"""
from __future__ import annotations

import logging

import discord
from discord import app_commands

logger = logging.getLogger(__name__)

SCOPE_CHOICES = [
    app_commands.Choice(name='全部頻道（預設）', value='all'),
    app_commands.Choice(name='僅公告頻道', value='announcements'),
    app_commands.Choice(name='僅單一頻道', value='single'),
    app_commands.Choice(name='進階 Allow/Deny', value='advanced'),
]

TONE_CHOICES = [
    app_commands.Choice(name='活潑（適合社群）', value='lively'),
    app_commands.Choice(name='簡潔（資訊為主）', value='concise'),
]

RULE_TYPE_CHOICES = [
    app_commands.Choice(name='允許（allow）', value='allow'),
    app_commands.Choice(name='排除（deny）', value='deny'),
]


async def _require_admin(interaction: discord.Interaction) -> bool:
    if interaction.guild is None:
        await interaction.response.send_message('❌ 此指令僅能在伺服器內使用。', ephemeral=True)
        return False
    perms = interaction.user.guild_permissions
    if not perms.administrator:
        await interaction.response.send_message(
            '❌ 需要**伺服器管理員**權限才能使用此指令。',
            ephemeral=True,
        )
        return False
    return True


def _bot_can_send(channel: discord.abc.GuildChannel, bot_member: discord.Member | None) -> bool:
    if bot_member is None:
        return True
    try:
        perms = channel.permissions_for(bot_member)
        return bool(perms.view_channel and perms.send_messages and perms.embed_links)
    except Exception:
        return False


def setup_slash_commands(tree: app_commands.CommandTree) -> None:
    """註冊所有斜線指令至 CommandTree。"""

    read_scope = app_commands.Group(
        name='read-scope',
        description='設定 Bot 爬取訊息的頻道讀取範圍（需伺服器管理員）',
        default_permissions=discord.Permissions(administrator=True),
    )

    news_target = app_commands.Group(
        name='news-target',
        description='設定情報推播目標頻道與語氣（需伺服器管理員）',
        default_permissions=discord.Permissions(administrator=True),
    )

    @read_scope.command(name='view', description='查看目前頻道讀取範圍設定')
    async def read_scope_view(interaction: discord.Interaction):
        if not await _require_admin(interaction):
            return
        from asgiref.sync import sync_to_async
        from app_uma_info_portal.guild_settings_service import (
            format_read_scope_summary,
            get_or_create_guild_setting,
        )

        def _fetch():
            _, setting = get_or_create_guild_setting(
                str(interaction.guild.id), guild_name=interaction.guild.name,
            )
            return format_read_scope_summary(setting)

        text = await sync_to_async(_fetch)()
        await interaction.response.send_message(
            f'📡 **頻道讀取範圍** — {interaction.guild.name}\n{text}\n\n'
            f'💡 也可至官網管理：`/uma-info/servers/{interaction.guild.id}/manage/`',
            ephemeral=True,
        )

    @read_scope.command(name='set', description='設定讀取範圍模式')
    @app_commands.describe(
        scope='讀取範圍',
        channel='當 scope=僅單一頻道時必填',
    )
    @app_commands.choices(scope=SCOPE_CHOICES)
    async def read_scope_set(
        interaction: discord.Interaction,
        scope: app_commands.Choice[str],
        channel: discord.TextChannel | None = None,
    ):
        if not await _require_admin(interaction):
            return

        scope_val = scope.value
        if scope_val == 'single' and channel is None:
            await interaction.response.send_message(
                '❌ 選擇「僅單一頻道」時必須指定 `channel` 參數。',
                ephemeral=True,
            )
            return

        payload = {'read_scope': scope_val}
        if scope_val == 'single':
            payload['single_channel_id'] = str(channel.id)
        elif scope_val != 'single':
            payload['single_channel_id'] = ''

        from asgiref.sync import sync_to_async
        from app_uma_info_portal.guild_settings_service import (
            format_read_scope_summary,
            update_guild_setting_fields,
        )

        def _apply():
            result = update_guild_setting_fields(
                str(interaction.guild.id),
                payload,
                str(interaction.user.id),
                guild_name=interaction.guild.name,
                send_news_confirm=False,
            )
            return format_read_scope_summary(result['setting'])

        summary = await sync_to_async(_apply)()
        await interaction.response.send_message(
            f'✅ 已更新頻道讀取範圍。\n{summary}',
            ephemeral=True,
        )

    @read_scope.command(name='rule-add', description='新增進階 Allow/Deny 頻道規則')
    @app_commands.describe(
        rule_type='允許或排除',
        channel='目標頻道',
    )
    @app_commands.choices(rule_type=RULE_TYPE_CHOICES)
    async def read_scope_rule_add(
        interaction: discord.Interaction,
        rule_type: app_commands.Choice[str],
        channel: discord.TextChannel,
    ):
        if not await _require_admin(interaction):
            return

        from asgiref.sync import sync_to_async
        from app_uma_info_portal.models import GuildChannelRule
        from app_uma_info_portal.guild_settings_service import (
            format_read_scope_summary,
            get_or_create_guild_setting,
            update_guild_setting_fields,
        )

        def _apply():
            guild, setting = get_or_create_guild_setting(
                str(interaction.guild.id), guild_name=interaction.guild.name,
            )
            update_guild_setting_fields(
                str(interaction.guild.id),
                {'read_scope': 'advanced'},
                str(interaction.user.id),
                guild_name=interaction.guild.name,
                send_news_confirm=False,
            )
            GuildChannelRule.objects.update_or_create(
                guild=guild,
                channel_id=str(channel.id),
                defaults={
                    'channel_name': channel.name,
                    'rule_type': rule_type.value,
                    'note': f'Discord 斜線指令 by {interaction.user}',
                },
            )
            setting.refresh_from_db()
            return format_read_scope_summary(setting)

        summary = await sync_to_async(_apply)()
        tag = 'allow' if rule_type.value == 'allow' else 'deny'
        await interaction.response.send_message(
            f'✅ 已新增 **{tag}** 規則：`#{channel.name}`\n{summary}',
            ephemeral=True,
        )

    @read_scope.command(name='rule-remove', description='移除進階頻道規則')
    async def read_scope_rule_remove(
        interaction: discord.Interaction,
        channel: discord.TextChannel,
    ):
        if not await _require_admin(interaction):
            return

        from asgiref.sync import sync_to_async
        from app_uma_info_portal.models import GuildChannelRule, DiscordGuild
        from app_uma_info_portal.guild_settings_service import format_read_scope_summary, get_or_create_guild_setting

        def _apply():
            _, setting = get_or_create_guild_setting(
                str(interaction.guild.id), guild_name=interaction.guild.name,
            )
            guild = DiscordGuild.objects.get(guild_id=str(interaction.guild.id))
            deleted, _ = GuildChannelRule.objects.filter(
                guild=guild, channel_id=str(channel.id),
            ).delete()
            setting.refresh_from_db()
            return deleted, format_read_scope_summary(setting)

        deleted, summary = await sync_to_async(_apply)()
        if deleted:
            await interaction.response.send_message(
                f'🗑️ 已移除 `#{channel.name}` 的規則。\n{summary}',
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                f'⚠️ `#{channel.name}` 沒有進階規則紀錄。',
                ephemeral=True,
            )

    @read_scope.command(name='rule-list', description='列出進階 Allow/Deny 規則')
    async def read_scope_rule_list(interaction: discord.Interaction):
        if not await _require_admin(interaction):
            return
        from asgiref.sync import sync_to_async
        from app_uma_info_portal.guild_settings_service import (
            format_read_scope_summary,
            get_or_create_guild_setting,
        )

        def _fetch():
            _, setting = get_or_create_guild_setting(
                str(interaction.guild.id), guild_name=interaction.guild.name,
            )
            return format_read_scope_summary(setting)

        text = await sync_to_async(_fetch)()
        await interaction.response.send_message(text, ephemeral=True)

    @news_target.command(name='view', description='查看目前推播目標設定')
    async def news_target_view(interaction: discord.Interaction):
        if not await _require_admin(interaction):
            return
        from asgiref.sync import sync_to_async
        from app_uma_info_portal.guild_settings_service import (
            format_news_target_summary,
            get_or_create_guild_setting,
        )

        def _fetch():
            _, setting = get_or_create_guild_setting(
                str(interaction.guild.id), guild_name=interaction.guild.name,
            )
            return format_news_target_summary(setting)

        text = await sync_to_async(_fetch)()
        await interaction.response.send_message(
            f'📰 **推播目標** — {interaction.guild.name}\n{text}',
            ephemeral=True,
        )

    @news_target.command(name='set', description='設定推播頻道、開關、語氣與 Ping 身分組')
    @app_commands.describe(
        channel='推播目標頻道（留空表示清除）',
        enabled='是否啟用情報推播',
        tone='摘要語氣',
        ping_role='推播時 Ping 的身分組（可選）',
    )
    @app_commands.choices(tone=TONE_CHOICES)
    async def news_target_set(
        interaction: discord.Interaction,
        channel: discord.TextChannel | None = None,
        enabled: bool | None = None,
        tone: app_commands.Choice[str] | None = None,
        ping_role: discord.Role | None = None,
    ):
        if not await _require_admin(interaction):
            return

        if channel is None and enabled is None and tone is None and ping_role is None:
            await interaction.response.send_message(
                '❌ 請至少指定一項要更新的參數（channel / enabled / tone / ping_role）。',
                ephemeral=True,
            )
            return

        if channel is not None:
            bot_member = interaction.guild.me
            if not _bot_can_send(channel, bot_member):
                await interaction.response.send_message(
                    f'❌ Bot 在 #{channel.name} 沒有「檢視頻道 / 傳送訊息 / 嵌入連結」權限，無法設為推播頻道。',
                    ephemeral=True,
                )
                return

        payload: dict = {}
        if channel is not None:
            payload['news_channel_id'] = str(channel.id)
        if enabled is not None:
            payload['news_enabled'] = enabled
        if tone is not None:
            payload['news_tone'] = tone.value
        if ping_role is not None:
            payload['ping_role_id'] = str(ping_role.id)

        from asgiref.sync import sync_to_async
        from app_uma_info_portal.guild_settings_service import (
            format_news_target_summary,
            update_guild_setting_fields,
        )

        def _apply():
            result = update_guild_setting_fields(
                str(interaction.guild.id),
                payload,
                str(interaction.user.id),
                guild_name=interaction.guild.name,
                send_news_confirm=True,
            )
            return result['news_channel_confirm_sent'], format_news_target_summary(result['setting'])

        confirm_sent, summary = await sync_to_async(_apply)()
        extra = '\n📨 已向推播頻道發送確認訊息。' if confirm_sent else ''
        await interaction.response.send_message(
            f'✅ 已更新推播目標。{extra}\n{summary}',
            ephemeral=True,
        )

    @news_target.command(name='clear', description='清除推播頻道設定')
    async def news_target_clear(interaction: discord.Interaction):
        if not await _require_admin(interaction):
            return
        from asgiref.sync import sync_to_async
        from app_uma_info_portal.guild_settings_service import (
            format_news_target_summary,
            update_guild_setting_fields,
        )

        def _apply():
            result = update_guild_setting_fields(
                str(interaction.guild.id),
                {'news_channel_id': ''},
                str(interaction.user.id),
                guild_name=interaction.guild.name,
                send_news_confirm=False,
            )
            return format_news_target_summary(result['setting'])

        summary = await sync_to_async(_apply)()
        await interaction.response.send_message(
            f'✅ 已清除推播頻道。\n{summary}',
            ephemeral=True,
        )

    tree.add_command(read_scope)
    tree.add_command(news_target)
