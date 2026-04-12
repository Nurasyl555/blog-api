from rest_framework import serializers
from apps.notifications.models import Notification
from apps.blog.serializers import CommentSerializer
from apps.users.serializers import UserSerializer

class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model"""
    recipient = UserSerializer(read_only=True)
    comment = CommentSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'recipient', 'comment', 'is_read', 'created_at']
        read_only_fields = ['id', 'created_at']