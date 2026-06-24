from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='CrawlerRun',
            fields=[
                ('run_id',        models.CharField(max_length=64, primary_key=True, serialize=False, default=lambda: uuid.uuid4().hex)),
                ('source',        models.CharField(max_length=20, choices=[('bilibili','bilibili'),('bahamut','bahamut'),('udn','udn'),('ettoday','ettoday'),('gamme','gamme')])),
                ('status',        models.CharField(max_length=20, default='running', choices=[('running','運行中'),('success','成功'),('failed','失敗'),('cancelled','已取消')])),
                ('triggered_by',  models.CharField(max_length=20, default='manual', choices=[('manual','手動觸發'),('schedule','排程觸發')])),
                ('started_at',    models.DateTimeField(auto_now_add=True)),
                ('ended_at',      models.DateTimeField(null=True, blank=True)),
                ('articles_new',  models.IntegerField(default=0)),
                ('articles_skip', models.IntegerField(default=0)),
                ('articles_err',  models.IntegerField(default=0)),
                ('log_text',      models.TextField(blank=True, default='')),
            ],
            options={'app_label': 'app_crawler_admin', 'ordering': ['-started_at']},
        ),
        migrations.CreateModel(
            name='CrawlerSchedule',
            fields=[
                ('id',         models.BigAutoField(primary_key=True, serialize=False)),
                ('source',     models.CharField(max_length=20, unique=True, choices=[('bilibili','bilibili'),('bahamut','bahamut'),('udn','udn'),('ettoday','ettoday'),('gamme','gamme')])),
                ('mode',       models.CharField(max_length=20, default='daily', choices=[('daily','每日'),('weekly','每週'),('interval','固定間隔')])),
                ('cron_expr',  models.CharField(max_length=60, default='0 2 * * *')),
                ('enabled',    models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'app_label': 'app_crawler_admin'},
        ),
        migrations.CreateModel(
            name='CrawlerConfig',
            fields=[
                ('id',             models.BigAutoField(primary_key=True, serialize=False)),
                ('source',         models.CharField(max_length=20, unique=True, choices=[('bilibili','bilibili'),('bahamut','bahamut'),('udn','udn'),('ettoday','ettoday'),('gamme','gamme')])),
                ('max_pages',      models.IntegerField(default=50)),
                ('delay_min',      models.FloatField(default=0.8)),
                ('delay_max',      models.FloatField(default=1.5)),
                ('use_playwright', models.BooleanField(default=False)),
                ('user_agent',     models.TextField(blank=True, default='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')),
                ('extra_notes',    models.TextField(blank=True, default='')),
            ],
            options={'app_label': 'app_crawler_admin'},
        ),
    ]
