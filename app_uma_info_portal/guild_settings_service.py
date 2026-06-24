"""
GuildSetting 共用更新邏輯（Portal API 與 Discord Bot 斜線指令共用）
"""
from __future__ import annotations

from app_uma_info_portal.models import (
    DiscordGuild,
    GuildSetting,
    GuildSettingAudit,
    READ_SCOPE_CHOICES,
    NEWS_TONE_CHOICES,
)

# Portal 與 Discord 斜線指令允許寫入的欄位
GUILD_SETTING_WRITABLE_FIELDS = frozenset({
    'read_scope', 'single_channel_id',
    'news_channel_id', 'ping_role_id', 'news_enabled', 'news_tone',
    'ai_chat_enabled', 'ai_daily_quota',
})

READ_SCOPE_LABELS = dict(READ_SCOPE_CHOICES)
NEWS_TONE_LABELS = dict(NEWS_TONE_CHOICES)


def get_or_create_guild_setting(guild_id: str, guild_name: str = '') -> tuple[DiscordGuild, GuildSetting]:
    """取得或建立 DiscordGuild + GuildSetting。"""
    defaults = {'name': guild_name or guild_id, 'is_bot_present': True}
    dg, _ = DiscordGuild.objects.get_or_create(guild_id=str(guild_id), defaults=defaults)
    if guild_name and dg.name != guild_name:
        dg.name = guild_name
        dg.is_bot_present = True
        dg.save(update_fields=['name', 'is_bot_present'])
    setting, _ = GuildSetting.objects.get_or_create(guild=dg)
    return dg, setting


def update_guild_setting_fields(
    guild_id: str,
    data: dict,
    changed_by: str,
    *,
    guild_name: str = '',
    send_news_confirm: bool = True,
) -> dict:
    """
    更新 GuildSetting 允許欄位並寫入稽核。
    回傳 {'updated_fields': [...], 'news_channel_changed': bool}
    """
    guild, setting = get_or_create_guild_setting(guild_id, guild_name=guild_name)
    audits: list[GuildSettingAudit] = []
    updated_fields: list[str] = []
    news_channel_changed = False
    old_news_channel = setting.news_channel_id

    for field, new_val in data.items():
        if field not in GUILD_SETTING_WRITABLE_FIELDS:
            continue
        old_val = str(getattr(setting, field))
        new_str = str(new_val)
        if old_val != new_str:
            audits.append(GuildSettingAudit(
                guild=guild,
                changed_by=str(changed_by),
                field_name=field,
                old_value=old_val,
                new_value=new_str,
            ))
            updated_fields.append(field)
            if field == 'news_channel_id':
                news_channel_changed = True
        setattr(setting, field, new_val)

    if updated_fields:
        setting.updated_by = str(changed_by)
        setting.save()
        GuildSettingAudit.objects.bulk_create(audits)

    # Embed 確認由前端 _sendNewsChannelConfirm() 統一負責，service 層不重複觸發
    return {
        'guild': guild,
        'setting': setting,
        'updated_fields': updated_fields,
        'news_channel_changed': news_channel_changed,
        'news_channel_confirm_sent': False,
    }


def format_read_scope_summary(setting: GuildSetting) -> str:
    """格式化讀取範圍摘要（供 Discord / 日誌使用）。"""
    from app_uma_info_portal.models import GuildChannelRule, GuildChannelCache

    label = READ_SCOPE_LABELS.get(setting.read_scope, setting.read_scope)
    lines = [f'**讀取範圍**：{label}']

    if setting.read_scope == 'single':
        ch_name = setting.single_channel_id
        if setting.single_channel_id:
            cached = GuildChannelCache.objects.filter(
                guild=setting.guild, channel_id=setting.single_channel_id,
            ).first()
            if cached:
                ch_name = f'#{cached.channel_name} (`{setting.single_channel_id}`)'
            else:
                ch_name = f'`{setting.single_channel_id}`'
        lines.append(f'**指定頻道**：{ch_name or "（未設定）"}')

    if setting.read_scope == 'advanced':
        rules = GuildChannelRule.objects.filter(guild=setting.guild).order_by('rule_type', 'channel_name')
        if not rules:
            lines.append('**進階規則**：（尚無 allow/deny 規則）')
        else:
            lines.append('**進階規則**：')
            for r in rules[:15]:
                tag = '✅ allow' if r.rule_type == 'allow' else '⛔ deny'
                name = r.channel_name or r.channel_id
                lines.append(f'  · {tag} `#{name}` (`{r.channel_id}`)')
            if rules.count() > 15:
                lines.append(f'  … 另有 {rules.count() - 15} 條')

    return '\n'.join(lines)


def format_news_target_summary(setting: GuildSetting) -> str:
    """格式化推播目標摘要。"""
    from app_uma_info_portal.models import GuildChannelCache, GuildRoleCache

    enabled = '✅ 啟用' if setting.news_enabled else '⏸ 停用'
    tone = NEWS_TONE_LABELS.get(setting.news_tone, setting.news_tone)

    ch_label = '（未設定）'
    if setting.news_channel_id:
        cached = GuildChannelCache.objects.filter(
            guild=setting.guild, channel_id=setting.news_channel_id,
        ).first()
        ch_label = f'#{cached.channel_name}' if cached else setting.news_channel_id
        ch_label += f' (`{setting.news_channel_id}`)'

    role_label = '（不 Ping）'
    if setting.ping_role_id:
        role = GuildRoleCache.objects.filter(
            guild=setting.guild, role_id=setting.ping_role_id,
        ).first()
        role_label = f'@{role.role_name}' if role else setting.ping_role_id
        role_label += f' (`{setting.ping_role_id}`)'

    return (
        f'**推播開關**：{enabled}\n'
        f'**推播頻道**：{ch_label}\n'
        f'**Ping 身分組**：{role_label}\n'
        f'**摘要語氣**：{tone}\n'
        f'📅 推播時程（頻率/時間）由情報站控制台統一管理。'
    )
