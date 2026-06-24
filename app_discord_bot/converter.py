"""
D5: DiscordMessage → NewsData 轉換整合
"""
from .models import DiscordMessage


def convert_discord_to_newsdata() -> int:
    """
    將 is_umamusume=True 且尚未轉換的 DiscordMessage 匯入 NewsData。
    """
    from app_user_keyword_db.models import NewsData

    pending = DiscordMessage.objects.filter(
        is_umamusume=True,
        news_data_id=''
    ).order_by('timestamp')

    created = 0
    for msg in pending:
        item_id = f'discord_{msg.msg_id}'
        title = msg.content[:50].replace('\n', ' ')

        obj, is_new = NewsData.objects.get_or_create(
            item_id=item_id,
            defaults={
                'date':            msg.timestamp.date(),
                'category':        'Discord',
                'source':          'discord',
                'title':           title,
                'content':         msg.content,
                'link':            f'https://discord.com/channels/*/{msg.channel_id}/{msg.msg_id}',
                'photo_link':      '',
                'tokens_filtered': '',
                'top_key_freq':    '',
                'sentiment':       None,
            }
        )
        if is_new:
            msg.news_data_id = item_id
            msg.save(update_fields=['news_data_id'])
            created += 1

    print(f'[Converter] 新增 {created} 筆 NewsData（Discord 來源）')
    return created
