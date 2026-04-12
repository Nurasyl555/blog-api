import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_spectacular.utils import extend_schema, OpenApiExample

from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer

logger = logging.getLogger(__name__)

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """Views for notifications app
        list and retrieve
    """

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """return notifications for the current user"""
        return Notification.objects.filter(recipient=self.request.user)

    @extend_schema(
        tags=['Notifications'],
        summary='list of notifications',
        description="""
            Returns a list of notifications for the current user.
            **Requires authentication.** Bearer JWT token
            **Paginated.** Default page size is 10. 
        """,
        responses={
            200: NotificationSerializer(many=True),
            401: 'Unauthorized. Authentication credentials were not provided or are invalid.'}
    )
    def list(self, request, *args, **kwargs):
        """List notifications for the current user"""
        return super().list(request, *args, **kwargs)
    
    @extend_schema(
        tags=['Notifications'],
        summary='mark notification as read',
        description="""
            Marks a notification as read.
            **Requires authentication.** Bearer JWT token
        """,
        request=None,
        responses={
            200: OpenApiExample(
                'Success',
                value={'message': 'Notification marked as read', 'updated_count': 5}
            ),
            401: 'Unauthorized'
        }
    )
    @action(detail=False, methods=['post'], url_path='read')
    def mark_all_read(self, request):
        """Mark all notifications as read for the current user"""
        updated_count = Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        logger.info('User %s marked %d notifications as read', request.user.email, updated_count)
        return Response({'message': 'Notification marked as read', 'updated_count': updated_count}, status=status.HTTP_200_OK)
    
@extend_schema(
    tags=['Notifications'],
    summary='Number of unread notifications',
    description="""
    Returns the number of unread notifications for the current user
    """,
    responses={
        200: OpenApiExample(
            'Success',
            value={'unread_count': 3}
        ),
        401: 'Unauthorized'
    }
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications_count_view(request):
    """Returns the number of unread notifications for the current user"""
    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    logger.debug('User %s has %d unread notifications', request.user.email, unread_count)
    return Response({'unread_count': unread_count}, status=status.HTTP_200_OK)