from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='GeneratedNewsArticle',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('query', models.CharField(max_length=200)),
                ('category', models.CharField(default='全部', max_length=50)),
                ('source', models.CharField(default='all', max_length=20)),
                ('weeks', models.PositiveSmallIntegerField(default=4)),
                ('topk', models.PositiveSmallIntegerField(default=8)),
                ('title', models.CharField(max_length=220)),
                ('subtitle', models.CharField(blank=True, max_length=320)),
                ('content', models.TextField()),
                ('summary', models.TextField(blank=True)),
                ('cover_image_url', models.URLField(blank=True, max_length=600)),
                ('source_chunks', models.JSONField(blank=True, default=list)),
                ('source_links', models.JSONField(blank=True, default=list)),
                ('status', models.CharField(choices=[('draft', '草稿'), ('published', '已發布')], default='published', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'AI 生成新聞',
                'verbose_name_plural': 'AI 生成新聞',
                'ordering': ['-created_at'],
            },
        ),
    ]
