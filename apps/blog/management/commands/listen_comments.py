import json
import asyncio
from django.core.management.base import BaseCommand
from django.conf import settings
import redis.asyncio as aioredis


class Command(BaseCommand):
    help = 'Listens to the Redis comments channel and prints messages to the console (async version)'
    
    def handle(self, *args, **options):
        
        # Run the async function in the event loop
        asyncio.run(self.listen_to_comments())
    
    async def listen_to_comments(self):
        """Async function for listening to the comments channel"""
        
        # Create an async Redis client
        redis_client = await aioredis.from_url(
            settings.REDIS_URL if hasattr(settings, 'REDIS_URL') 
            else f'redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}',
            decode_responses=True
        )
        
        try:
            # Create a pubsub object
            pubsub = redis_client.pubsub()
            
            # Subscribe to the channel
            await pubsub.subscribe('comments')
            
            self.stdout.write(
                self.style.SUCCESS('✓ Subscribed to the comments channel (async). Waiting for messages...')
            )
            
            # Infinite loop - listening to messages
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    # Парсим JSON
                    try:
                        data = json.loads(message['data'])
                        
                        # Beautifully displayed
                        self.stdout.write(
                            self.style.SUCCESS(f'\n━━━ Новый комментарий ━━━')
                        )
                        self.stdout.write(f"  📝 post slug: {data.get('post_slug', 'N/A')}")
                        self.stdout.write(f"  👤 Author ID: {data.get('author_id', 'N/A')}")
                        self.stdout.write(f"  💬 Text: {data.get('body', 'N/A')}")
                        self.stdout.write(f"  🕐 Time: {data.get('created_at', 'N/A')}")
                        self.stdout.write(
                            self.style.SUCCESS('━━━━━━━━━━━━━━━━━━━━━━━━━\n')
                        )
                    
                    except json.JSONDecodeError as e:
                        self.stdout.write(
                            self.style.ERROR(f'Ошибка парсинга JSON: {e}')
                        )
        
        except asyncio.CancelledError:
            self.stdout.write(
                self.style.WARNING('\n✗ Received stop signal')
            )
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {e}')
            )
        
        finally:
            # Отписываемся и закрываем соединение
            await pubsub.unsubscribe('comments')
            await redis_client.close()
            self.stdout.write(
                self.style.WARNING('✗ Unsubscribed from the comments channel')
            )