import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.env.local')

app = Celery('blog_api')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

# setting
app.conf.beat_schedule = {
    'publish-scheduled-posts': {
        'task': 'apps.blog.tasks.publish_scheduled_posts',
        'schedule': 60.0,  # every 60 seconds (1 minute)
    },
    'clear-expired-notifications': {
        'task': 'apps.notifications.tasks.clear_expired_notifications',
        'schedule': crontab(hour=3, minute=0),  # every day
    },
    'generate-daily-stats': {
        'task': 'apps.blog.tasks.generate_daily_stats',
        'schedule': crontab(hour=0, minute=0),  # every day at midnight
    },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')