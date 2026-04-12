import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import get_user_model
from apps.blog.models import Post

logger = logging.getLogger(__name__)

User = get_user_model()


class CommentConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for receiving live comments on a post.
    
    URL: ws://host/ws/posts/<slug>/comments/?token=<jwt_access_token>
    
    """
    
    async def connect(self):
        """Called when attempting to establish a WebSocket connection"""
        self.post_slug = self.scope['url_route']['kwargs']['slug']
        self.group_name = f'post_{self.post_slug}_comments'
        
        # Authentication via JWT token
        token = self.scope['query_string'].decode().split('token=')[-1].split('&')[0]
        
        if not token:
            logger.warning('WebSocket connection rejected: no token provided')
            await self.close(code=4001)  # 4001 = Unauthorized
            return
        
        # Проверяем токен
        user = await self.get_user_from_token(token)
        if not user:
            logger.warning('WebSocket connection rejected: invalid token')
            await self.close(code=4001)
            return
        
        self.scope['user'] = user
        
        # Проверяем что пост существует
        post_exists = await self.check_post_exists(self.post_slug)
        if not post_exists:
            logger.warning('WebSocket connection rejected: post %s not found', self.post_slug)
            await self.close(code=4004)  # 4004 = Not Found
            return
        
        # Добавляем в группу
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info('WebSocket connected: user %s to post %s', user.email, self.post_slug)
    
    async def disconnect(self, close_code):
        """Called when the WebSocket connection is closed"""
        # Remove from the group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        
        logger.info('WebSocket disconnected from post %s with code %s', 
                   self.post_slug, close_code)
    
    async def receive(self, text_data):
        """Called when a message is received from the client (not used)"""
        pass
    
    async def comment_message(self, event):
        await self.send(text_data=json.dumps(event['data']))
    
    @database_sync_to_async
    def get_user_from_token(self, token: str):
        """Gets user from JWT token"""
        try:
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            return User.objects.get(id=user_id)
        except (TokenError, User.DoesNotExist):
            return None
    
    @database_sync_to_async
    def check_post_exists(self, slug: str) -> bool:
        """Checks if a post exists"""
        return Post.objects.filter(slug=slug).exists()
