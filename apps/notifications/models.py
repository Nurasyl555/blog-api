from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class Notification(models.Model):
    """Model representing a notification.
        Notification for user
    """

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('Recipient')
    )
    comment = models.ForeignKey(
        'blog.Comment',
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('Comment')
    )
    is_read = models.BooleanField(default=False, verbose_name=_('Is Read'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')

    def __str__(self) -> str:
        return f'Notification for {self.recipiient.email} - Comment for: {self.comment.post.title}'
        