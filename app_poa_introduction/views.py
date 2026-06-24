from django.shortcuts import render


def introduction(request):
    """賽馬娘輿情分析平台介紹頁"""
    context = {
        'platform_name': '賽馬娘輿情分析平台',
        'data_source': '巴哈姆特馬娘版（bsn=34421）+ Bilibili BWIKI 官方公告',
        'tech_stack': [
            ('後端框架', 'Django 5.2.15 LTS'),
            ('Gemini 模型', 'gemini-3.5-flash'),
            ('Claude 模型', 'claude-sonnet-4-6'),
            ('向量搜尋', 'FAISS 1.14.2'),
            ('資料庫', 'SQLite（Django ORM）'),
            ('排程', 'APScheduler 3.11.2'),
            ('部署', 'Docker + Nginx + Gunicorn'),
        ],
        'features': [
            ('◎ 角色人氣 PK', '首頁多角色聲量與情緒對比'),
            ('📊 關鍵字聲量分析', '自訂關鍵字時間趨勢圖'),
            ('💬 情感分析', '正/負/中性情緒分布'),
            ('🤖 雙模型 AI 報告', 'Gemini 3.5 Flash + Claude Sonnet 4.6'),
            ('📝 留言情感儀表板', '巴哈板貼文情緒六維度分析'),
            ('🧠 Agentic AI 助理', '多工具呼叫馬娘知識問答'),
            ('🔍 RAG 知識庫', 'FAISS 向量檢索 + 引用來源'),
            ('🔥 熱門關鍵詞排行', '各類別公告高頻詞彙'),
            ('⭐ 熱門角色排行', '各類別最熱門馬娘'),
        ],
    }
    return render(request, 'app_poa_introduction/platform-introduction.html', context)
