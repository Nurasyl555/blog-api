import logging
import json
import redis
from django.conf import settings
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from apps.users.ratelimit import rate_limit


from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from apps.blog.permissions import IsAuthorOrReadOnly
from apps.blog.models import Post, Comment
from apps.blog.serializers import (
    PostListSerializer,
    PostDetailSerializer,
    PostCreateUpdateSerializer,
    CommentSerializer
)

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True
)

logger = logging.getLogger(__name__)

@method_decorator(
    rate_limit(key_prefix='post_create', max_requests=20, window_seconds=60),
    name='create'
)
class PostViewSet(viewsets.ModelViewSet):
    """CRUD for post"""
    queryset = Post.objects.filter(status=Post.Status.PUBLISHED)
    lookup_field = 'slug' # finding with slug
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]

    def get_serializer_class(self):
        """
        Selecting a serializer based on the action
        """
        if self.action == 'list':
            return PostListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return PostCreateUpdateSerializer
        
        return PostDetailSerializer
    
    def get_queryset(self):
        """If the user is authorized, we also show their drafts."""
        queryset = super().get_queryset()

        #Showing published + your drafts
        if self.request.user.is_authenticated:
            queryset = Post.objects.filter(
                status=Post.Status.PUBLISHED
            ) | Post.objects.filter(
                author = self.request.user
            )

        return queryset.distinct()
    
    def list(self, request, *args, **kwargs):
        '''We cache the list of posts for 60 seconds.'''
        cache_key = 'post_list'
        cached_data = cache.get(cache_key)

        if cached_data:
            logger.info('Returned the list of posts from the cache')
            return Response(cached_data)
        
        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, 60) # cache 60s
        logger.info('The list of posts is cached')

        return response
    
    def perform_create(self, serializer):
        """Automatically set author = current user"""
        logger.info('Creating post user %s', self.request.user.email)
        serializer.save(author=self.request.user)
        logger.info('Post create ', serializer.instance.title)

        # Invalidate the cache
        cache.delete('post_list')
        logger.info('Post create: %s cache clean', serializer.instance.title)

    def perform_update(self, serializer):
        logger.info('Updating post %s user %s',
                    serializer.instance.title, self.request.user.email)
        serializer.save()

        # Invalidate the cache
        cache.delete('posts_list')
        logger.info('Post update, cache clean')

    def perform_destroy(self, instance):
        logger.info('Deleting post %s user %s', 
                    instance, self.request.user.email)
        instance.delete()

        # Invalidate the cache
        cache.delete('posts_list')
        logger.info('Post delete, cache clean')

    @action(detail=True, methods=['get', 'post'], url_path='comments')
    def comments(self, request, slug=None):
        """
        GET /api/posts/{slug}/commets/ - list of commetns
        Post /api/posts/{slug}/comments/ - add comments
        """

        post = self.get_object()

        if request.method == 'GET':
            comments = post.comments.all()
            serializer = CommentSerializer(comments, many=True)
            return Response(serializer.data)
        
        elif request.method == 'POST':
            serializer = CommentSerializer(data=request.data)
            if serializer.is_valid():
                comment = serializer.save(author=request.user, post=post)
                logger.info('Comment added to post: %s  user %s',
                            post.title, request.user.email)
                
                # publish an event to Redis
                event_data = {
                    'comment_id': comment.id,
                    'post_id': post.id,
                    'post_title': post.title,
                    'author_email': request.user.email,
                    'body': comment.body,
                    'created_at': comment.created_at.isoformat(),
                }
                redis_client.publish('comment', json.dumps(event_data))
                logger.info('event is publish in redis comments')
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)