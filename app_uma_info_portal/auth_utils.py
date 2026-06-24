"""
UMA Info Portal — Discord OAuth2 工具函式
"""
import os
import secrets
import requests
from urllib.parse import urlencode


DISCORD_API = 'https://discord.com/api/v10'
DISCORD_AUTH_URL = 'https://discord.com/oauth2/authorize'
DISCORD_TOKEN_URL = 'https://discord.com/api/oauth2/token'

MANAGE_GUILD   = 0x20
ADMINISTRATOR  = 0x8


def get_oauth_url(state: str) -> str:
    """組合 Discord OAuth2 授權 URL"""
    params = {
        'client_id':     os.getenv('DISCORD_CLIENT_ID', ''),
        'redirect_uri':  os.getenv('DISCORD_OAUTH_REDIRECT', 'http://localhost:8000/uma-info/auth/callback/'),
        'response_type': 'code',
        'scope':         'identify guilds',
        'state':         state,
        'prompt':        'none',
    }
    return DISCORD_AUTH_URL + '?' + urlencode(params)


def get_invite_url() -> str:
    """產生最小權限 Bot 邀請連結"""
    # 必要：ViewChannel(1024) + SendMessages(2048) + ReadMessageHistory(65536) + EmbedLinks(16384)
    permissions = 1024 + 2048 + 65536 + 16384
    params = {
        'client_id':   os.getenv('DISCORD_CLIENT_ID', ''),
        'permissions': permissions,
        'scope':       'bot',
    }
    return DISCORD_AUTH_URL + '?' + urlencode(params)


def exchange_code(code: str) -> dict:
    """用 authorization code 換取 access_token"""
    data = {
        'client_id':     os.getenv('DISCORD_CLIENT_ID', ''),
        'client_secret': os.getenv('DISCORD_CLIENT_SECRET', ''),
        'grant_type':    'authorization_code',
        'code':          code,
        'redirect_uri':  os.getenv('DISCORD_OAUTH_REDIRECT', 'http://localhost:8000/uma-info/auth/callback/'),
    }
    resp = requests.post(DISCORD_TOKEN_URL, data=data, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_user_info(access_token: str) -> dict:
    """取得 Discord 用戶資訊 /users/@me"""
    headers = {'Authorization': f'Bearer {access_token}'}
    resp = requests.get(f'{DISCORD_API}/users/@me', headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_user_guilds(access_token: str) -> list:
    """取得用戶所在伺服器清單 /users/@me/guilds"""
    headers = {'Authorization': f'Bearer {access_token}'}
    resp = requests.get(f'{DISCORD_API}/users/@me/guilds', headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()


def can_manage_guild(permissions_int) -> bool:
    """判斷用戶是否擁有該伺服器管理權限"""
    try:
        p = int(permissions_int)
        return bool(p & ADMINISTRATOR) or bool(p & MANAGE_GUILD)
    except (TypeError, ValueError):
        return False


def filter_manageable_guilds(guilds: list) -> list:
    """回傳用戶可管理的伺服器清單"""
    return [g for g in guilds if can_manage_guild(g.get('permissions', 0))]


def generate_state() -> str:
    return secrets.token_urlsafe(32)
