import logging
import json
import redis
from django.core.cache import cache
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from apps.users.ratelimit import rate_limit
from django.utils.translation import get_language

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from apps.blog.permissions import IsAuthorOrReadOnly
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse, OpenApiParameter
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
        serializer.save(author=self.request.user)

        self._invalidate_all_caches()
        logger.info('Post create %s, cache cleared for all languages', serializer.instance.title)

        # Invalidate the cache
        self._invalidate_all_caches()
        logger.info('Post create: %s cache clean', serializer.instance.title)

    def perform_update(self, serializer):
        logger.info('Updating post %s user %s',
                    serializer.instance.title, self.request.user.email)
        serializer.save()

        # Invalidate the cache
        self._invalidate_all_caches()
        logger.info('Post update, cache clean')

    def perform_destroy(self, instance):
        logger.info('Deleting post %s user %s', 
                    instance, self.request.user.email)
        instance.delete()

        # Invalidate the cache
        self._invalidate_all_caches()
        logger.info('Post delete, cache clean for all languages')

    def _invalidate_all_caches(self):
        """Helper method to invalidate caches for all languages."""
        for lang_code, lang_name in settings.LANGUAGES:
            cache_key = f'post_list_{lang_code}'
            cache.delete(cache_key)
            logger.info('Cache invalidated for language: %s (%s)', lang_code, lang_name)


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