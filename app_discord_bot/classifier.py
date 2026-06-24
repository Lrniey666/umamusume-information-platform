"""
D4: 馬娘主題篩選（關鍵字層 + Gemini Batch 分類層）

改版重點：
  - 分批讀取（CHUNK_SIZE 筆）並即時寫入 DB，避免大批量記憶體與長時間無輸出
  - Layer 2 每批次前可即時取消，也可設定每次執行最多送 Gemini 的批次上限
  - 每個 CHUNK 的 Layer 1 跑完立即存一次，Layer 2 跑完再存一次
"""
import os
from typing import Callable, Optional

from .models import DiscordMessage

UMA_KEYWORDS = {
    '賽馬娘', '馬娘', 'ウマ娘', 'umamusume', 'uma musume',
    '育成', '情景', '因子', '技能', '固有', '進化技能',
    '天賦', '競速', '決賽', '支援卡', '限定', '卡池', '抽卡',
    '活動', '劇情', '故事', '練馬', '勉強', '智慧',
    '特別週', '無聲鈴鹿', '東海帝王', '丸善斯基', '草上飛',
    '小栗帽', '黃金城市', '伏特加', '大和赤驥', '大樹快車',
    '目白麥昆', '神鷹', '超級小海灣', '空中神宮', '不敗帝王',
    '圓周率', 'PvP', '勝組', '速通', '重置',
}

BATCH_SIZE  = 50     # 每次送 Gemini 的訊息數
CHUNK_SIZE  = 2000   # 每輪從 DB 撈取的訊息數（撈完立即存回）
MAX_L2_BATCHES = 200  # 每次執行最多送 Gemini 的批次數（50 則/批 × 200 = 10,000 則上限）

_GEMINI_CLIENT = None

CancelCheck = Optional[Callable[[], bool]]


def _get_gemini_client():
    global _GEMINI_CLIENT
    if _GEMINI_CLIENT is None:
        from google import genai
        _GEMINI_CLIENT = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
    return _GEMINI_CLIENT


def layer1_keyword(content: str) -> bool:
    """Layer 1：關鍵字比對"""
    c = content.lower()
    return any(kw.lower() in c for kw in UMA_KEYWORDS)


def layer2_gemini_batch(
    messages: list,
    cancel_check: CancelCheck = None,
    max_batches: int = MAX_L2_BATCHES,
    batch_counter: list = None,  # 傳入可變容器以跨 chunk 累計批次數
) -> dict:
    """Layer 2：批次送 Gemini 判斷是否為馬娘相關訊息"""
    client = _get_gemini_client()
    results = {}
    if batch_counter is None:
        batch_counter = [0]

    for i in range(0, len(messages), BATCH_SIZE):
        if cancel_check and cancel_check():
            print('[Classifier] Layer 2 已取消')
            break
        if batch_counter[0] >= max_batches:
            print(f'[Classifier] Layer 2 已達每次執行上限（{max_batches} 批次），本次暫停，下次繼續')
            break
        batch = messages[i:i + BATCH_SIZE]
        numbered = '\n'.join(
            f'{j + 1}. {m.content[:300]}'
            for j, m in enumerate(batch)
        )
        prompt = (
            '以下是 Discord 訊息清單，請判斷每則訊息是否與「賽馬娘 Pretty Derby」遊戲相關。'
            '只回覆數字清單，格式：序號. YES 或 序號. NO，不需解釋。\n\n' + numbered
        )
        try:
            from google.genai import types as genai_types
            resp = client.models.generate_content(
                model='gemini-3.1-flash-lite',
                config=genai_types.GenerateContentConfig(
                    max_output_tokens=512, temperature=0.0
                ),
                contents=prompt,
            )
            batch_counter[0] += 1
            for line in resp.text.strip().splitlines():
                parts = line.split('.', 1)
                if len(parts) == 2:
                    try:
                        idx = int(parts[0].strip()) - 1
                        if 0 <= idx < len(batch):
                            results[batch[idx].msg_id] = 'YES' in parts[1].upper()
                    except ValueError:
                        pass
        except Exception as e:
            print(f'[Classifier] Gemini batch 失敗: {e}')
            batch_counter[0] += 1  # 失敗也計入，避免無限重試
    return results


