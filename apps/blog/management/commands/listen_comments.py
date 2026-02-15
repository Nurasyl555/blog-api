import json
import redis
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Listens to the Redis comments channel and prints messages to the console'

    def handle(self, *args, **options):
        # connect to Redis
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db = settings.REDIS_DB,
            decode_responses= True
        )

        #create pubsub object
        pubsub = redis_client.pubsub()

        #subscribe to the channel
        pubsub.subscribe('comment')

        self.stdout.write(
            self.style.SUCCESS('✓ Подписались на канал comments. Ожидаем сообщения...')
        )
        
       # Infinite loop - listening to messages
        try:
            for message in pubsub.listen():
                if message['type'] == 'message':
                    # Парсим JSON
                    data = json.loads(message['data'])
                    
                    # Beautifully displayed
                    self.stdout.write(
                        self.style.SUCCESS(f'\n━━━ new comment ━━━')
                    )
                    self.stdout.write(f"  📝 Пост: {data['post_title']}")
                    self.stdout.write(f"  👤 Автор: {data['author_email']}")
                    self.stdout.write(f"  💬 Текст: {data['body']}")
                    self.stdout.write(f"  🕐 Время: {data['created_at']}")
                    self.stdout.write(
                        self.style.SUCCESS('━━━━━━━━━━━━━━━━━━━━━━━━━\n')
                    )
        
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('\n✗ Отписались от канала comments')
            )
            pubsub.unsubscribe('comments')