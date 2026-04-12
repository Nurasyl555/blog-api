import logging
from celery import shared_task
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from apps.blog.models import Post

logger = logging.getLogger(__name__)

@shared_task(
        autoretry_for=(Exception,),
        retry_backoff=True,
        max_retries=3,
)
def invalidate_posts_cache_task():
    """ invalidate the cache for the list of posts """
    for lang_code, lang_name in settings.LANGUAGES:
        cache_key = f'posts_list_{lang_code}'
        cache.delete(cache_key)
        logger.debug('Delete cache for language %s', lang_code)

    logger.info('Cache for posts list invalidated successfully')


@shared_task
def publish_scheduled_posts():
    """publish posts that are scheduled to be published"""  
    from apps.blog.models import Post
    import json
    import redis

    now = timezone.now()

    posts_to_publish = Post.objects.filter(
        status='scheduled',
        publish_at__lte=now
    )

    count = posts_to_publish.count()
    if count == 0:
        logger.info('No posts to publish at %s', now)
        return
    
    # connect to Redis for SSE events
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=True
    )

    for post in posts_to_publish:
        post.status = Post.Status.PUBLISHED
        post.save(update_fields=['status'])
        logger.info('Published post "%s" (ID: %d)', post.title, post.id)

        # Send SSE event to notify clients about the new post
        event_data = {
            'id': post.id,
            'title': post.title,
            'slug': post.slug,
            'author': {
                'id': post.author.id,
                'email': post.author.email,
            },
            'published_at': post.publish_at.isoformat(),
        }
        redis_client.publish('posts_channel', json.dumps(event_data))
    
    logger.info('Published %d posts and sent SSE events', count)

    invalidate_posts_cache_task.delay()

@shared_task
def generate_daily_stats():
    """Generate daily statistics for posts and users."""
    from apps.blog.models import Post, Comment
    from apps.users.models import User

    yesterday = timezone.now() - timedelta(days=1)

    new_posts = Post.objects.filter(created_at__gte=yesterday).count()
    new_comments = Comment.objects.filter(created_at__gte=yesterday).count()
    new_users = User.objects.filter(date_joined__gte=yesterday).count()

    logger.info('Daily stats - New posts: %d, New comments: %d, New users: %d', new_posts, new_comments, new_users)