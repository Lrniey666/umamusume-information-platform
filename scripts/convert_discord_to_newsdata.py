"""
scripts/convert_discord_to_newsdata.py

將 DiscordMessage（is_umamusume=True，尚未轉換）增量寫入 NewsData。
可獨立執行，也可由 Pipeline Step 6 呼叫。

用法：
    python scripts/convert_discord_to_newsdata.py
"""
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
os.chdir(ROOT_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website_configs.settings')
django.setup()

from app_discord_bot.converter import convert_discord_to_newsdata
from app_user_keyword_db.models import NewsData


def main():
    before = NewsData.objects.filter(source='discord').count()
    created = convert_discord_to_newsdata()
    after = NewsData.objects.filter(source='discord').count()
    print(f"[INFO] Discord 來源：匯入前 {before} 筆 → 匯入後 {after} 筆（新增 {created} 筆）")
    print(f"Done.")


if __name__ == '__main__':
    main()
