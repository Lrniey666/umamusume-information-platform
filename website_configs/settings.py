import os
import json
from dotenv import load_dotenv
from pathlib import Path

# 明確指定專案根目錄的 .env，避免被父層目錄的 .env 覆蓋
_ENV_FILE = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(_ENV_FILE, override=True)

BASE_DIR = Path(__file__).resolve().parent.parent

# ─────────────────────────────────────
# 安全設定
# ─────────────────────────────────────
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'ij^*zz$7bd!#2&dhq_&5y+36@=&*8+m0nil9f2q8@_wu8q4$9w')

DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS_STR = os.getenv('DJANGO_ALLOWED_HOSTS', '*')
ALLOWED_HOSTS = [h.strip() for h in ALLOWED_HOSTS_STR.split(',')]

# ─────────────────────────────────────
# 已安裝應用程式
# ─────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 第三方
    'corsheaders',
    'django_apscheduler',
    # ── 主線 Apps（from w12）──
    'app_character_pk',
    'app_user_keyword',
    'app_user_keyword_association',
    'app_user_keyword_sentiment',
    'app_user_keyword_db',
    'app_user_keyword_llm_report',
    'app_uma_top_keyword',
    'app_uma_top_character',
    'app_crawler_admin',
    # ── Feature Apps（from w13）──
    'app_uma_news',
    'app_uma_comments',
    'app_comment_sentiment',
    'app_dashboard',
    # ── 進階 AI Apps（from w16）──
    'app_agent_uma',
    'app_rag_uma',
    # ── 介紹頁 ──
    'app_poa_introduction',
    # ── 選用（關聯分析）──
    'app_correlation_analysis',
    # ── 進階 AI Apps（w17）──
    'app_rag_agent',
    'app_course_intro',
    # ── LangChain / LangGraph Agents（O2/O3）──
    'app_agent_langchain',
    'app_agent_langgraph',
    # ── YouTube 影片情感（O5）──
    'app_youtube_uma',
    # ── Discord Bot ──
    'app_discord_bot',
    # ── UMA Info 官網 Portal ──
    'app_uma_info_portal',
]

# ─────────────────────────────────────
# 中介層
# ─────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # 靜態檔案（非 Docker 時可用）
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'website_configs.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'website_configs.wsgi.application'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─────────────────────────────────────
# 資料庫
#   預設 PostgreSQL（Docker 正式部署，支援多進程並發寫入）；
#   未設定 DJANGO_DB_ENGINE=postgres 時 fallback 至 SQLite（本機開發）。
# ─────────────────────────────────────
_DB_ENGINE = os.getenv('DJANGO_DB_ENGINE', 'sqlite').lower()

if _DB_ENGINE in ('postgres', 'postgresql', 'psql'):
    DATABASES = {
        'default': {
            'ENGINE':   'django.db.backends.postgresql',
            'NAME':     os.getenv('POSTGRES_DB', 'umamusume'),
            'USER':     os.getenv('POSTGRES_USER', 'postgres'),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'postgres'),
            'HOST':     os.getenv('POSTGRES_HOST', 'db'),
            'PORT':     os.getenv('POSTGRES_PORT', '5432'),
            'CONN_MAX_AGE': int(os.getenv('DJANGO_DB_CONN_MAX_AGE', '60')),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ─────────────────────────────────────
# 密碼驗證
# ─────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ─────────────────────────────────────
# 國際化
# ─────────────────────────────────────
LANGUAGE_CODE = 'zh-hant'
TIME_ZONE = 'Asia/Taipei'
USE_I18N = True
USE_TZ = True

# ─────────────────────────────────────
# 靜態檔案
# ─────────────────────────────────────
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# WhiteNoise 壓縮（開發用）
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ─────────────────────────────────────
# Session（Agentic AI 對話歷史用）
# ─────────────────────────────────────
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 86400  # 24 小時（Portal OAuth 登入需要更長 session）

# ─────────────────────────────────────
# CORS
# ─────────────────────────────────────
CORS_ORIGIN_ALLOW_ALL = True

# ─────────────────────────────────────
# APScheduler（django-apscheduler）
# ─────────────────────────────────────
APSCHEDULER_DATETIME_FORMAT = "N j, Y, f:s a"
APSCHEDULER_RUN_NOW_TIMEOUT = 25  # 秒

# ─────────────────────────────────────
# 日誌設定
# ─────────────────────────────────────
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'django_file': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': LOGS_DIR / 'django.log',
            'when': 'midnight',
            'backupCount': 14,
            'encoding': 'utf-8',
            'formatter': 'verbose',
        },
        'error_file': {
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': LOGS_DIR / 'error.log',
            'when': 'midnight',
            'backupCount': 30,
            'encoding': 'utf-8',
            'formatter': 'verbose',
            'level': 'ERROR',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'django_file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'django_file', 'error_file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['error_file'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

# ─────────────────────────────────────
# AI API 金鑰（從 .env 讀取）
# ─────────────────────────────────────
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
GEMINI_IMAGE_MODEL = os.getenv('GEMINI_IMAGE_MODEL', 'gemini-3.1-flash-image')

AI_NEWS_DEFAULT_TEXT_MODEL = os.getenv('AI_NEWS_DEFAULT_TEXT_MODEL', 'gemini_35_flash')
_ai_news_models_env = os.getenv('AI_NEWS_TEXT_MODELS', '').strip()
if _ai_news_models_env:
    try:
        _parsed = json.loads(_ai_news_models_env)
        AI_NEWS_TEXT_MODELS = _parsed if isinstance(_parsed, list) else []
    except Exception:
        AI_NEWS_TEXT_MODELS = []
else:
    AI_NEWS_TEXT_MODELS = []

# ─────────────────────────────────────
# Discord OAuth2（UMA Info Portal 用）
# ─────────────────────────────────────
DISCORD_CLIENT_ID     = os.getenv('DISCORD_CLIENT_ID', '')
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET', '')
DISCORD_OAUTH_REDIRECT = os.getenv(
    'DISCORD_OAUTH_REDIRECT',
    'http://localhost:8000/uma-info/auth/callback/'
)

# UMA Info AI 問答模型（最便宜的 Gemini）
UMA_CHAT_MODEL = os.getenv('UMA_CHAT_MODEL', 'gemini-3.5-flash')
