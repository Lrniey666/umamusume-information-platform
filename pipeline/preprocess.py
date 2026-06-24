"""
T2: 資料前處理（多來源版，Phase 2b DB 化）
P5 修復：移除各來源逐欄補缺失欄位的 patch 邏輯；
        各爬蟲（P1–P3）完成後已輸出統一格式，此處只需合併即可。
Phase 2b 新增：
  - 優先從 NewsData(status='raw') 讀取待處理資料；若 DB 無資料則 fallback 至 CSV
  - 斷詞結果雙輸出：
      1. CSV: data/processed/uma_combined_tokenized.csv（向下相容）
      2. DB:  NewsData bulk_update tokens + status='tokenized'

輸入（優先讀 DB，向下相容舊路徑）:
  - bilibili_uma_raw.csv / bahamut_uma_raw.csv / ettoday_uma_raw.csv
  - udn_uma_raw.csv / gamme_uma_raw.csv

輸出:
  - data/processed/uma_combined_tokenized.csv
"""
import os
import re
import sys
import pandas as pd
from pathlib import Path
from collections import Counter

# ── Django 環境（Phase 2b：雙輸出需要 ORM）─────────────────────
_SCRIPT_DIR = Path(__file__).parent
_ROOT_DIR   = _SCRIPT_DIR.parent
sys.path.insert(0, str(_ROOT_DIR))

from dotenv import load_dotenv
load_dotenv(_ROOT_DIR / '.env')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'website_configs.settings')
import django
django.setup()

from opencc import OpenCC
import jieba
import jieba.posseg as pseg

# ── 路徑設定 ─────────────────────────────────────────────────
RAW_DIR  = _ROOT_DIR / "data" / "raw"
PROC_DIR = _ROOT_DIR / "data" / "processed"
PROC_DIR.mkdir(parents=True, exist_ok=True)

OUT_CSV = PROC_DIR / "uma_combined_tokenized.csv"

# 統一規格欄位（P1–P3 後所有爬蟲均輸出此格式）
CANONICAL_COLS = ['item_id', 'source', 'date', 'category', 'title', 'content', 'link', 'photo_link']

