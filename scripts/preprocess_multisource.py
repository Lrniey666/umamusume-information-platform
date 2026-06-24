"""
scripts/preprocess_multisource.py
對 ettoday/bahamut 原始 CSV 做最小前處理（jieba 斷詞 + 情感打分），
再合併進 uma_news_preprocessed.csv，讓聲量/情感分析 app 支援多來源篩選。

用法：
    python scripts/preprocess_multisource.py
"""
import os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import pandas as pd
import jieba
import jieba.posseg as pseg

jieba.setLogLevel('ERROR')

# ── 路徑設定 ──────────────────────────────────────────────────
W12_RAW = (
    ROOT / '參考專案' / 'w12'
    / 'w12-5-HW@w12-呼叫線上GeminiOpenAI-AI生成你自己的分析報告'
    / 'umamusume-llm-report' / 'data' / 'raw'
)
PROCESSED_CSV = ROOT / 'data' / 'processed' / 'uma_news_preprocessed.csv'

SOURCES_RAW = {
    'ettoday': W12_RAW / 'ettoday_uma_raw.csv',
    'bahamut': W12_RAW / 'bahamut_uma_raw.csv',
}

# ── 停用詞（簡易版）─────────────────────────────────────────
STOP = set('的了在是我有和就不都很為以與及或等從將對由這那他她它一二三四五六七八九十個也'.split())

# ── 情感詞典（極簡版，僅做展示用）─────────────────────────
POS_WORDS = {'好', '優秀', '強', '厲害', '可愛', '帥氣', '期待', '歡迎', '新增', '活動', '獎勵', '限定', '免費', '感謝', '更新', '改善'}
NEG_WORDS = {'壞', '弱', '難', '失望', '錯誤', '問題', '故障', '延遲', '取消', '刪除', '降低', '減少', '封號', '禁止'}


def clean_date(val) -> str | None:
    if not val or pd.isna(val):
        return None
    val = str(val).strip()
    val = re.sub(r'[^\d\-/].*', '', val).strip()
    for fmt in ('%Y-%m-%d', '%Y/%m/%d'):
        try:
            from datetime import datetime
            return datetime.strptime(val[:10], fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None


def tokenize(text: str) -> tuple[str, str, str]:
    """回傳 (tokens_filtered, token_pos, top_key_freq)"""
    if not text or not isinstance(text, str):
        return '', '', ''

    keep_pos = {'n', 'nr', 'ns', 'nt', 'nz', 'ng', 'vn', 'an', 'a', 'v'}
    words_pos = []
    filtered  = []

    for w in pseg.cut(text[:2000]):
        word = w.word.strip()
        if len(word) < 2 or word in STOP:
            continue
        words_pos.append(f'{word}/{w.flag}')
        if w.flag[:1] in ('n', 'v', 'a'):
            filtered.append(word)

    from collections import Counter
    freq = Counter(filtered)
    top_key = str(dict(freq.most_common(10)))
    return ' '.join(filtered), ' '.join(words_pos), top_key


def simple_sentiment(text: str) -> float:
    """簡易情感分數 [-1, 1]"""
    if not text:
        return 0.0
    words = set(jieba.cut(text[:500]))
    pos = len(words & POS_WORDS)
    neg = len(words & NEG_WORDS)
    total = pos + neg
    if total == 0:
        return 0.0
    return round((pos - neg) / total, 4)


def process_raw(source: str, path: Path) -> pd.DataFrame:
    if not path.exists():
        print(f'[SKIP] {source}: {path}')
        return pd.DataFrame()

    df = pd.read_csv(path, sep='|', on_bad_lines='skip')
    print(f'[INFO] {source}: {len(df)} rows')

    rows = []
    for i, row in df.iterrows():
        item_id  = f"{source}_{str(row.get('item_id',''))}"
        content  = str(row.get('content', '') or '')
        title    = str(row.get('title', '') or '')
        date_val = clean_date(row.get('date'))
        category = str(row.get('category', '其他') or '其他')
        link     = str(row.get('link', '') or '') or None
        photo    = str(row.get('photo_link', '') or '') or None

        tf, tp, tkf = tokenize(content)
        senti = (float(row['sentiment'])
                 if pd.notna(row.get('sentiment'))
                 else simple_sentiment(content))

        rows.append({
            'item_id':         item_id,
            'date':            date_val,
            'category':        category,
            'title':           title,
            'content':         content,
            'link':            link,
            'photo_link':      photo,
            'tokens':          tf,
            'tokens_filtered': tf,
            'token_pos':       tp,
            'top_key_freq':    tkf,
            'tokens_v2':       tf,
            'sentiment':       senti,
            'summary':         title[:100],
            'source':          source,
        })

    out = pd.DataFrame(rows)
    print(f'  → processed {len(out)} rows for {source}')
    return out


def main():
    # 讀取現有 preprocessed CSV
    main_df = pd.read_csv(PROCESSED_CSV, sep='|')
    print(f'[INFO] 現有 CSV: {len(main_df)} rows, cols={list(main_df.columns)}')

    # 確保有 source 欄
    if 'source' not in main_df.columns:
        main_df['source'] = 'bilibili'

    existing_ids = set(main_df['item_id'].astype(str).tolist())

    new_dfs = []
    for source, path in SOURCES_RAW.items():
        df_new = process_raw(source, path)
        if df_new.empty:
            continue
        # 去除已存在的 item_id
        df_new = df_new[~df_new['item_id'].isin(existing_ids)]
        print(f'  → {len(df_new)} new rows (after dedup) for {source}')
        new_dfs.append(df_new)

    if not new_dfs:
        print('[WARN] No new data to append')
        return

    combined = pd.concat([main_df] + new_dfs, ignore_index=True)
    combined.to_csv(PROCESSED_CSV, sep='|', index=False, encoding='utf-8-sig')
    print(f'\n[OK] CSV updated: {len(combined)} rows total')

    # 驗證
    check = pd.read_csv(PROCESSED_CSV, sep='|')
    print('source breakdown:')
    print(check['source'].value_counts().to_string())


if __name__ == '__main__':
    main()
