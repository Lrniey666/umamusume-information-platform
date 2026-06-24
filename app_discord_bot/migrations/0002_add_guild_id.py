"""
為 DiscordMessage 與 DiscordNewsLog 加入 guild_id 欄位，
讓資料可以按伺服器維度統計與篩選。
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app_discord_bot', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='discordmessage',
            name='guild_id',
            field=models.CharField(
                blank=True, db_index=True, max_length=30,
                verbose_name='伺服器 ID', default='',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='discordnewslog',
            name='guild_id',
            field=models.CharField(
                blank=True, db_index=True, max_length=30,
                verbose_name='伺服器 ID', default='',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='discordnewslog',
            name='pinged_role_id',
            field=models.CharField(
                blank=True, max_length=30,
                verbose_name='Ping 的身分組 ID', default='',
            ),
            preserve_default=False,
        ),
    ]
