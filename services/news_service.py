"""
services/news_service.py

⚠️  廢棄通知（Phase 4）
此模組在 DB 化完成後將逐步廢棄（計畫 v0.5.x）：
- NEWS_CSV / load_news_df()   → 改用 NewsData.objects.filter(status='labeled')
- TOPKEY_CSV                  → 改用 TopKeyword.objects.filter(window_days=0)
- TOP_CHARACTER_CSV           → 改用 TopCharacter.objects.filter(window_days=0)
- CHARACTERS_CSV              → 改用 UmaCharacter.objects.all()
- PK_CSV                      → 暫保留（CharacterVoteResult 模型評估中）

在此過渡期間，本模組仍然可用，並作為 CSV fallback 使用。
新程式碼不應再依賴此模組讀取主要資料。

集中管理 data/processed/ 內各 CSV 的路徑與共用載入邏輯。
資料流：
  pipeline/crawl_*.py   → data/raw/ + NewsData DB（Phase 2c 後）
  pipeline/preprocess.py + label_sentiment.py → data/processed/ + NewsData DB（Phase 2b 後）
  scripts/generate_*.py → data/processed/ + TopKeyword/TopCharacter DB（Phase 2b 後）
"""

import os
import warnings
import pandas as pd

# 專案根目錄（此檔在 services/，往上一層即為根目錄）
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROCESSED = os.path.join(_ROOT, 'data', 'processed')


def _p(filename: str) -> str:
    """回傳 data/processed/<filename> 的絕對路徑。"""
    return os.path.join(_PROCESSED, filename)


# ── 各 CSV 的絕對路徑常數 ──────────────────────────────────────────
NEWS_CSV           = _p('uma_news_preprocessed.csv')      # 主要新聞 / 公告資料
CHARACTERS_CSV     = _p('uma_characters_bilingual.csv')   # 角色雙語名稱
PK_CSV             = _p('pk_uma_characters.csv')          # 角色人氣 PK 資料
TOPKEY_CSV         = _p('uma_topkey_with_category.csv')   # 各分類熱門關鍵字
TOP_CHARACTER_CSV  = _p('uma_top_character_with_category.csv')  # 各分類熱門角色


# ── 新聞 DataFrame 快取 ───────────────────────────────────────────
_news_df: 'pd.DataFrame | None' = None


def load_news_df(force_reload: bool = False) -> pd.DataFrame:
    """
    回傳處理後的新聞 DataFrame，第一次呼叫時從 NEWS_CSV 讀取並快取。

    ⚠️  廢棄通知：Phase 3 完成後，請改用
        NewsData.objects.filter(status='labeled')
        app_user_keyword/views.py 已自動優先讀 DB，此函式僅作 fallback。

    Args:
        force_reload: True 時強制重新讀取。

    Returns:
        pd.DataFrame: 新聞資料表。

    Raises:
        FileNotFoundError: 若 NEWS_CSV 不存在。
    """
    global _news_df
    if _news_df is None or force_reload:
        if not os.path.exists(NEWS_CSV):
            raise FileNotFoundError(
                f"找不到新聞資料：{NEWS_CSV}\n"
                "請先執行 pipeline/ 下的爬蟲與前處理腳本，"
                "或確認 data/processed/ 目錄是否存在。"
            )
        _news_df = pd.read_csv(NEWS_CSV, sep='|')
    return _news_df
