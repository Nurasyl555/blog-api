import logging
import json
import redis
import asyncio
from django.core.cache import cache
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from apps.users.ratelimit import rate_limit
from django.utils.translation import get_language

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, AllowAny
from apps.blog.permissions import IsAuthorOrReadOnly
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse, OpenApiParameter
import redis.asyncio as aioredis

from apps.notifications.tasks import process_new_comment_task
from apps.blog.tasks import invalidate_posts_cache_task
from apps.notifications.models import Notification
from apps.blog.models import Post, Comment
from apps.blog.serializers import (
    PostListSerializer,
    PostDetailSerializer,
    PostCreateUpdateSerializer,
    CommentSerializer
)
from django.http import StreamingHttpResponse
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

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
    
    @extend_schema(
            tags=['Posts'],
            summary='List of posts',
            description="""
            Retrieve a list of published posts.

            **Caching**:
            - Answer: The list of posts is cached for 60 seconds. The cache key includes the current language, so different languages will have separate caches.
            - Cache dependency: The cache is automatically invalidated whenever a post is created, updated, or deleted. This ensures that users always see the most up-to-date list of posts.
            - Cache invalidation: When a post is created, updated, or deleted, the cache for all languages is cleared to ensure that users see the most current data.

            **language behavior**:
            - The API supports multilingual content. The list of posts is cached separately for each language,
            - Date and time fields in the response are formatted according to the user's timezone and language preferences. If the user is authenticated, their timezone is used; otherwise, UTC is used.

            **Timezone**
            - Authenticated users see date and time fields formatted according to their timezone preferences. Unauthenticated users see date and time in UTC.
            - Anonymous users see date and time in UTC.

            **Authentication**: Both authenticated and anonymous users can access the list of posts. Authenticated users will see their drafts in addition to published posts, while anonymous users will only see published posts.

            **Pagination**: The list of posts is paginated, with a default page size of 10 posts per page. Clients can navigate through pages using query parameters.
            """,
            parameters=[
                OpenApiParameter(
                    name='lang',
                    description='Language answer (en, ru, kk)',
                    required=False,
                    type=str
                )
            ],
            responses={
                200: PostListSerializer(many=True),
                400: OpenApiResponse(description='Bad Request'),
                401: OpenApiResponse(description='Unauthorized'),
            }
    )
    def list(self, request, *args, **kwargs):
        '''We cache the list of posts for 60 seconds.'''
        current_language = get_language()
        cache_key = f'post_list_{current_language}'
        cached_data = cache.get(cache_key)

        if cached_data:
            logger.info('Returned the list of posts from the cache %s', current_language)
            return Response(cached_data)
        
        self.queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(self.queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
            paginated_response = self.get_paginated_response(serializer.data)
            cache.set(cache_key, paginated_response.data, 60) # cache 60s
            logger.info('The list of posts is cached %s', current_language)
            return paginated_response

        serializer = self.get_serializer(self.queryset, many=True, context={'request': request})
        cache.set(cache_key, serializer.data, 60) # cache 60s
        logger.info('The list of posts is cached %s', current_language)

        return Response(serializer.data)
    
    @extend_schema(
            tags=['Posts'],
            summary='Create a new post',
            description="""
            Create a new blog post. Only authenticated users can create posts.

            **Authentication**: Bearer JWT token

            **Side effects**:
            - Author is automatically set to the current authenticated user.
            - The cache for the list of posts is invalidated for all languages to ensure that the new post appears in the list immediately.
            - Rate limiting is applied to prevent abuse. Each user can create a maximum of 20 posts per minute.
            """,
            request=PostCreateUpdateSerializer,
            responses={
                201: PostDetailSerializer,
                400: OpenApiResponse(description='Validation Error'),
                401: OpenApiResponse(description='Unauthorized'),
                429: OpenApiResponse(description='Too Many Requests'),
            },
            examples=[
                OpenApiExample(
                    'Create Post Example',
                    value={
                        "title": "My First Post",
                        'slug': 'my-first-post',
                        'body': 'This is the content of my first post.',
                        'category': 1,  # Assuming category with ID 1 exists
                        'tags': [1, 2],  # Assuming tags with IDs 1 and 2 exist
                        'status': 'published',
                    },
                )
            ]
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @extend_schema(
        tags=['Posts'],
        summary='Retrieve post details',
        description="""
        Returns detailed information about a post.

        **Language behavior:**
        - Category name in the active language
        - Dates in the user's timezone (if logged in)

        **Authentication:** Not required
        """,
        responses={
            200: PostDetailSerializer,
            404: OpenApiResponse(description='Post not found')
        }
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @extend_schema(
        tags=['Posts'],
        summary='Update post',
        description="""
        Updates an existing post.

        **Authentication:** Bearer JWT token

        **Permissions:**
        - Only the author can edit their own post
        
        **Side effects:**
        - Invalidates the cache for the list of posts for all languages
        """,
        request=PostCreateUpdateSerializer,
        responses={
            200: PostDetailSerializer,
            400: OpenApiResponse(description='Validation Error'),
            401: OpenApiResponse(description='Unauthorized'),
            403: OpenApiResponse(description='You are not the author of this post'),
            404: OpenApiResponse(description='Post not found')
        }
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        tags=['Posts'],
        summary='Partially update post',
        description='Same as update, but you can update only some fields',
        request=PostCreateUpdateSerializer,
        responses={
            200: PostDetailSerializer,
            400: OpenApiResponse(description='Validation Error'),
            401: OpenApiResponse(description='Unauthorized'),
            403: OpenApiResponse(description='You are not the author of this post'),
            404: OpenApiResponse(description='Post not found')
        }
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)
    
    @extend_schema(
        tags=['Posts'],
        summary='Delete post',
        description="""
        Deletes a post.

        **Authentication:** Bearer JWT token
        
        **Permissions:**
        - Only the author can delete their own post
        
        **Side effects:**
        - Invalidates the cache for the list of posts for all languages
        - Deletes all comments for the post
        """,
        responses={
            204: OpenApiResponse(description='Post successfully deleted'),
            401: OpenApiResponse(description='Unauthorized'),
            403: OpenApiResponse(description='You are not the author of this post'),
            404: OpenApiResponse(description='Post not found')
        }
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        """Automatically set author = current user"""
        logger.info('Creating post user %s', self.request.user.email)
        post =serializer.save(author=self.request.user)

        # Invalidate the cache
        #self._invalidate_all_caches()
        invalidate_posts_cache_task.delay()
        logger.info('Post create: %s tasks invalidate add to sequens', post.title)

        # Publish an event to Redis if the post is published
        if post.status == Post.Status.PUBLISHED:
            self._publish_post_event(post)


    def perform_update(self, serializer):
        logger.info('Updating post %s user %s',
                    serializer.instance.title, self.request.user.email)
        old_status = serializer.instance.status
        post = serializer.save()

        # Invalidate the cache
        #self._invalidate_all_caches()
        invalidate_posts_cache_task.delay()
        logger.info('Post update, cache clean')

        if old_status != Post.Status.PUBLISHED and post.status == Post.Status.PUBLISHED:
            self._publish_post_event(post)
    
    def _invalidate_all_caches(self):
        """Clean cache for all languages"""
        for lang_code, lang_name in settings.LANGUAGES:
            cache_key = f'post_list_{lang_code}'
            cache.delete(cache_key)
            logger.info('Cache invalidated for language: %s (%s)', lang_code, lang_name)

    def _publish_post_event(self, post):
        event_data = {
            'post_id': post.id,
            'title': post.title,
            'slug': post.slug,
            'author': {
                'id': post.author.id,
                'email': post.author.email
            },
            #'published_at': post.published_at.isoformat() if post.published_at else None
            'published_at': post.created_at.isoformat() if post.created_at else None
        }
        redis_client.publish('post_published', json.dumps(event_data))
        logger.info('Post published event sent to Redis for post: %s', post.title)

    def perform_destroy(self, instance):
        logger.info('Deleting post %s user %s', 
                    instance, self.request.user.email)
        instance.delete()

        # Invalidate the cache
        #self._invalidate_all_caches()
        invalidate_posts_cache_task.delay()
        logger.info('Post delete, cache clean for all languages')

    # def _invalidate_all_caches(self):
    #     """Helper method to invalidate caches for all languages."""
    #     for lang_code, lang_name in settings.LANGUAGES:
    #         cache_key = f'post_list_{lang_code}'
    #         cache.delete(cache_key)
    #         logger.info('Cache invalidated for language: %s (%s)', lang_code, lang_name)


    @extend_schema(
        tags=['Comments'],
        summary='List comments for a post',
        description="""
        Returns all comments for the specified post.

        **Authentication:** Not required
        """,
        responses={
            200: CommentSerializer(many=True),
            404: OpenApiResponse(description='Post not found')
        }
    )
    @extend_schema(
        methods=['POST'],
        tags=['Comments'],
        summary='Add comment',
        description="""
        Adds a new comment to the post.

        **Authentication:** Bearer JWT token
        
        **Side effects:**
        - Author is automatically set to the current user
        - Publishes an event to the Redis channel 'comments' with data: post_slug, author_id, body
        """,
        request=CommentSerializer,
        responses={
            201: CommentSerializer,
            400: OpenApiResponse(description='Validation Errors'),
            401: OpenApiResponse(description='Unauthorized'),
            404: OpenApiResponse(description='Post not found')
        },
        examples=[
            OpenApiExample(
                'Add Comment Example',
                value={
                    'body': 'Отличный пост!'
                }
            )
        ]
    )
    @action(detail=True, methods=['get', 'post'], url_path='comments', permission_classes=[IsAuthenticatedOrReadOnly])
    def comments(self, request, slug=None):
        """
        GET /api/posts/{slug}/commets/ - list of commetns
        Post /api/posts/{slug}/comments/ - add comments
        """

        post = self.get_object()

        if request.method == 'GET':
            comments = post.comments.all()
            serializer = CommentSerializer(comments, many=True, context={'request': request})
            return Response(serializer.data)
        
        elif request.method == 'POST':
            serializer = CommentSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                comment = serializer.save(author=request.user, post=post)
                logger.info('Comment added to post: %s  user %s',
                            post.title, request.user.email)
                
                # publish an event to Redis/Sub
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

                process_new_comment_task.delay(comment.id)
                logger.info('Scheduled task to process new comment (ID: %d)', comment.id)

                # Send live update to WebSocket consumers
                # channel_layer = get_channel_layer()
                # group_name = f'post_{post.slug}_comments'

                # message_data = {
                #     'comment_id': comment.id,
                #     'author': {
                #         'id': request.user.id,
                #         'email': request.user.email,
                #     },
                #     'body': comment.body,
                #     'created_at': comment.created_at.isoformat(),
                # }
                # async_to_sync(channel_layer.group_send)(group_name, {
                #     "type": "comment.message",
                #     "data": message_data
                # })

                # logger.info('Live update sent to WebSocket group %s', group_name)

                # # Create notifications for the post author if the commenter is not the author
                # if post.author != request.user:
                #     Notification.objects.create(
                #         recipient=post.author,
                #         comment=comment
                #     )
                #     logger.info('Notification created for user %s about new comment on post %s',
                #                 post.author.email, post.title)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
@extend_schema(
    tags=['Posts'],
    summary='SSE stream of post publications',
    description="""
    Server-Sent Events endpoint for receiving real-time notifications about new publications.
    
    **Format:** text/event-stream
    
    **Behavior:**
    - The connection remains open
    - When a post transitions to the 'published' status, an event is sent to all connected clients
    - Events contain: post_id, title, slug, author (id + email), published_at
    
    **Authentication:** Not required
    
    **SSE vs WebSockets:**
    SSE - good choice for this use case because:
    1. Unidirectional communication (server -> client) - client doesn't need to send data
    2. Automatic reconnection built into the browser
    3. Simpler to implement than WebSockets
    4. Works through regular HTTP (easier with proxies, firewalls)
    
    **When to Choose WebSockets Over SSE:**
    - Need bidirectional communication (client also sends data)
    - Need a binary protocol (not just text)
    - Need rooms/groups with dynamic subscription (chat, games)
    - Critical low latency requirements
    
    **Usage:**
    ```javascript
    const eventSource = new EventSource('/api/posts/stream/');
    eventSource.onmessage = (event) => {
        const post = JSON.parse(event.data);
        console.log('New post:', post.title);
    };
    ```
    """,
    responses={
        200: OpenApiExample(
            'SSE Event',
            value={
                'post_id': 1,
                'title': 'New post',
                'slug': 'new-post',
                'author': {
                    'id': 1,
                    'email': 'author@example.com'
                },
                'published_at': '2025-02-15T12:30:00Z'
            }
        )
    }
)
#@api_view(['GET'])
#@permission_classes([AllowAny])
async def post_stream_view(request):
    """
    Async SSE endpoint for post publishing.
    
    WHY ASYNC?
    SSE соединение остаётся открытым на неопределённое время (минуты, часы).
    Если это sync view, каждое соединение блокирует worker thread.
    
    При 100 одновременных SSE клиентах:
    - Sync: 100 заблокированных threads = сервер перестаёт принимать новые запросы
    - Async: 1 thread обрабатывает все 100 соединений через event loop
    
    Async позволяет держать тысячи открытых SSE соединений на одном процессе.
    """
    
    async def event_stream():
        """Генератор событий для SSE"""
        
        # Подключаемся к Redis
        redis_client = await aioredis.from_url(
            settings.REDIS_URL,
            decode_responses=True
        )
        
        # Подписываемся на канал
        pubsub = redis_client.pubsub()
        await pubsub.subscribe('post_published')
        
        logger.info('SSE клиент подключился к потоку публикаций')
        
        try:
            # Отправляем heartbeat каждые 30 секунд чтобы соединение не закрылось
            async def send_heartbeat():
                while True:
                    await asyncio.sleep(30)
                    yield f": heartbeat\n\n"
            
            # Слушаем события из Redis
            async def listen_events():
                async for message in pubsub.listen():
                    if message['type'] == 'message':
                        # Формируем SSE событие
                        # Формат SSE: data: {json}\n\n
                        yield f"data: {message['data']}\n\n"
            
            # Объединяем heartbeat и события
            async for chunk in async_merge(send_heartbeat(), listen_events()):
                yield chunk
        
        except asyncio.CancelledError:
            logger.info('SSE клиент отключился')
        
        finally:
            await pubsub.unsubscribe('post_published')
            await redis_client.close()
    
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'  # Отключаем буферизацию для nginx
    
    return response


async def async_merge(*async_iterables):
    """Объединяет несколько async генераторов в один"""
    queue = asyncio.Queue()
    
    async def drain(aiter):
        async for item in aiter:
            await queue.put(item)
    
    async def merged():
        tasks = [asyncio.create_task(drain(aiter)) for aiter in async_iterables]
        
        try:
            while True:
                # Ждём с таймаутом чтобы проверять завершились ли задачи
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield item
                except asyncio.TimeoutError:
                    # Проверяем живы ли задачи
                    if all(task.done() for task in tasks):
                        break
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
    
    async for item in merged():
        yield item
