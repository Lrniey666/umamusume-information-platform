from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include, re_path
from django.views.generic.base import RedirectView
from app_user_keyword_db.views import api_source_stats

urlpatterns = [
    # ── 首頁：角色人氣 PK ──
    path('',                    include('app_character_pk.urls')),

    # ── 主線分析 Apps（w12）──
    path('userkeyword/',        include('app_user_keyword.urls')),
    path('userkeyword_assoc/',  include('app_user_keyword_association.urls')),
    path('userkeyword_senti/',  include('app_user_keyword_sentiment.urls')),
    path('userkeyword_db/',     include('app_user_keyword_db.urls')),
    path('userkeyword_report/', include('app_user_keyword_llm_report.urls')),
    path('uma_top_keyword/',    include('app_uma_top_keyword.urls')),
    path('uma_top_character/',  include('app_uma_top_character.urls')),
    path('api/source_stats/',   api_source_stats, name='api_source_stats'),
    path('crawler-admin/',      include('app_crawler_admin.urls')),
    path('control/',            RedirectView.as_view(url='/crawler-admin/', permanent=False)),
    re_path(r'^control/(?P<path>.*)$', RedirectView.as_view(url='/crawler-admin/%(path)s', permanent=False)),

    # ── Feature Apps：留言情緒儀表板（w13）──
    path('dashboard/',          include('app_dashboard.urls')),
    path('api/',                include('app_dashboard.urls_api')),
    path('comment_sentiment/',  include('app_comment_sentiment.urls')),  # C1 修復：補儀表板路由

    # ── 進階 AI Apps（w16）──
    path('agent/',              include('app_agent_uma.urls')),
    path('rag/',                include('app_rag_uma.urls')),

    # ── 介紹頁 ──
    path('introduction/',       include('app_poa_introduction.urls')),

    # ── 關聯分析（選用）──
    path('correlation/',        include('app_correlation_analysis.urls')),

    # ── 進階 AI Apps（w17）──
    path('rag-agent/',          include('app_rag_agent.urls')),
    path('course/',             include('app_course_intro.urls')),

    # ── LangChain / LangGraph Agents（O2/O3）──
    path('langchain-agent/',    include('app_agent_langchain.urls')),
    path('langgraph-agent/',    include('app_agent_langgraph.urls')),

    # ── YouTube 影片情感（O5）──
    path('youtube/',            include('app_youtube_uma.urls')),

    # ── Discord Bot（D1-D8）──
    path('discord/',            include('app_discord_bot.urls')),

    # ── UMA Info 官網 Portal（U1-U16）──
    path('uma-info/',           include('app_uma_info_portal.urls')),

    # ── Django Admin ──
    path('admin/',              admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
