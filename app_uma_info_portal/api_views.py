"""
UMA Info Portal — REST API Views
"""
import json
import logging

from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import get_object_or_404

from .models import (
    DiscordGuild, GuildSetting, GuildChannelRule,
    GuildChannelCache, GuildRoleCache, GuildSettingAudit,
)
from .views import check_guild_permission


def _check(request, guild_id):
    """快速驗證路由層級的權限，失敗回傳 JsonResponse，成功回傳 None"""
    if not check_guild_permission(request, guild_id):
        return JsonResponse({'error': '無管理權限或未登入'}, status=403)
    return None


@require_GET
def api_guild_channels(request, guild_id: str):
    err = _check(request, guild_id)
    if err:
        return err
    guild = get_object_or_404(DiscordGuild, guild_id=guild_id)
    channels = list(
        GuildChannelCache.objects.filter(guild=guild)
        .order_by('position')
        .values('channel_id', 'channel_name', 'channel_type')
    )
    return JsonResponse({'channels': channels})


@require_GET
def api_guild_roles(request, guild_id: str):
    err = _check(request, guild_id)
    if err:
        return err
    guild = get_object_or_404(DiscordGuild, guild_id=guild_id)
    roles = list(
        GuildRoleCache.objects.filter(guild=guild)
        .order_by('-position')
        .values('role_id', 'role_name', 'role_color')
    )
    return JsonResponse({'roles': roles})


@require_GET
def api_guild_stats(request, guild_id: str):
    """取得伺服器即時統計（總覽 / 統計面板動態刷新用）"""
    err = _check(request, guild_id)
    if err:
        return err
    guild = get_object_or_404(DiscordGuild, guild_id=guild_id)
    from .guild_stats import compute_guild_stats
    channel_count = GuildChannelCache.objects.filter(guild=guild).count()
    stats = compute_guild_stats(guild_id, channel_count=channel_count)
    return JsonResponse({'guild_id': guild_id, 'guild_name': guild.name, 'stats': stats})


# ── 儲存設定 ────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def api_guild_settings_save(request, guild_id: str):
    err = _check(request, guild_id)
    if err:
        return err

    guild = get_object_or_404(DiscordGuild, guild_id=guild_id)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': '無效的 JSON 格式'}, status=400)

    user_id = request.session.get('discord_user_id', '')

    from .guild_settings_service import update_guild_setting_fields

    result = update_guild_setting_fields(
        guild_id,
        data,
        user_id,
        guild_name=guild.name,
        send_news_confirm=True,
    )

    return JsonResponse({
        'status': 'ok',
        'updated_fields': result['updated_fields'],
        'news_channel_confirm_sent': result['news_channel_confirm_sent'],
    })


# ── 頻道規則 CRUD ────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def api_channel_rule_add(request, guild_id: str):
    err = _check(request, guild_id)
    if err:
        return err

    guild = get_object_or_404(DiscordGuild, guild_id=guild_id)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': '無效的 JSON 格式'}, status=400)

    channel_id = data.get('channel_id', '').strip()
    if not channel_id:
        return JsonResponse({'error': '缺少 channel_id'}, status=400)

    rule_type = data.get('rule_type', 'allow')
    if rule_type not in ('allow', 'deny'):
        return JsonResponse({'error': '無效的 rule_type'}, status=400)

    rule, created = GuildChannelRule.objects.update_or_create(
        guild=guild, channel_id=channel_id,
        defaults={
            'channel_name': data.get('channel_name', ''),
            'rule_type':    rule_type,
            'note':         data.get('note', ''),
        }
    )
    return JsonResponse({'status': 'ok', 'id': rule.pk, 'created': created})


@csrf_exempt
@require_POST
def api_channel_rule_delete(request, guild_id: str, pk: int):
    err = _check(request, guild_id)
    if err:
        return err

    guild = get_object_or_404(DiscordGuild, guild_id=guild_id)
    rule  = get_object_or_404(GuildChannelRule, pk=pk, guild=guild)
    rule.delete()
    return JsonResponse({'status': 'ok'})


# ── 快取同步觸發（管理員手動刷新）────────────────────────────────────────

@csrf_exempt
@require_POST
def api_sync_cache(request, guild_id: str):
    """觸發 Bot 重新同步該伺服器的頻道與身分組快取（非同步觸發，立即回傳）"""
    err = _check(request, guild_id)
    if err:
        return err

    # 寫入一個任務觸發旗標給 Bot 讀取（簡單做法：直接透過 Bot 物件呼叫）
    try:
        from app_discord_bot.management.commands.run_discord_bot import get_bot_instance
        import asyncio
        bot = get_bot_instance()
        if bot:
            asyncio.run_coroutine_threadsafe(
                bot.sync_guild_cache(guild_id),
                bot.loop,
            )
            return JsonResponse({'status': 'triggered'})
    except Exception:
        pass

    return JsonResponse({'status': 'queued', 'message': 'Bot 同步將於下次啟動時執行'})


