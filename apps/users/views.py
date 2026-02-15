import logging
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.utils.decorators import method_decorator
from apps.users.serializers import RegisterSerializer, UserSerializer
from apps.users.ratelimit import rate_limit

logger = logging.getLogger(__name__)


class RegisterViewSet(viewsets.ViewSet):
    """Registrantion for new user"""
    permission_classes = [AllowAny] 

    @rate_limit(key_prefix='register', max_requests=5, window_seconds=60)
    def create(self, request):
        email = request.data.get('email')
        logger.info('registration attempt for email: %s', request.data.get('email'))
        
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            #create jwt token
            refresh = RefreshToken.for_user(user)

            logger.info('User is registered %s', user.email)

            return Response({
                'user': UserSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_201_CREATED)
        logger.warning('Registration failed for email %s, error %s', 
                       request.data.get('email'), serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RateLimitedTokenObtainPairView(TokenObtainPairView):
    """
    TokenObtainPairView with rate limiting
    """
    @rate_limit(key_prefix='login', max_requests=10, window_seconds=60)
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
        