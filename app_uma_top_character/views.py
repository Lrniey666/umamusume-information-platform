from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Max


_CATEGORIES = ['活動', '卡池', '競賽', '系統', '其他']


def _load_topchar_data() -> dict:
    """優先從 TopCharacter DB 載入最新快照；無資料時 fallback 至 CSV。"""
    result = {}
    try:
        from app_uma_top_character.models import TopCharacter
        latest = (
            TopCharacter.objects
            .filter(window_days=0)
            .aggregate(d=Max('computed_date'))['d']
        )
        if latest is not None:
            qs = (
                TopCharacter.objects
                .filter(window_days=0, computed_date=latest)
                .order_by('-mention_count')
            )
            for cate in _CATEGORIES:
                result[cate] = list(
                    qs.filter(category=cate).values_list('character', 'mention_count')
                )
            print(f"[app_uma_top_character] 從 DB 載入，computed_date={latest}")
            return result
    except Exception as exc:
        print(f"[app_uma_top_character] DB 載入失敗，改讀 CSV：{exc}")
    # fallback: CSV
    try:
        import pandas as pd
        from services.news_service import TOP_CHARACTER_CSV
        df_topchar = pd.read_csv(TOP_CHARACTER_CSV)
        for _, row in df_topchar.iterrows():
            result[row['category']] = eval(row['top_keys'])
        print("[app_uma_top_character] fallback: 從 CSV 載入")
    except Exception as exc:
        print(f"[app_uma_top_character] CSV 亦不可用：{exc}")
    return result


data = _load_topchar_data()


def home(request):
    return render(request, 'app_uma_top_character/home.html')


@csrf_exempt
def api_get_topCharacter(request):
    cate = request.POST.get('news_category')
    topk = int(request.POST.get('topk', 10))
    chart_data, wf_pairs = get_category_topCharacter(cate, topk)
    return JsonResponse({'chart_data': chart_data, 'wf_pairs': wf_pairs})


def get_category_topCharacter(cate, topk=10):
    wf_pairs = data.get(cate, [])[:topk]
    words = [w for w, f in wf_pairs]
    freqs = [f for w, f in wf_pairs]
    chart_data = {"category": cate, "labels": words, "values": freqs}
    return chart_data, wf_pairs


print("app_uma_top_character 熱門角色排行載入成功!")
