from rest_framework import serializers
from django.utils.translation import get_language
from django.utils import timezone, formats  # Исправленные импорты!
from apps.blog.models import Category, Tag, Post, Comment, CategoryTranslation
from apps.users.serializers import UserSerializer


class CategorySerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']

    def get_name(self, obj):
        return obj.get_name()


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']


class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    created_at_formatted = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'post', 'author', 'body', 'created_at', 'created_at_formatted']
        read_only_fields = ['id', 'created_at', 'post']

    # Исправлено имя метода (было formatter)
    def get_created_at_formatted(self, obj):
        """Formatting date locale user"""
        request = self.context.get('request')

        if request and request.user.is_authenticated:
            # Получаем часовой пояс, который мы сохраняли юзеру в БД
            user_tz = timezone.get_current_timezone()
            local_time = obj.created_at.astimezone(user_tz)
        else:
            local_time = obj.created_at
            
        # Исправлено format на formats
        return formats.date_format(local_time, 'DATETIME_FORMAT')


class PostListSerializer(serializers.ModelSerializer):
    """"For list of Post"""
    author = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    comment_count = serializers.IntegerField(source='comments.count', read_only=True)
    created_at_formatted = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'author', 'category',
            'tags', 'status', 'created_at', 'created_at_formatted', 'comment_count'
        ]

    def get_created_at_formatted(self, obj):
        request = self.context.get('request')

        # Исправлено: убраны скобки () после is_authenticated
        if request and request.user.is_authenticated:
            user_tz = timezone.get_current_timezone()
            local_time = obj.created_at.astimezone(user_tz)
        else:
            local_time = obj.created_at

        return formats.date_format(local_time, 'DATETIME_FORMAT')


class PostDetailSerializer(serializers.ModelSerializer):
    """
    Docstring for PostDetailSerializer
    """
    author = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    created_at_formatted = serializers.SerializerMethodField()
    updated_at_formatted = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'body', 'author',
            'category', 'tags', 'status', 
            'created_at', 'created_at_formatted',
            'updated_at_formatted',
            'updated_at', 'comments'
        ]
    
    def get_created_at_formatted(self, obj):
        request = self.context.get('request')

        if request and request.user.is_authenticated:
            user_tz = timezone.get_current_timezone()
            local_time = obj.created_at.astimezone(user_tz)
        else:
            local_time = obj.created_at
        return formats.date_format(local_time, 'DATETIME_FORMAT')

    def get_updated_at_formatted(self, obj):
        request = self.context.get('request')

        if request and request.user.is_authenticated:
            user_tz = timezone.get_current_timezone()
            local_time = obj.updated_at.astimezone(user_tz)
        else:
            local_time = obj.updated_at
        return formats.date_format(local_time, 'DATETIME_FORMAT')


class PostCreateUpdateSerializer(serializers.ModelSerializer):
    """for create/update post"""

    class Meta:
        model = Post
        fields = ['title', 'slug', 'body', 'category', 'tags', 'status']