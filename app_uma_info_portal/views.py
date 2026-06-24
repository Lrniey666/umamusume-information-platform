"""
UMA Info Portal — 頁面 Views
"""
import json
import datetime
import os

from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .models import DiscordUser, DiscordGuild, GuildSetting, GuildChannelRule, GuildChannelCache, GuildRoleCache
from .auth_utils import (
    get_oauth_url, get_invite_url,
    exchange_code, get_user_info, get_user_guilds,
    filter_manageable_guilds, generate_state,
)
from .models import encrypt_token


# ── 工具函式 ────────────────────────────────────────────────────────────

def _portal_user(request):
    """從 session 取得目前登入用戶（或 None）"""
    uid = request.session.get('discord_user_id')
    if not uid:
        return None
    return DiscordUser.objects.filter(discord_id=uid).first()


def check_guild_permission(request, guild_id: str) -> bool:
    """確認目前用戶對該伺服器擁有管理權限"""
    if not request.session.get('discord_user_id'):
        return False
    return guild_id in request.session.get('manageable_guild_ids', [])


def _uma_chat_model_label() -> str:
    """將 UMA_CHAT_MODEL 環境變數轉為前台可讀名稱"""
    from django.conf import settings
    labels = {
        'gemini-3.1-flash-lite': 'Gemini 3.1 Flash Lite',
        'gemini-3.5-flash': 'Gemini 3.5 Flash',
        'gemini-2.5-flash-lite': 'Gemini 2.5 Flash Lite',
        'gemini-2.5-flash': 'Gemini 2.5 Flash',
    }
    model_id = getattr(settings, 'UMA_CHAT_MODEL', 'gemini-3.5-flash')
    return labels.get(model_id, model_id)


# ── 首頁 ────────────────────────────────────────────────────────────────

def home(request):
    user = _portal_user(request)
    guild_count = DiscordGuild.objects.filter(is_bot_present=True).count()
    return render(request, 'app_uma_info_portal/home.html', {
        'user': user,
        'invite_url': get_invite_url(),
        'guild_count': guild_count,
        'client_id_set': bool(os.getenv('DISCORD_CLIENT_ID')),
    })


# ── OAuth 流程 ──────────────────────────────────────────────────────────

def auth_login(request):
    if not os.getenv('DISCORD_CLIENT_ID'):
        return redirect('/uma-info/?error=no_client_id')
    state = generate_state()
    request.session['oauth_state'] = state
    return redirect(get_oauth_url(state))


def auth_callback(request):
    error = request.GET.get('error')
    if error:
        return redirect('/uma-info/?error=' + error)

    code  = request.GET.get('code', '')
    state = request.GET.get('state', '')

    if state != request.session.pop('oauth_state', None):
        return redirect('/uma-info/?error=invalid_state')

    try:
        token_data = exchange_code(code)
    except Exception:
        return redirect('/uma-info/?error=token_exchange')

    access_token = token_data.get('access_token', '')
    if not access_token:
        return redirect('/uma-info/?error=no_token')

    try:
        user_info = get_user_info(access_token)
        guilds    = get_user_guilds(access_token)
    except Exception:
        return redirect('/uma-info/?error=api_error')

    # 計算 token 到期時間
    expires_in = token_data.get('expires_in', 604800)
    expires_at = timezone.now() + datetime.timedelta(seconds=expires_in)

    # 更新或建立 DiscordUser
    avatar_hash = user_info.get('avatar') or ''
    discord_user, _ = DiscordUser.objects.update_or_create(
        discord_id=user_info['id'],
        defaults={
            'username':          user_info.get('global_name') or user_info.get('username', ''),
            'avatar_hash':       avatar_hash,
            'access_token_enc':  encrypt_token(access_token),
            'token_expires_at':  expires_at,
        }
    )

    # 篩選可管理的伺服器
    manageable = filter_manageable_guilds(guilds)
    manageable_ids = [g['id'] for g in manageable]

    # 把完整伺服器資料存入 session（給 servers 頁面用）
    request.session['discord_user_id']       = discord_user.discord_id
    request.session['manageable_guild_ids']  = manageable_ids
    request.session['user_guilds_raw']       = [
        {'id': g['id'], 'name': g['name'], 'icon': g.get('icon') or ''}
        for g in manageable
    ]

    return redirect('/uma-info/servers/')