# ── 稽核記錄 ────────────────────────────────────────────────────────────

@require_GET
def api_guild_audits(request, guild_id: str):
    err = _check(request, guild_id)
    if err:
        return err

    guild  = get_object_or_404(DiscordGuild, guild_id=guild_id)
    audits = list(
        GuildSettingAudit.objects.filter(guild=guild)
        .order_by('-changed_at')[:50]
        .values('changed_by', 'changed_at', 'field_name', 'old_value', 'new_value')
    )
    return JsonResponse({'audits': audits})


# ── 推播頻道 Embed 確認 ──────────────────────────────────────────────────

def _send_news_channel_confirm_embed(guild, setting, changed_by: str):
    """
    直接透過 Discord HTTP API（Bot Token）向推播頻道發送設定確認 Embed。
    不依賴 Bot 進程（get_bot_instance 只在同進程有效），適用於 Django web server 呼叫。
    回傳 (ok: bool, reason: str)。
    """
    import os
    import requests as _req

    token = os.getenv('DISCORD_BOT_TOKEN', '')
    channel_id = setting.news_channel_id

    if not token:
        return False, 'DISCORD_BOT_TOKEN 未設定'
    if not channel_id or not channel_id.isdigit():
        return False, '尚未設定有效的推播頻道'

    tone_label = '🎉 活潑（社群向）' if setting.news_tone == 'lively' else '📋 簡潔（資訊向）'
    fields = [
        {'name': '伺服器',   'value': guild.name,                                          'inline': True},
        {'name': '推播開關', 'value': '✅ 啟用' if setting.news_enabled else '⏸ 停用',     'inline': True},
        {'name': '摘要語氣', 'value': tone_label,                                          'inline': True},
    ]
    if setting.ping_role_id:
        fields.append({'name': 'Ping 身分組', 'value': f'<@&{setting.ping_role_id}>', 'inline': True})

    payload = {
        'embeds': [{
            'title':       '✅ UMA Info 推播頻道已設定',
            'description': (
                f'此頻道已成功設定為 **{guild.name}** 的每日情報推播頻道。\n'
                'UMA Info Bot 將依控制台排程時間在這裡推送最新賽馬娘情報摘要。'
            ),
            'color': 0x5865F2,
            'fields': fields,
            'footer': {'text': f'由 {changed_by or "UMA Info 管理員"} 設定 · 如需調整請至 /uma-info/'},
        }],
    }

    log = logging.getLogger(__name__)
    try:
        resp = _req.post(
            f'https://discord.com/api/v10/channels/{channel_id}/messages',
            headers={'Authorization': f'Bot {token}', 'Content-Type': 'application/json'},
            json=payload,
            timeout=10,
        )
        if resp.status_code in (200, 201):
            return True, ''

        # 解析 Discord 錯誤碼，回傳可判讀原因
        reason = f'Discord API 回應 {resp.status_code}'
        if resp.status_code == 403:
            reason = 'Bot 在此頻道沒有「傳送訊息／嵌入連結」權限，請至 Discord 頻道權限設定後重試'
        elif resp.status_code == 404:
            reason = '找不到該頻道（可能已刪除或 Bot 不在該伺服器）'
        elif resp.status_code == 400:
            reason = '此頻道類型無法直接發送訊息（例如論壇或分類頻道），請改選文字頻道'
        log.warning(f'[Portal] 發送 Embed 失敗：{resp.status_code} {resp.text[:200]}')
        return False, reason
    except Exception as exc:
        log.warning(f'[Portal] 推播頻道確認 Embed 例外：{exc}')
        return False, f'發送時發生例外：{exc}'


@csrf_exempt
@require_POST
def api_confirm_news_channel(request, guild_id: str):
    """
    POST：向目前設定的推播頻道發送確認 Embed。
    可在儲存後前端主動呼叫，或由 api_guild_settings_save 在頻道變更時自動觸發。
    """
    err = _check(request, guild_id)
    if err:
        return err

    guild   = get_object_or_404(DiscordGuild, guild_id=guild_id)
    setting = GuildSetting.objects.filter(guild=guild).first()
    if not setting or not setting.news_channel_id:
        return JsonResponse({'status': 'skipped', 'reason': '尚未設定推播頻道'})

    user_id = request.session.get('discord_user_id', '')
    sent, reason = _send_news_channel_confirm_embed(guild, setting, user_id)
    if sent:
        return JsonResponse({'status': 'sent'})
    return JsonResponse({'status': 'failed', 'reason': reason})
