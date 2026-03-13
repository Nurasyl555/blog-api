from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.blog.views import PostViewSet
from apps.blog.stats_views import stats_view
router = DefaultRouter()
router.register(r'posts', PostViewSet, basename='post')

urlpatterns = [
    path('stats/', stats_view, name='stats'),
    path('', include(router.urls)),
]