# 各來源 raw CSV 路徑（先找 data/raw/，再向下相容 pipeline/ 目錄）
def _find_raw_csv(source: str) -> Path | None:
    candidates = [
        RAW_DIR / f"{source}_uma_raw.csv",
        _SCRIPT_DIR / f"{source}_uma_raw.csv",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None

RAW_SOURCES = ['bilibili', 'bahamut', 'ettoday', 'udn', 'gamme']

# ── 工具函式 ────────────────────────────────────────────────
cc = OpenCC('s2t')
jieba.setLogLevel('ERROR')

STOP_WORDS = {
    '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都',
    '一', '上', '也', '很', '到', '要', '去', '你', '会', '着',
    '没有', '看', '好', '自己', '这', '那', '与', '及', '或', '等',
    '从', '将', '为', '以', '对', '由', '可以', '并', '其', '而',
    '如', '来', '至', '它', '他', '她', '公', '告', '年', '月',
    '日', '时', '分', '秒',
    '进行', '开始', '结束', '使用', '相关', '详情', '以下', '本次',
    '此次', '期间', '如下', '内容', '活动', '进行中',
}
KEEP_POS = {'n', 'nr', 'ns', 'nt', 'nz', 'ng', 'vn', 'an'}


def is_keep(word: str, pos: str) -> bool:
    return (
        len(word) >= 2
        and word not in STOP_WORDS
        and (pos[:1] == 'n' or pos in ('vn', 'an'))
    )


def tokenize(text: str):
    words_pos       = list(pseg.cut(str(text)))
    tokens_all      = [w.word for w in words_pos if w.word.strip()]
    token_pos       = [(w.word, w.flag) for w in words_pos if w.word.strip()]
    tokens_filtered = [w.word for w in words_pos if is_keep(w.word, w.flag)]
    freq            = Counter(tokens_filtered)
    top_key_freq    = freq.most_common(15)
    return tokens_all, tokens_filtered, token_pos, top_key_freq


# ── 資料讀取 ─────────────────────────────────────────────────
def _load_raw_from_db() -> pd.DataFrame | None:
    """從 NewsData(status='raw') 讀取待處理資料。"""
    try:
        from app_user_keyword_db.models import NewsData
        qs = NewsData.objects.filter(status='raw').values(*CANONICAL_COLS)
        df_db = pd.DataFrame.from_records(list(qs))
        if not df_db.empty:
            df_db['date'] = df_db['date'].astype(str)
            print(f"[preprocess] 從 DB 讀取 {len(df_db)} 筆（status=raw）")
            return df_db
        print("[preprocess] DB 無 status=raw 資料，fallback 至 CSV")
    except Exception as exc:
        print(f"[preprocess] DB 讀取失敗，fallback 至 CSV：{exc}")
    return None


def _load_raw_from_csv() -> pd.DataFrame | None:
    """從各來源 CSV 讀取原始資料。"""
    frames = []
    for src in RAW_SOURCES:
        csv_path = _find_raw_csv(src)
        if csv_path is None:
            print(f"[略過] {src} raw CSV 不存在")
            continue
        print(f"讀取 {src}：{csv_path}")
        try:
            df_src = pd.read_csv(
                csv_path, sep='|', dtype=str, encoding='utf-8-sig',
                engine='python', on_bad_lines='skip',
            )
        except Exception as exc:
            print(f"  [ERROR] 讀取 {src} 失敗，已跳過此來源：{exc}")
            continue
        df_src.columns = [str(c).lstrip('\ufeff').strip() for c in df_src.columns]
        if 'content' not in df_src.columns:
            print(f"  [warn] {src} 無 content 欄位，跳過此來源")
            continue
        df_src = df_src[df_src['content'].fillna('') != '找不到內文'].copy()
        missing = [c for c in CANONICAL_COLS if c not in df_src.columns]
        if missing:
            print(f"  [warn] {src} CSV 缺少欄位：{missing}，自動補空字串")
            for c in missing:
                df_src[c] = src if c == 'source' else ''
        df_src['source'] = df_src['source'].fillna(src).replace('', src)
        print(f"  有效筆數：{len(df_src)}")
        frames.append(df_src[CANONICAL_COLS])
    if not frames:
        return None
    df = pd.concat(frames, ignore_index=True)
    return df


# ── DB 回寫 ──────────────────────────────────────────────────
def _write_tokens_to_db(df: pd.DataFrame) -> None:
    """將斷詞結果 bulk_update 至 NewsData，status 改為 'tokenized'。"""
    try:
        from app_user_keyword_db.models import NewsData
        item_ids = df['item_id'].tolist()
        existing = {
            obj.item_id: obj
            for obj in NewsData.objects.filter(item_id__in=item_ids)
        }
        to_update = []
        for _, row in df.iterrows():
            iid = str(row.get('item_id', ''))
            obj = existing.get(iid)
            if obj is None:
                continue
            obj.tokens_filtered = str(row.get('tokens_filtered', ''))
            obj.token_pos        = str(row.get('token_pos', ''))
            obj.top_key_freq     = str(row.get('top_key_freq', ''))
            obj.status           = 'tokenized'
            to_update.append(obj)

        if to_update:
            NewsData.objects.bulk_update(
                to_update,
                ['tokens_filtered', 'token_pos', 'top_key_freq', 'status'],
                batch_size=500,
            )
            print(f"[preprocess] DB bulk_update {len(to_update)} 筆 → status=tokenized")
        else:
            print("[preprocess] DB 中無對應 item_id，跳過 DB 更新")
    except Exception as exc:
        print(f"[preprocess] DB 回寫失敗（CSV 仍已正常寫出）：{exc}")


# ── 主流程 ───────────────────────────────────────────────────
def main():
    # 1. 讀取資料
    df = _load_raw_from_db()
    if df is None:
        df = _load_raw_from_csv()
    if df is None or df.empty:
        print("[ERROR] 沒有任何可用的原始資料，請先執行各爬蟲腳本")
        return

    # ── 合併 + 去重 ──────────────────────────────────────────
    df = df[
        df['content'].notna() &
        (df['content'] != '找不到內文') &
        (df['content'].str.len() > 3)
    ].copy()

    df_with_link    = df[df['link'].fillna('').str.len() > 0].drop_duplicates(subset='link', keep='first')
    df_without_link = df[df['link'].fillna('').str.len() == 0].copy()
    df = pd.concat([df_with_link, df_without_link], ignore_index=True).reset_index(drop=True)

    print(f"\n合併去重後有效筆數：{len(df)}")
    print(f"各來源：{df['source'].value_counts().to_dict()}")
    print(f"各類別：{df['category'].value_counts().to_dict()}")

    # ── P5：日期容錯補丁 ──────────────────────────────────────
    def safe_date(raw: str) -> str:
        m = re.search(r'(\d{4})[-/](\d{2})[-/](\d{2})', str(raw))
        if m:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        return '2024-01-01'

    df['date'] = df['date'].apply(safe_date)
    print(f"日期 fallback 筆數：{(df['date'] == '2024-01-01').sum()}")

    # ── P5：OpenCC content 簡→繁 ─────────────────────────────
    print("OpenCC content 轉換中...")
    df['content'] = df['content'].apply(lambda x: cc.convert(str(x)) if pd.notna(x) else x)

    # ── jieba 斷詞 ────────────────────────────────────────────
    print("jieba 斷詞中（請稍候）...")
    tokens_all_list, tokens_filt_list, token_pos_list, top_kf_list = [], [], [], []
    for i, row in df.iterrows():
        ta, tf, tp, tkf = tokenize(row['content'])
        tokens_all_list.append(ta)
        tokens_filt_list.append(tf)
        token_pos_list.append(tp)
        top_kf_list.append(tkf)
        if (i + 1) % 50 == 0:
            print(f"  已處理 {i+1}/{len(df)}")

    df['tokens']          = tokens_all_list
    df['tokens_filtered'] = tokens_filt_list
    df['token_pos']       = token_pos_list
    df['top_key_freq']    = top_kf_list
    df['tokens_v2']       = tokens_filt_list

    # ── 驗收 ─────────────────────────────────────────────────
    empty_filter = (df['tokens_filtered'].apply(len) < 5).sum()
    print(f"\n驗收：tokens_filtered < 5 詞的篇數：{empty_filter}")
    for src in RAW_SOURCES:
        cnt = (df['source'] == src).sum()
        print(f"  {src}：{cnt} 筆")

    # ── 1. 寫 CSV（向下相容）─────────────────────────────────
    df.to_csv(OUT_CSV, sep='|', index=False)
    print(f"\n[OK] CSV 寫入 {OUT_CSV}，共 {len(df)} 筆")

    # ── 2. DB bulk_update status='tokenized'（Phase 2b）───────
    _write_tokens_to_db(df)


if __name__ == "__main__":
    main()