def run_classifier(cancel_check: CancelCheck = None) -> str:
    """
    主入口：對所有 is_umamusume=None 的訊息執行分類。
    採分批讀取，每批 CHUNK_SIZE 筆，Layer 1 後立即寫入 DB，
    再做 Layer 2 Gemini（跨批次共用 MAX_L2_BATCHES 上限）。
    回傳 'ok'、'cancelled' 或 'limit_reached'。
    """
    total = DiscordMessage.objects.filter(is_umamusume=None).count()
    print(f'[Classifier] 待分類 {total} 筆訊息')

    if total == 0:
        return 'ok'

    processed    = 0
    uma_count    = 0
    batch_counter = [0]  # 跨 chunk 共用 Gemini 批次計數

    while True:
        if cancel_check and cancel_check():
            print('[Classifier] 已取消')
            return 'cancelled'

        # 每次取一批尚未分類的訊息
        chunk = list(
            DiscordMessage.objects.filter(is_umamusume=None)
            .order_by('timestamp')[:CHUNK_SIZE]
        )
        if not chunk:
            break

        # ── Layer 1：關鍵字比對 ─────────────────────────────
        layer2_candidates = []
        for msg in chunk:
            if layer1_keyword(msg.content):
                msg.is_umamusume = True
                msg.classified_by = 'keyword'
                uma_count += 1
            elif len(msg.content) <= 20:
                msg.is_umamusume = False
                msg.classified_by = 'keyword'
            else:
                layer2_candidates.append(msg)

        # Layer 1 結果先存到 DB（layer2_candidates 還是 None，下輪會繼續撈）
        l1_done = [m for m in chunk if m.is_umamusume is not None]
        if l1_done:
            DiscordMessage.objects.bulk_update(
                l1_done, ['is_umamusume', 'classified_by'], batch_size=500
            )

        # ── Layer 2：Gemini 批次 ────────────────────────────
        if layer2_candidates:
            # 已達上限時，把這批 layer2_candidates 標為 False（保守策略），繼續下輪
            if batch_counter[0] >= MAX_L2_BATCHES:
                print(f'[Classifier] Layer 2 已達批次上限，本 chunk 剩餘 {len(layer2_candidates)} 筆標為無關')
                for msg in layer2_candidates:
                    msg.is_umamusume = False
                    msg.classified_by = 'keyword'
                DiscordMessage.objects.bulk_update(
                    layer2_candidates, ['is_umamusume', 'classified_by'], batch_size=500
                )
            else:
                l2_results = layer2_gemini_batch(
                    layer2_candidates,
                    cancel_check=cancel_check,
                    max_batches=MAX_L2_BATCHES,
                    batch_counter=batch_counter,
                )
                if cancel_check and cancel_check():
                    # 取消：把已有結果存起來，其餘留 None 下次繼續
                    for msg in layer2_candidates:
                        if msg.msg_id in l2_results:
                            msg.is_umamusume = l2_results[msg.msg_id]
                            msg.classified_by = 'gemini'
                            if msg.is_umamusume:
                                uma_count += 1
                    partial = [m for m in layer2_candidates if m.is_umamusume is not None]
                    if partial:
                        DiscordMessage.objects.bulk_update(
                            partial, ['is_umamusume', 'classified_by'], batch_size=500
                        )
                    print('[Classifier] 取消，已保留部分 Layer 2 結果')
                    return 'cancelled'
                for msg in layer2_candidates:
                    msg.is_umamusume = l2_results.get(msg.msg_id, False)
                    msg.classified_by = 'gemini'
                    if msg.is_umamusume:
                        uma_count += 1
                DiscordMessage.objects.bulk_update(
                    layer2_candidates, ['is_umamusume', 'classified_by'], batch_size=500
                )

        processed += len(chunk)
        remaining = DiscordMessage.objects.filter(is_umamusume=None).count()
        print(f'[Classifier] 進度：{processed} 筆已處理，剩餘 {remaining} 筆，馬娘累計 {uma_count} 筆，L2 批次 {batch_counter[0]}/{MAX_L2_BATCHES}')

        if cancel_check and cancel_check():
            return 'cancelled'

        # Layer 2 達上限且還有剩餘 → 本次執行結束，讓使用者再次觸發繼續
        if batch_counter[0] >= MAX_L2_BATCHES and remaining > 0:
            print(f'[Classifier] Layer 2 上限已達，本次完成 {processed} 筆，剩餘 {remaining} 筆待下次執行')
            return 'limit_reached'

    print(f'[Classifier] 完成：共 {processed} 筆，馬娘相關 {uma_count} 筆')
    return 'ok'
