"""
UMA Info Portal 資料模型
以「伺服器（Guild）」為中心，管理 Bot 的逐伺服器設定。
"""
from django.db import models
from django.core import signing


# ── Token 加解密（用 Django SECRET_KEY，無需額外套件）──────────────────

def encrypt_token(raw: str) -> str:
    """加密 OAuth token（Signed + compressed，防止明文入庫）"""
    if not raw:
        return ''
    return signing.dumps(raw, salt='uma_info_oauth_token')


def decrypt_token(enc: str) -> str:
    """解密 OAuth token"""
    if not enc:
        return ''
    try:
        return signing.loads(enc, salt='uma_info_oauth_token', max_age=None)
    except (signing.BadSignature, signing.SignatureExpired):
        return ''


# ── Discord 登入用戶 ────────────────────────────────────────────────────

class DiscordUser(models.Model):
    """Discord OAuth 登入用戶"""
    discord_id          = models.CharField(max_length=30, unique=True, verbose_name='Discord ID')
    username            = models.CharField(max_length=200, verbose_name='顯示名稱')
    avatar_hash         = models.CharField(max_length=100, blank=True, verbose_name='頭像 Hash')
    access_token_enc    = models.TextField(blank=True, verbose_name='Access Token（加密）')
    refresh_token_enc   = models.TextField(blank=True, verbose_name='Refresh Token（加密）')
    token_expires_at    = models.DateTimeField(null=True, blank=True, verbose_name='Token 到期')
    last_login_at       = models.DateTimeField(auto_now=True, verbose_name='最後登入')
    created_at          = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Discord 用戶'
        verbose_name_plural = 'Discord 用戶'

    def __str__(self):
        return f'{self.username} ({self.discord_id})'

    @property
    def access_token(self) -> str:
        return decrypt_token(self.access_token_enc)

    @access_token.setter
    def access_token(self, raw: str):
        self.access_token_enc = encrypt_token(raw)

    @property
    def avatar_url(self) -> str:
        if self.avatar_hash:
            return f'https://cdn.discordapp.com/avatars/{self.discord_id}/{self.avatar_hash}.png'
        return f'https://cdn.discordapp.com/embed/avatars/0.png'


# ── Discord 伺服器 ──────────────────────────────────────────────────────

class DiscordGuild(models.Model):
    """Bot 曾加入或已加入的 Discord 伺服器"""
    guild_id        = models.CharField(max_length=30, unique=True, verbose_name='伺服器 ID')
    name            = models.CharField(max_length=200, verbose_name='伺服器名稱')
    icon_hash       = models.CharField(max_length=100, blank=True, verbose_name='圖示 Hash')
    joined_at       = models.DateTimeField(null=True, blank=True, verbose_name='Bot 加入時間')
    is_bot_present  = models.BooleanField(default=False, verbose_name='Bot 在線中')
    member_count    = models.IntegerField(default=0, verbose_name='成員數')
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Discord 伺服器'
        verbose_name_plural = 'Discord 伺服器'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.guild_id})'

    @property
    def icon_url(self) -> str:
        if not self.icon_hash:
            return ''
        # 相容舊版：若 icon_hash 已是完整 URL（由 str(guild.icon) 存入），直接使用
        if self.icon_hash.startswith('http'):
            return self.icon_hash.split('?')[0]
        # 正常格式：純 hash 字串
        ext = 'gif' if self.icon_hash.startswith('a_') else 'png'
        return f'https://cdn.discordapp.com/icons/{self.guild_id}/{self.icon_hash}.{ext}'


# ── 逐伺服器設定 ────────────────────────────────────────────────────────

READ_SCOPE_CHOICES = [
    ('all',           '全部頻道（預設）'),
    ('announcements', '僅公告頻道'),
    ('single',        '僅單一頻道'),
    ('advanced',      '進階設定（Allow/Deny 清單）'),
]

NEWS_FREQ_CHOICES = [
    ('daily',  '每日'),
    ('weekly', '每週'),
    ('off',    '關閉'),
]

NEWS_TONE_CHOICES = [
    ('lively',  '活潑（適合社群）'),
    ('concise', '簡潔（資訊為主）'),
]


class GuildSetting(models.Model):
    """每伺服器的 UMA Info Bot 設定（OneToOne to DiscordGuild）"""
    guild               = models.OneToOneField(
                            DiscordGuild, on_delete=models.CASCADE,
                            related_name='setting', verbose_name='伺服器')
    # 頻道讀取
    read_scope          = models.CharField(
                            max_length=20, choices=READ_SCOPE_CHOICES,
                            default='all', verbose_name='讀取範圍')
    single_channel_id   = models.CharField(max_length=30, blank=True, verbose_name='指定單一頻道 ID')
    # 推播設定
    news_channel_id     = models.CharField(max_length=30, blank=True, verbose_name='推播頻道 ID')
    ping_role_id        = models.CharField(max_length=30, blank=True, verbose_name='Ping 身分組 ID')
    news_enabled        = models.BooleanField(default=True, verbose_name='啟用推播')
    news_frequency      = models.CharField(
                            max_length=10, choices=NEWS_FREQ_CHOICES,
                            default='daily', verbose_name='推播頻率')
    news_hour           = models.IntegerField(default=20, verbose_name='推播時間（整點，台北）')
    news_tone           = models.CharField(
                            max_length=10, choices=NEWS_TONE_CHOICES,
                            default='lively', verbose_name='摘要語氣')
    # AI 問答
    ai_chat_enabled     = models.BooleanField(default=True, verbose_name='啟用 AI 問答')
    ai_daily_quota      = models.IntegerField(default=100, verbose_name='每日 AI 問答上限')
    # 稽核
    updated_by          = models.CharField(max_length=30, blank=True, verbose_name='最後修改者')
    updated_at          = models.DateTimeField(auto_now=True, verbose_name='最後修改時間')

    class Meta:
        verbose_name = '伺服器設定'
        verbose_name_plural = '伺服器設定'

    def __str__(self):
        return f'設定：{self.guild.name}'


