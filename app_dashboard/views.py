from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.core.paginator import Paginator
from app_uma_news.models import GameAnnouncement

CATEGORIES = ['全部', '活動', '卡池', '競賽', '系統', '其他']
PAGE_SIZE = 24


def dashboard(request):
    return render(request, 'app_dashboard/dashboard.html', {'categories': CATEGORIES})


def announcement_list(request):
    q        = request.GET.get('q', '').strip()
    category = request.GET.get('category', '全部')
    page_num = request.GET.get('page', 1)

    qs = GameAnnouncement.objects.select_related('sentiment').all()
    if q:
        qs = (qs.filter(title__icontains=q) | GameAnnouncement.objects.filter(content__icontains=q)).distinct()
    if category and category != '全部':
        qs = qs.filter(category=category)

    qs = qs.order_by('-published_date', '-created_at')
    total_count = qs.count()
    paginator   = Paginator(qs, PAGE_SIZE)
    page_obj    = paginator.get_page(page_num)

    return render(request, 'app_dashboard/announcement_list.html', {
        'announcements':    page_obj,
        'page_obj':         page_obj,
        'total_count':      total_count,
        'categories':       CATEGORIES,
        'current_category': category,
        'query':            q,
    })


def announcement_detail(request, pk):
    ann      = get_object_or_404(GameAnnouncement, pk=pk)
    comments = ann.comments.order_by('-upvotes')[:30]
    sentiment = getattr(ann, 'sentiment', None)
    if sentiment and sentiment.analyzed_at is None:
        sentiment = None
    return render(request, 'app_dashboard/announcement_detail.html', {
        'announcement': ann,
        'comments': comments,
        'comments_count': ann.comments_count,
        'sentiment': sentiment,
    })


def scheduler_page(request):
    # 排程控制統一移至後台，避免前台誤觸。
    return redirect(reverse('app_crawler_admin:schedule'))
