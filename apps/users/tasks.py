import logging
from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import translation

logger = logging.getLogger(__name__)


@shared_task(
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def send_welcome_email_task(user_id: int, user_language: str):
    """Task to send a welcome email to a new user."""
    from .models import User

    try:
        user = User.objects.get(id=user_id)
        logger.debug('Preparing to send welcome email to %s (ID: %d)', user.email, user_id)

    except User.DoesNotExist:
        logger.error('User with ID %d does not exist. Cannot send welcome email.', user_id)
        return
    
    # Activate the user's preferred language for email content
    with translation.override(user_language):
        subject = render_to_string('emails/welcome/subject.txt', {'user': user}).strip()
        body = render_to_string('emails/welcome/body.txt', {'user': user})

        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            logger.info('Welcome email sent to %s to language %s', user.email, user_language)
        except Exception as e:
            logger.error('Failed to send welcome email to %s: %s', user.email, str(e))
            raise e  # This will trigger the retry mechanism