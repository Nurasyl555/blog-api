from django.urls import re_path
from apps.notifications import consumers

websocket_urlpatterns = [
    re_path(r'ws/posts/(?P<slug>[\w-]+)/comments/$', consumers.CommentConsumer.as_asgi()),
]   