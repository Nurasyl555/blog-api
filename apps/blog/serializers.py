from rest_framework import serializers
from apps.blog.models import Category, Tag, Post, Comment
from apps.users.serializers import UserSerializer


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug']


class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'post', 'author', 'body', 'created_at']
        read_only_fields = ['id', 'created_at', 'post']


class PostListSerializer(serializers.ModelSerializer):
    """"For list of Post"""
    author = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    comment_count = serializers.IntegerField(source='comments.count', read_only=True)

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'author', 'category',
            'tags', 'status', 'created_at', 'comment_count'
        ]


class PostDetailSerializer(serializers.ModelSerializer):
    """
    Docstring for PostDetailSerializer
    """
    author = UserSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        fields = [
            'id', 'title', 'slug', 'body', 'author',
            'category', 'tags', 'status', 'created_at',
            'updated_at', 'comments'
        ]


class PostCreateUpdateSerializer(serializers.ModelSerializer):
    """for create/update post"""

    class Meta:
        model = Post
        fields = ['title', 'slug', 'body', 'category', 'tags', 'status']