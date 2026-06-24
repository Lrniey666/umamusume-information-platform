from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        # ── DiscordUser ──────────────────────────────────────────────────
        migrations.CreateModel(
            name='DiscordUser',
            fields=[
                ('id',               models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('discord_id',       models.CharField(max_length=30, unique=True, verbose_name='Discord ID')),
                ('username',         models.CharField(max_length=200, verbose_name='顯示名稱')),
                ('avatar_hash',      models.CharField(blank=True, max_length=100, verbose_name='頭像 Hash')),
                ('access_token_enc', models.TextField(blank=True, verbose_name='Access Token（加密）')),
                ('refresh_token_enc',models.TextField(blank=True, verbose_name='Refresh Token（加密）')),
                ('token_expires_at', models.DateTimeField(blank=True, null=True, verbose_name='Token 到期')),
                ('last_login_at',    models.DateTimeField(auto_now=True, verbose_name='最後登入')),
                ('created_at',       models.DateTimeField(auto_now_add=True)),
            ],
            options={'verbose_name': 'Discord 用戶', 'verbose_name_plural': 'Discord 用戶'},
        ),

        # ── DiscordGuild ─────────────────────────────────────────────────
        migrations.CreateModel(
            name='DiscordGuild',
            fields=[
                ('id',           models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('guild_id',     models.CharField(max_length=30, unique=True, verbose_name='伺服器 ID')),
                ('name',         models.CharField(max_length=200, verbose_name='伺服器名稱')),
                ('icon_hash',    models.CharField(blank=True, max_length=100, verbose_name='圖示 Hash')),
                ('joined_at',    models.DateTimeField(blank=True, null=True, verbose_name='Bot 加入時間')),
                ('is_bot_present', models.BooleanField(default=False, verbose_name='Bot 在線中')),
                ('member_count', models.IntegerField(default=0, verbose_name='成員數')),
                ('created_at',   models.DateTimeField(auto_now_add=True)),
            ],
            options={'verbose_name': 'Discord 伺服器', 'verbose_name_plural': 'Discord 伺服器', 'ordering': ['name']},
        ),

        # ── GuildSetting ─────────────────────────────────────────────────
        migrations.CreateModel(
            name='GuildSetting',
            fields=[
                ('id',               models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('guild',            models.OneToOneField(
                                         on_delete=django.db.models.deletion.CASCADE,
                                         related_name='setting',
                                         to='app_uma_info_portal.discordguild',
                                         verbose_name='伺服器')),
                ('read_scope',       models.CharField(
                                         choices=[('all','全部頻道（預設）'),('announcements','僅公告頻道'),
                                                  ('single','僅單一頻道'),('advanced','進階設定（Allow/Deny 清單）')],
                                         default='all', max_length=20, verbose_name='讀取範圍')),
                ('single_channel_id',models.CharField(blank=True, max_length=30, verbose_name='指定單一頻道 ID')),
                ('news_channel_id',  models.CharField(blank=True, max_length=30, verbose_name='推播頻道 ID')),
                ('ping_role_id',     models.CharField(blank=True, max_length=30, verbose_name='Ping 身分組 ID')),
                ('news_enabled',     models.BooleanField(default=True, verbose_name='啟用推播')),
                ('news_frequency',   models.CharField(
                                         choices=[('daily','每日'),('weekly','每週'),('off','關閉')],
                                         default='daily', max_length=10, verbose_name='推播頻率')),
                ('news_hour',        models.IntegerField(default=20, verbose_name='推播時間（整點，台北）')),
                ('news_tone',        models.CharField(
                                         choices=[('lively','活潑（適合社群）'),('concise','簡潔（資訊為主）')],
                                         default='lively', max_length=10, verbose_name='摘要語氣')),
                ('ai_chat_enabled',  models.BooleanField(default=True, verbose_name='啟用 AI 問答')),
                ('ai_daily_quota',   models.IntegerField(default=100, verbose_name='每日 AI 問答上限')),
                ('updated_by',       models.CharField(blank=True, max_length=30, verbose_name='最後修改者')),
                ('updated_at',       models.DateTimeField(auto_now=True, verbose_name='最後修改時間')),
            ],
            options={'verbose_name': '伺服器設定', 'verbose_name_plural': '伺服器設定'},
        ),

        # ── GuildChannelRule ──────────────────────────────────────────────
        migrations.CreateModel(
            name='GuildChannelRule',
            fields=[
                ('id',           models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('guild',        models.ForeignKey(
                                     on_delete=django.db.models.deletion.CASCADE,
                                     related_name='channel_rules',
                                     to='app_uma_info_portal.discordguild',
                                     verbose_name='伺服器')),
                ('channel_id',   models.CharField(max_length=30, verbose_name='頻道 ID')),
                ('channel_name', models.CharField(blank=True, max_length=200, verbose_name='頻道名稱')),
                ('rule_type',    models.CharField(choices=[('allow','允許'),('deny','排除')], max_length=5, verbose_name='規則類型')),
                ('note',         models.CharField(blank=True, max_length=200, verbose_name='備注')),
            ],
            options={'verbose_name': '頻道規則', 'verbose_name_plural': '頻道規則'},
        ),
        migrations.AddConstraint(
            model_name='guildchannelrule',
            constraint=models.UniqueConstraint(fields=['guild', 'channel_id'], name='unique_guild_channel_rule'),
        ),

        # ── GuildSettingAudit ─────────────────────────────────────────────
        migrations.CreateModel(
            name='GuildSettingAudit',
            fields=[
                ('id',          models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('guild',       models.ForeignKey(
                                    on_delete=django.db.models.deletion.CASCADE,
                                    related_name='audits',
                                    to='app_uma_info_portal.discordguild',
                                    verbose_name='伺服器')),
                ('changed_by',  models.CharField(max_length=30, verbose_name='修改者 Discord ID')),
                ('changed_at',  models.DateTimeField(auto_now_add=True, verbose_name='修改時間')),
                ('field_name',  models.CharField(max_length=50, verbose_name='欄位名稱')),
                ('old_value',   models.TextField(blank=True, verbose_name='原值')),
                ('new_value',   models.TextField(blank=True, verbose_name='新值')),
            ],
            options={'verbose_name': '設定稽核記錄', 'verbose_name_plural': '設定稽核記錄', 'ordering': ['-changed_at']},
        ),

        # ── GuildChannelCache ─────────────────────────────────────────────
        migrations.CreateModel(
            name='GuildChannelCache',
            fields=[
                ('id',           models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('guild',        models.ForeignKey(
                                     on_delete=django.db.models.deletion.CASCADE,
                                     related_name='channels',
                                     to='app_uma_info_portal.discordguild',
                                     verbose_name='伺服器')),
                ('channel_id',   models.CharField(max_length=30, verbose_name='頻道 ID')),
                ('channel_name', models.CharField(max_length=200, verbose_name='頻道名稱')),
                ('channel_type', models.CharField(
                                     choices=[('text','文字頻道'),('news','公告頻道'),('forum','論壇頻道'),
                                              ('voice','語音頻道'),('other','其他')],
                                     default='text', max_length=10, verbose_name='頻道類型')),
                ('position',     models.IntegerField(default=0, verbose_name='排列順序')),
                ('cached_at',    models.DateTimeField(auto_now=True, verbose_name='快取時間')),
            ],
            options={'verbose_name': '頻道快取', 'ordering': ['position']},
        ),
        migrations.AddConstraint(
            model_name='guildchannelcache',
            constraint=models.UniqueConstraint(fields=['guild', 'channel_id'], name='unique_guild_channel_cache'),
        ),

        # ── GuildRoleCache ────────────────────────────────────────────────
        migrations.CreateModel(
            name='GuildRoleCache',
            fields=[
                ('id',         models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('guild',      models.ForeignKey(
                                   on_delete=django.db.models.deletion.CASCADE,
                                   related_name='roles',
                                   to='app_uma_info_portal.discordguild',
                                   verbose_name='伺服器')),
                ('role_id',    models.CharField(max_length=30, verbose_name='身分組 ID')),
                ('role_name',  models.CharField(max_length=200, verbose_name='身分組名稱')),
                ('role_color', models.CharField(blank=True, max_length=10, verbose_name='顏色（Hex）')),
                ('position',   models.IntegerField(default=0, verbose_name='排列順序')),
                ('cached_at',  models.DateTimeField(auto_now=True, verbose_name='快取時間')),
            ],
            options={'verbose_name': '身分組快取', 'ordering': ['-position']},
        ),
        migrations.AddConstraint(
            model_name='guildrolecache',
            constraint=models.UniqueConstraint(fields=['guild', 'role_id'], name='unique_guild_role_cache'),
        ),
    ]
