from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.blog.views import PostViewSet, post_stream_view
from apps.blog.stats_views import stats_view

router = DefaultRouter()
router.register(r'posts', PostViewSet, basename='post')

urlpatterns = [
    # Этот маршрут должен быть ПЕРВЫМ. 
    # Он перехватит запрос до того, как роутер решит, что "stream" — это slug поста.
    path('posts/stream/', post_stream_view, name='post-stream'),
    
    path('stats/', stats_view, name='stats'),
    
    # Роутер идет в конце
    path('', include(router.urls)),
]