"""
app_discord_bot/views.py

Discord Bot 狀態儀表板 + 頻道設定管理 API。
"""
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import DiscordMessage, DiscordBotConfig, DiscordNewsLog


def dashboard(request):
    """Discord Bot 狀態總覽"""
    total_messages = DiscordMessage.objects.count()
    umamusume_count = DiscordMessage.objects.filter(is_umamusume=True).count()
    unclassified_count = DiscordMessage.objects.filter(is_umamusume=None).count()
    all_configs = DiscordBotConfig.objects.all().order_by('channel_type', 'name')
    recent_logs = DiscordNewsLog.objects.order_by('-created_at')[:5]

    return render(request, 'app_discord_bot/dashboard.html', {
        'total_messages': total_messages,
        'umamusume_count': umamusume_count,
        'unclassified_count': unclassified_count,
        'configs': all_configs,
        'recent_logs': recent_logs,
    })


def api_stats(request):
    """JSON API — Discord Bot 統計數據"""
    from django.utils import timezone
    today = timezone.now().date()
    return JsonResponse({
        'total_messages': DiscordMessage.objects.count(),
        'umamusume_messages': DiscordMessage.objects.filter(is_umamusume=True).count(),
        'unclassified': DiscordMessage.objects.filter(is_umamusume=None).count(),
        'active_configs': DiscordBotConfig.objects.filter(is_active=True).count(),
        'news_logs': DiscordNewsLog.objects.count(),
        'news_today': DiscordNewsLog.objects.filter(created_at__date=today, status='sent').count(),
    })


def api_trigger_news(request):
    """手動觸發 Discord 新聞生成推播（非同步）"""
    if request.method != 'POST':
        return JsonResponse({'error': '只支援 POST'}, status=405)
    import subprocess, sys
    from django.conf import settings as django_settings
    from pathlib import Path
    try:
        script = Path(django_settings.BASE_DIR) / 'app_discord_bot' / 'news_generator.py'
        if script.exists():
            subprocess.Popen(
                [sys.executable, str(script)],
                cwd=str(django_settings.BASE_DIR),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return JsonResponse({'status': 'started'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
def api_channel_add(request):
    """新增或更新頻道設定"""
    import json
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': '無效的 JSON 格式'}, status=400)

    channel_id = (data.get('channel_id') or '').strip()
    name = (data.get('name') or '').strip()
    channel_type = (data.get('channel_type') or '').strip()
    is_active = data.get('is_active', True)
    note = (data.get('note') or '').strip()

    if not channel_id or not channel_id.isdigit():
        return JsonResponse({'error': '頻道 ID 必須為純數字'}, status=400)
    if channel_type not in ('crawl', 'news'):
        return JsonResponse({'error': '頻道類型必須為 crawl 或 news'}, status=400)
    if not name:
        return JsonResponse({'error': '名稱不可為空'}, status=400)

    obj, created = DiscordBotConfig.objects.update_or_create(
        channel_id=channel_id,
        defaults={
            'name': name,
            'channel_type': channel_type,
            'is_active': bool(is_active),
            'note': note,
        }
    )
    return JsonResponse({
        'status': 'created' if created else 'updated',
        'id': obj.pk,
        'channel_id': obj.channel_id,
        'name': obj.name,
        'channel_type': obj.channel_type,
        'is_active': obj.is_active,
    })


@require_POST
def api_channel_delete(request, pk):
    """刪除指定頻道設定"""
    cfg = get_object_or_404(DiscordBotConfig, pk=pk)
    cfg.delete()
    return JsonResponse({'status': 'deleted', 'id': pk})


@require_POST
def api_channel_toggle(request, pk):
    """切換頻道啟用／停用狀態"""
    cfg = get_object_or_404(DiscordBotConfig, pk=pk)
    cfg.is_active = not cfg.is_active
    cfg.save(update_fields=['is_active'])
    return JsonResponse({'status': 'ok', 'is_active': cfg.is_active})
