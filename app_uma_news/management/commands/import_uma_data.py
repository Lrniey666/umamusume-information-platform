import os
import pandas as pd
from django.core.management.base import BaseCommand
from app_uma_news.models import GameAnnouncement

from django.conf import settings
CSV_PATH = os.path.join(settings.BASE_DIR, 'data', 'uma_news_preprocessed.csv')

CATEGORY_MAP = {
    '活動': '活動', '活动': '活動',
    '卡池': '卡池', '卡池': '卡池',
    '競賽': '競賽', '竞赛': '競賽',
    '系統': '系統', '系统': '系統',
    'event': '活動', 'gacha': '卡池',
    'race': '競賽', 'system': '系統',
}


class Command(BaseCommand):
    help = '將 W12 uma_news_preprocessed.csv 公告資料匯入至資料庫'

    def handle(self, *args, **options):
        if not os.path.exists(CSV_PATH):
            self.stdout.write(self.style.ERROR(f'找不到 CSV 檔案：{CSV_PATH}'))
            return

        df = pd.read_csv(CSV_PATH, sep='|')
        self.stdout.write(f'讀取 CSV 完成，共 {len(df)} 筆資料')

        created, skipped = 0, 0

        for _, row in df.iterrows():
            try:
                link = str(row.get('link', '') or '')
                url = link if link.startswith('http') else None

                # 去重：以 source_url 為唯一鍵（有連結時），或以 title 去重
                if url and GameAnnouncement.objects.filter(source_url=url).exists():
                    skipped += 1
                    continue
                title = str(row.get('title', '') or '')[:255]
                if not url and GameAnnouncement.objects.filter(title=title).exists():
                    skipped += 1
                    continue

                raw_cat = str(row.get('category', '') or '')
                category = CATEGORY_MAP.get(raw_cat, '其他')

                date_val = pd.to_datetime(row.get('date'), errors='coerce')

                GameAnnouncement.objects.create(
                    title          = title,
                    content        = str(row.get('content', '') or ''),
                    category       = category,
                    source_url     = url,
                    published_date = date_val.date() if pd.notna(date_val) else None,
                    source         = 'bilibili',
                )
                created += 1

            except Exception as e:
                self.stdout.write(self.style.WARNING(f'跳過異常列：{e}'))
                continue

        self.stdout.write(self.style.SUCCESS(
            f'完成！已匯入 {created} 筆，跳過 {skipped} 筆（重複）'
        ))
