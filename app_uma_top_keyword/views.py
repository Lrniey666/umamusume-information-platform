from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Max


_CATEGORIES = ['活動', '卡池', '競賽', '系統', '其他']


def _load_topkey_data() -> dict:
    """優先從 TopKeyword DB 載入最新快照；無資料時 fallback 至 CSV。"""
    result = {}
    try:
        from app_uma_top_keyword.models import TopKeyword
        latest = (
            TopKeyword.objects
            .filter(window_days=0)
            .aggregate(d=Max('computed_date'))['d']
        )
        if latest is not None:
            qs = (
                TopKeyword.objects
                .filter(window_days=0, computed_date=latest)
                .order_by('-freq')
            )
            for cate in _CATEGORIES:
                result[cate] = list(
                    qs.filter(category=cate).values_list('keyword', 'freq')
                )
            print(f"[app_uma_top_keyword] 從 DB 載入，computed_date={latest}")
            return result
    except Exception as exc:
        print(f"[app_uma_top_keyword] DB 載入失敗，改讀 CSV：{exc}")
    # fallback: CSV
    try:
        import pandas as pd
        from services.news_service import TOPKEY_CSV
        df_topkey = pd.read_csv(TOPKEY_CSV)
        for _, row in df_topkey.iterrows():
            result[row['category']] = eval(row['top_keys'])
        print("[app_uma_top_keyword] fallback: 從 CSV 載入")
    except Exception as exc:
        print(f"[app_uma_top_keyword] CSV 亦不可用：{exc}")
    return result


data = _load_topkey_data()


def home(request):
    return render(request, 'app_uma_top_keyword/home.html')


@csrf_exempt
def api_get_cate_topword(request):
    cate = request.POST.get('news_category')
    topk = int(request.POST.get('topk', 10))
    chart_data, wf_pairs = get_category_topword(cate, topk)
    return JsonResponse({'chart_data': chart_data, 'wf_pairs': wf_pairs})


def get_category_topword(cate, topk=10):
    wf_pairs = data.get(cate, [])[:topk]
    words = [w for w, f in wf_pairs]
    freqs = [f for w, f in wf_pairs]
    chart_data = {"category": cate, "labels": words, "values": freqs}
    return chart_data, wf_pairs


print("app_uma_top_keyword 熱門關鍵詞載入成功!")