def auth_logout(request):
    request.session.flush()
    return redirect('/uma-info/')


# ── 伺服器選擇頁 ─────────────────────────────────────────────────────────

def servers(request):
    user = _portal_user(request)
    if not user:
        return redirect('/uma-info/')

    manageable_ids = request.session.get('manageable_guild_ids', [])
    guilds_raw     = request.session.get('user_guilds_raw', [])

    # 已安裝 Bot 的伺服器（DB 中有紀錄且 is_bot_present）
    installed_guilds = list(
        DiscordGuild.objects.filter(guild_id__in=manageable_ids, is_bot_present=True)
    )
    installed_ids = {g.guild_id for g in installed_guilds}

    # OAuth Session 資料含有 Discord API 直接回傳的 icon hash（純 hash，無 CDN 前綴）
    # 若 DB 中 icon_hash 為空（例如 Bot 尚未重啟重新同步），以 session 資料補足並持久化
    session_icon_map = {g['id']: (g.get('icon') or '') for g in guilds_raw}
    needs_update = []
    for guild in installed_guilds:
        if not guild.icon_hash:
            session_hash = session_icon_map.get(guild.guild_id, '')
            if session_hash:
                guild.icon_hash = session_hash
                needs_update.append(guild)
    if needs_update:
        DiscordGuild.objects.bulk_update(needs_update, ['icon_hash'])

    # 各伺服器已收集訊息數（供選擇頁預覽）
    try:
        from app_discord_bot.models import DiscordMessage
        from django.db.models import Count
        msg_counts = dict(
            DiscordMessage.objects
            .filter(guild_id__in=installed_ids)
            .values('guild_id')
            .annotate(c=Count('id'))
            .values_list('guild_id', 'c')
        )
    except Exception:
        msg_counts = {}
    for guild in installed_guilds:
        guild.msg_count = msg_counts.get(guild.guild_id, 0)

    # 未安裝：在 guilds_raw 中但不在 installed_ids
    not_installed = [g for g in guilds_raw if g['id'] not in installed_ids]

    return render(request, 'app_uma_info_portal/servers.html', {
        'user':             user,
        'installed_guilds': installed_guilds,
        'not_installed':    not_installed,
        'invite_url':       get_invite_url(),
        'total_manageable': len(manageable_ids),
    })


# ── 單一伺服器管理頁 ─────────────────────────────────────────────────────

def server_manage(request, guild_id: str):
    user = _portal_user(request)
    if not user:
        return redirect('/uma-info/')
    if not check_guild_permission(request, guild_id):
        return redirect('/uma-info/servers/')

    guild   = get_object_or_404(DiscordGuild, guild_id=guild_id, is_bot_present=True)
    setting, _ = GuildSetting.objects.get_or_create(guild=guild)

    channel_rules = list(GuildChannelRule.objects.filter(guild=guild))

    all_channels = GuildChannelCache.objects.filter(guild=guild).order_by('position')
    # 依 Bot 實際權限分組供模板使用：
    #   readable_channels — Bot 可讀取歷史（爬取來源選擇）
    #   sendable_channels — Bot 可發訊息且可嵌入（推播頻道選擇）
    channels           = list(all_channels)
    readable_channels  = [ch for ch in channels if ch.bot_can_read]
    sendable_channels  = [ch for ch in channels if ch.bot_can_send]

    roles = list(GuildRoleCache.objects.filter(guild=guild).order_by('-position'))

    from .guild_stats import compute_guild_stats
    stats = compute_guild_stats(guild_id, channel_count=len(channels))

    # 稽核記錄（最近 10 筆）
    from .models import GuildSettingAudit
    audits = list(GuildSettingAudit.objects.filter(guild=guild)[:10])

    return render(request, 'app_uma_info_portal/server_manage.html', {
        'user':               user,
        'guild':              guild,
        'setting':            setting,
        'channel_rules':      channel_rules,
        'channels':           channels,
        'readable_channels':  readable_channels,
        'sendable_channels':  sendable_channels,
        'roles':              roles,
        'audits':             audits,
        'stats':              stats,
        'ai_chat_model_label': _uma_chat_model_label(),
    })