# ── 進階頻道 Allow/Deny 清單 ────────────────────────────────────────────

RULE_TYPE_CHOICES = [('allow', '允許'), ('deny', '排除')]


class GuildChannelRule(models.Model):
    """進階讀取範圍的頻道允許/排除清單"""
    guild        = models.ForeignKey(
                     DiscordGuild, on_delete=models.CASCADE,
                     related_name='channel_rules', verbose_name='伺服器')
    channel_id   = models.CharField(max_length=30, verbose_name='頻道 ID')
    channel_name = models.CharField(max_length=200, blank=True, verbose_name='頻道名稱')
    rule_type    = models.CharField(max_length=5, choices=RULE_TYPE_CHOICES, verbose_name='規則類型')
    note         = models.CharField(max_length=200, blank=True, verbose_name='備注')

    class Meta:
        verbose_name = '頻道規則'
        verbose_name_plural = '頻道規則'
        unique_together = [('guild', 'channel_id')]

    def __str__(self):
        return f'[{self.rule_type}] {self.channel_name or self.channel_id}'


# ── 設定變更稽核 ────────────────────────────────────────────────────────

class GuildSettingAudit(models.Model):
    """設定變更紀錄（可追溯多管理員協作）"""
    guild       = models.ForeignKey(
                    DiscordGuild, on_delete=models.CASCADE,
                    related_name='audits', verbose_name='伺服器')
    changed_by  = models.CharField(max_length=30, verbose_name='修改者 Discord ID')
    changed_at  = models.DateTimeField(auto_now_add=True, verbose_name='修改時間')
    field_name  = models.CharField(max_length=50, verbose_name='欄位名稱')
    old_value   = models.TextField(blank=True, verbose_name='原值')
    new_value   = models.TextField(blank=True, verbose_name='新值')

    class Meta:
        verbose_name = '設定稽核記錄'
        verbose_name_plural = '設定稽核記錄'
        ordering = ['-changed_at']

    def __str__(self):
        return f'[{self.guild.name}] {self.field_name}: {self.old_value}→{self.new_value}'


# ── 頻道 / 身分組快取（Bot 同步，供官網下拉清單）──────────────────────────

CHANNEL_TYPE_CHOICES = [
    ('text', '文字頻道'),
    ('news', '公告頻道'),
    ('forum', '論壇頻道'),
    ('voice', '語音頻道'),
    ('other', '其他'),
]


class GuildChannelCache(models.Model):
    """Bot 同步的頻道清單快取"""
    guild        = models.ForeignKey(
                     DiscordGuild, on_delete=models.CASCADE,
                     related_name='channels', verbose_name='伺服器')
    channel_id   = models.CharField(max_length=30, verbose_name='頻道 ID')
    channel_name = models.CharField(max_length=200, verbose_name='頻道名稱')
    channel_type = models.CharField(
                     max_length=10, choices=CHANNEL_TYPE_CHOICES,
                     default='text', verbose_name='頻道類型')
    position     = models.IntegerField(default=0, verbose_name='排列順序')
    # Bot 實際權限（由 run_discord_bot 同步時以 permissions_for(guild.me) 寫入）
    bot_can_read = models.BooleanField(default=True, verbose_name='Bot 可讀取（view+history）')
    bot_can_send = models.BooleanField(default=True, verbose_name='Bot 可發訊息（send+embed）')
    cached_at    = models.DateTimeField(auto_now=True, verbose_name='快取時間')

    class Meta:
        verbose_name = '頻道快取'
        ordering = ['position']
        unique_together = [('guild', 'channel_id')]

    def __str__(self):
        return f'#{self.channel_name} ({self.channel_type})'


class GuildRoleCache(models.Model):
    """Bot 同步的身分組快取"""
    guild       = models.ForeignKey(
                    DiscordGuild, on_delete=models.CASCADE,
                    related_name='roles', verbose_name='伺服器')
    role_id     = models.CharField(max_length=30, verbose_name='身分組 ID')
    role_name   = models.CharField(max_length=200, verbose_name='身分組名稱')
    role_color  = models.CharField(max_length=10, blank=True, verbose_name='顏色（Hex）')
    position    = models.IntegerField(default=0, verbose_name='排列順序')
    cached_at   = models.DateTimeField(auto_now=True, verbose_name='快取時間')

    class Meta:
        verbose_name = '身分組快取'
        ordering = ['-position']
        unique_together = [('guild', 'role_id')]

    def __str__(self):
        return f'@{self.role_name}'
