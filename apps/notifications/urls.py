from django.urls import include, path
from rest_framework.routers import DefaultRouter
from apps.notifications.views import NotificationViewSet, notifications_count_view

router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('notifications/count/', notifications_count_view, name='notification-count'),
    path('', include(router.urls)),
    
]