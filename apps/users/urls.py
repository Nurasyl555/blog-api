from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from apps.users.views import RegisterViewSet, RateLimitedTokenObtainPairView, UserPreferencesViewSet
urlpatterns = [
    path('register/',
         RegisterViewSet.as_view({'post': 'create'}), name='register'),
    path('token/', 
         RateLimitedTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(),
         name='token_refresh'),
     
     path('preferences/language/', UserPreferencesViewSet.as_view({'patch': 'update_language'}),
          name='update_language'),
     path('preferences/timezone/', UserPreferencesViewSet.as_view({'patch': 'update_timezone'}),
          name='update_timezone'),
]