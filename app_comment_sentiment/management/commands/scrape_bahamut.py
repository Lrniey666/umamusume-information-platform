"""
app_comment_sentiment/management/commands/scrape_bahamut.py

H2（修復版）：從巴哈姆特哈啦板爬取貼文與留言，
    將資料匯入 app_comment_sentiment.Article / Comment 資料表。

使用方式：
    python manage.py scrape_bahamut                # 從 data/raw/bahamut_uma_raw.csv 匯入
    python manage.py scrape_bahamut --crawl         # 先執行爬蟲再匯入
    python manage.py scrape_bahamut --pages 50      # 指定爬取頁數（搭配 --crawl）
    python manage.py scrape_bahamut --csv path/to/custom.csv
    python manage.py scrape_bahamut --fetch-comments  # 同時抓取各文章留言（需連網）
"""
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.utils import timezone

from app_comment_sentiment.models import Article, Comment

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
DEFAULT_CSV = PROJECT_DIR / "data" / "raw" / "bahamut_uma_raw.csv"
CRAWLER_SCRIPT = PROJECT_DIR / "pipeline" / "crawl_bahamut_uma.py"

BSN = "34421"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; UmaBot/1.0)"}

CATEGORY_MAP = {
    "公告": "其他", "情報": "其他", "活動": "活動", "系統": "系統",
    "討論": "其他", "閒聊": "其他", "問題": "其他", "心得": "其他",
    "攻略": "系統", "整理": "其他", "史實": "其他",
    "繪圖": "其他", "繪畫": "其他", "小說": "其他",
    "非洲集中串": "其他", "新馬娘串": "其他", "歐洲集中串": "其他",
}


def normalize_category(raw_cat: str) -> str:
    return CATEGORY_MAP.get(str(raw_cat).strip(), "其他")


def fetch_comments_for_article(url: str, article: Article, stdout=None) -> int:
    """抓取單篇文章的留言（bsn+snA 必填），回傳新增留言數。"""
    if not url or "snA=" not in url:
        return 0
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        added = 0
        for div in soup.select("div.c-reply__item"):
            content_el = div.select_one("div.c-reply__content")
            author_el  = div.select_one("a.reply-author")
            up_el      = div.select_one("span.reply-vote-num")
            down_el    = div.select_one("span.reply-unvote-num")

            content = content_el.get_text(strip=True) if content_el else ""
            if not content:
                continue
            author   = author_el.get_text(strip=True) if author_el else ""
            upvotes  = int(up_el.get_text(strip=True) or 0)   if up_el   else 0
            downvotes= int(down_el.get_text(strip=True) or 0) if down_el else 0

            Comment.objects.get_or_create(
                article=article,
                content=content[:2000],
                defaults={"author": author[:200], "upvotes": upvotes, "downvotes": downvotes},
            )
            added += 1
        return added
    except Exception as e:
        if stdout:
            stdout.write(f"  [warn] 無法抓取留言 {url}: {e}")
        return 0


class Command(BaseCommand):
    help = "從巴哈姆特哈啦板爬取貼文並存入 Article / Comment（H2 完整修復版）"

    def add_arguments(self, parser):
        parser.add_argument(
            "--crawl", action="store_true", default=False,
            help="先執行 crawl_bahamut_uma.py 爬蟲再匯入",
        )
        parser.add_argument(
            "--pages", type=int, default=0,
            help="爬取頁數上限（搭配 --crawl 使用，0 = 無上限）",
        )
        parser.add_argument(
            "--csv", type=str, default=str(DEFAULT_CSV),
            help=f"指定 CSV 路徑（預設：{DEFAULT_CSV}）",
        )
        parser.add_argument(
            "--limit", type=int, default=0,
            help="匯入筆數上限（0 = 全部）",
        )
        parser.add_argument(
            "--fetch-comments", action="store_true", default=False,
            help="對每篇文章抓取留言並存入 Comment（需連網，較慢）",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv"])

        # ── 1. 可選：先執行爬蟲 ─────────────────────────────────
        if options["crawl"]:
            self.stdout.write("爬蟲啟動：crawl_bahamut_uma.py ...")
            if not CRAWLER_SCRIPT.exists():
                self.stderr.write(f"找不到爬蟲腳本：{CRAWLER_SCRIPT}")
                return
            env = os.environ.copy()
            cmd = [sys.executable, str(CRAWLER_SCRIPT)]
            if options["pages"]:
                env["MAX_PAGES"] = str(options["pages"])
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if result.returncode != 0:
                self.stderr.write(f"爬蟲執行失敗：\n{result.stderr}")
                return
            self.stdout.write(self.style.SUCCESS("爬蟲完成"))

        # ── 2. 讀取 CSV ──────────────────────────────────────────
        if not csv_path.exists():
            self.stderr.write(
                f"找不到 CSV 檔案：{csv_path}\n"
                "請先執行爬蟲（--crawl）或確認路徑正確。"
            )
            return

        self.stdout.write(f"讀取：{csv_path}")
        try:
            df = pd.read_csv(csv_path, sep="|", dtype=str, low_memory=False)
        except Exception as e:
            self.stderr.write(f"CSV 讀取失敗：{e}")
            return

        self.stdout.write(f"共 {len(df)} 筆原始資料")

        required_cols = ["item_id", "title", "content"]
        for col in required_cols:
            if col not in df.columns:
                self.stderr.write(f"CSV 缺少必要欄位：{col}")
                return

        if options["limit"] > 0:
            df = df.head(options["limit"])
            self.stdout.write(f"限制匯入前 {len(df)} 筆")

        # ── 3. 逐筆匯入至 Article ────────────────────────────────
        created_count  = 0
        skipped_count  = 0
        error_count    = 0
        comment_count  = 0

        for _, row in df.iterrows():
            link    = str(row.get("link", "")).strip()
            title   = str(row.get("title", "")).strip()
            content = str(row.get("content", "")).strip()

            if not title or title == "nan":
                skipped_count += 1
                continue

            try:
                raw_cat  = str(row.get("category", row.get("raw_category", "其他")))
                category = normalize_category(raw_cat)

                date_str = str(row.get("date", "")).strip()
                pub_date = None
                if date_str and date_str != "nan":
                    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", date_str)
                    if m:
                        pub_date = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

                url = link if link and link != "nan" else f"https://forum.gamer.com.tw/placeholder/{row.get('item_id','')}"

                article, created = Article.objects.get_or_create(
                    url=url,
                    defaults={
                        "title":          title[:500],
                        "content":        content,
                        "category":       category,
                        "published_date": pub_date,
                        "source":         str(row.get("source", "bahamut")).strip() or "bahamut",
                    },
                )

                if created:
                    created_count += 1
                    # 可選：抓取留言
                    if options["fetch_comments"] and "snA=" in url:
                        n = fetch_comments_for_article(url, article, self.stdout)
                        comment_count += n
                else:
                    skipped_count += 1

            except Exception as e:
                error_count += 1
                self.stderr.write(f"  匯入失敗（{title[:30]}）：{e}")

        # ── 4. 結果報告 ──────────────────────────────────────────
        self.stdout.write(
            self.style.SUCCESS(
                f"\n完成！新增 {created_count} 筆 Article"
                f"，跳過重複 {skipped_count} 筆"
                f"，錯誤 {error_count} 筆"
                + (f"，新增留言 {comment_count} 筆" if comment_count else "")
            )
        )
        total = Article.objects.filter(source="bahamut").count()
        self.stdout.write(f"DB 目前 bahamut Article 總計：{total} 筆")
