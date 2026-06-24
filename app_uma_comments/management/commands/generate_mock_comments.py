import random
from django.core.management.base import BaseCommand
from app_uma_news.models import GameAnnouncement
from app_uma_comments.models import PlayerComment

TEMPLATES = {
    '活動': [
        '好棒的活動！獎勵超多', '終於來了！等很久了', '素材超好拿，感謝官方',
        'CP值滿點，必跑', '活動期間有點短...', '難度剛好，新手友善',
        '每次活動都要肝，累了', '這個劇情好感人', '免費石頭又來了！',
        '這次活動比上次好多了', '點數好拿！', '任務量有點多呢',
        '順手完成就好，別太認真', '獎勵很實用！', '特典很可愛～',
    ],
    '卡池': [
        '限定角色出了！衝！', '要肝了，存了好久的石頭',
        '沒有保底好難受', '歪到其他角了...心碎', '這次卡池值得抽',
        '機率太低了吧...', '終於出了我最想要的角色！！', '下次再出就好了',
        '單抽出限定！！！', '十連全白，嗚嗚', '比起上次好多了',
        '這個角色技能很強', '不抽不抽，錢包哭泣', '又一個限定...錢錢不夠',
        '手氣爆發！！', '這次圖很好看所以抽', '等復刻再說',
    ],
    '競賽': [
        '這賽制有挑戰性', '組合搭配很重要', '難度稍微高了點',
        '感謝攻略分享的各位', '打了十幾次終於過了！', '排名積分有點壓力',
        '和朋友一起玩超好玩', '規則說明可以更清楚', '有點看運氣成分',
        '獎勵很豐厚！', '這次對手太強了', '練習模式很方便',
        '終於到白金了！', '差一步就上鑽了嗚嗚', '下賽季繼續努力',
    ],
    '系統': [
        '維護辛苦了！', '修了個好 bug，謝謝', '維護時間有點長...',
        '更新後流暢很多', '希望下次能改善 UI', '這個功能很實用',
        '還有其他 bug 沒修到', '感謝官方持續優化', '新功能真方便',
        '效能好多了！', '等待也是值得的', '多平台支援什麼時候來',
        '更新內容超多！', '公告寫得很清楚', '這個改動很貼心',
    ],
    '其他': [
        '感謝官方用心', '期待未來更新', '這個公告很有趣',
        '喜歡這類通知', '繼續加油！', '好厲害',
        '官方真的很努力', '謝謝你們的付出', '期待下一個公告',
        '玩了好幾年了，一直支持', '賽馬娘最棒！',
    ],
}

AUTHORS = [
    '草紙', '風雲人物', 'P主阿俊', '深夜騎士', '晨曦',
    '黃金左腳', 'UMA愛好者', '跑跑跑', '星河旅人', '紫苑の夢',
    '馬場の番人', '閃電特快車', '阿福一起跑', 'gacha達人', '玩家甲',
    '玩家乙', '玩家丙', '無名騎師', '日出P', '月光P',
    'スペシャルウィーク', 'サイレンススズカ', 'テイエムオペラオー',
]


class Command(BaseCommand):
    help = '為每篇 GameAnnouncement 生成 Mock 玩家留言'

    def add_arguments(self, parser):
        parser.add_argument('--min', type=int, default=10, help='最少留言數（預設 10）')
        parser.add_argument('--max', type=int, default=25, help='最多留言數（預設 25）')
        parser.add_argument('--force', action='store_true', help='強制重新生成（清除舊留言）')

    def handle(self, *args, **options):
        min_c = options['min']
        max_c = options['max']
        force = options['force']

        announcements = GameAnnouncement.objects.all()
        total_created, total_skipped = 0, 0

        for ann in announcements:
            if not force and ann.comments.exists():
                total_skipped += 1
                continue

            if force:
                ann.comments.all().delete()

            n = random.randint(min_c, max_c)
            pool = TEMPLATES.get(ann.category, TEMPLATES['其他'])
            comments_to_create = []

            for floor in range(1, n + 1):
                text = random.choice(pool)
                # 加入公告標題關鍵字的變化，讓留言更自然
                if random.random() < 0.3 and ann.title:
                    keywords = ann.title[:10]
                    text = f'{text}（{keywords}）'

                comments_to_create.append(PlayerComment(
                    announcement = ann,
                    content      = text,
                    author       = random.choice(AUTHORS),
                    upvotes      = random.randint(0, 200),
                    downvotes    = random.randint(0, 15),
                    floor        = floor,
                ))

            PlayerComment.objects.bulk_create(comments_to_create)
            total_created += n

        self.stdout.write(self.style.SUCCESS(
            f'完成！已生成 {total_created} 則留言，跳過 {total_skipped} 篇（已有留言）'
        ))
        self.stdout.write(f'涵蓋 {announcements.count() - total_skipped} 篇公告')
