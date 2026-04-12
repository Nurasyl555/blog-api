import logging
import json
from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def process_new_comment_task(comment_id: int):
    """Task to process a new comment and send notifications."""
    from apps.blog.models import Comment
    from apps.notifications.models import Notification

    try:
        comment = Comment.objects.select_related('post', 'author').get(id=comment_id)
    except Comment.DoesNotExist:
        logger.error('Comment with ID %d does not exist. Cannot process notifications.', comment_id)
        return
    
    post = comment.post

    # 1 Create notification for the post author if the comment author is different
    if post.author != comment.author:
        Notification.objects.create(
            recipient=post.author,
            comment=comment,
        )
        logger.info('Notification created for post author %s  about new comment (ID: %d)', post.author.email, comment_id)

    # 2 Send real-time notification via WebSocket to the post author
    channel_layer = get_channel_layer()
    group_name = f'post_{post.slug}_comments'

    message_data = {
        'comment_id': comment.id,
        'author': {
            'id': comment.author.id,
            'email': comment.author.email,
        },
        'body': comment.body,
        'created_at': comment.created_at.isoformat(),
    }

    try: 
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'comment_message',
                'data': message_data,
            }
        )
        logger.info('Sent WebSocket notification to group %s about new comment (ID: %d)', group_name, comment_id)
    except Exception as e:
        logger.error('Failed to send WebSocket notification for comment (ID: %d): %s', comment_id, str(e))
        raise e  # This will trigger the retry mechanism
    

@shared_task
def clear_expired_notifications():
    """Task to clear notifications that are older than 30 days."""
    from apps.notifications.models import Notification
    from django.utils import timezone
    from datetime import timedelta

    expiration_date = timezone.now() - timedelta(days=30)

    deleted_count, _ = Notification.objects.filter(
        created_at__lt=expiration_date).delete()
    
    logger.info('Cleared %d expired notifications older than 30 days', deleted_count)