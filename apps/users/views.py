import logging
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import translation
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.utils.translation import gettext_lazy as _
from django.utils.decorators import method_decorator
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from apps.users.serializers import (
    RegisterSerializer, 
    UserSerializer,
    LanguageSerializer,
    TimezoneSerializer,
)
from apps.users.ratelimit import rate_limit

logger = logging.getLogger(__name__)


class RegisterViewSet(viewsets.ViewSet):
    """Registrantion for new user"""
    permission_classes = [AllowAny] 

    @extend_schema(
            tags=['Auth'],
            summary='Register a new user',
            description="""
            Create a new user account and receive JWT tokens

            **Requirement:**
            - `email` must be unique and valid
            - `password` must be at least 6 characters and match `password_confirm`
            - `language` must be one of the supported languages 

            **Side effects:**
            - Sends a welcome email to the new user in their selected language
            - Rate limited to 5 requests per minute per IP to prevent abuse

            **Language behavior:**
            - Email content is localized based on the `language` field provided during registration. Supported languages are defined in the project settings.
            - Validation errors and responses are also localized based on the `language` field or ?lang parameter, Accept-Language header.
            """,
            request=RegisterSerializer,
            responses={
                201: OpenApiResponse(
                    description='User registered successfully',
                    examples=[
                        OpenApiExample(
                            'Successful Registration',
                            value={
                                'user': {
                                    'id': 1,
                                    'email': 'user@example.com',
                                    'first_name': 'John',
                                    'last_name': 'Doe',
                                    'language': 'en',
                                    'timezone': 'UTC',
                                },
                                'tokens': {
                                    'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                                    'access': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
                                }
                            }
                        )
                    ]
                ),
                400: OpenApiResponse(
                    description='Invalid input data',
                    examples=[
                        OpenApiExample(
                            'Password Mismatch',
                            value={
                                'password': ["the passwords don't match"]
                            }
                        ),OpenApiExample(
                            'Email Already Exists',
                            value={
                                'email': ["A user with this email already exists."]}
                            )
                    ]
                ),
                429: OpenApiResponse(
                    description='Too Many Requests',
                    examples=[
                        OpenApiExample(
                            'Rate Limit Exceeded',
                            value={
                                'detail': 'Request was throttled. Expected available in 60 seconds.'
                            }
                        )
                    ]
                )
            },
            examples=[
                OpenApiExample(
                    'Registration Request',
                    value={
                        'email': 'user@example.com',
                        'password': 'securepassword',
                        'password_confirm': 'securepassword',
                        'first_name': 'John',
                        'last_name': 'Doe',
                        'language': 'en'
                    }
                )
            ]
        )
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

            # Send welcome email
            self._send_welcome_email(user)

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
    
    def _send_welcome_email(self, user):
        """Send welcome email to new user in their language"""
        # Activate user's language for email content
        with translation.override(user.language):
            subject = render_to_string('emails/welcome/subject.txt', {'user': user}).strip()
            body = render_to_string('emails/welcome/body.txt', {'user': user})

            try:
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                logger.info('Welcome email sent to %s in the %s language', user.email, user.language)
            except Exception as e:
                logger.error('Failed to send welcome email to %s: %s', user.email, str(e))

class RateLimitedTokenObtainPairView(TokenObtainPairView):
    """
    TokenObtainPairView with rate limiting
    """

    @extend_schema(
        tags=['Auth'],
        summary='Obtain JWT tokens',
        description="""
            Obtain access and refresh JWT tokens by providing valid user credentials.
            
            **Side effects:**
            - Rate limited to 10 requests per minute per IP to prevent brute-force attacks

            **Response:**
            - acsess token is valid for 5 minutes
            - refresh token is valid for 1 day
            """,
        examples=[
            OpenApiExample(
                'Login Example',
                value={
                    'email': 'user@example.com',
                    'password': 'securepassword'
                }
            )
        ],
        responses={
            200: OpenApiResponse(
                description='Tokens obtained successfully',
                examples=[
                    OpenApiExample(
                        'Successful Login',
                        value={
                            'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                            'access': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
                        }
                    )
                ]
            ),
            401: OpenApiResponse(
                description='Invalid credentials',
                examples=[
                    OpenApiExample(
                        'Invalid Login',
                        value={
                            'detail': 'No active account found with the given credentials'
                        }
                    )
                ]
            ),
            429: OpenApiResponse(
                description='Too Many Requests',
                examples=[
                    OpenApiExample(
                        'Rate Limit Exceeded',
                        value={
                            'detail': 'Request was throttled. Expected available in 60 seconds.'
                        }
                    )
                ]
            )
        }
    )
    @method_decorator(
        rate_limit(key_prefix='login', max_requests=10, window_seconds=60),
        #name='post'
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
        
class UserPreferencesViewSet(viewsets.ViewSet):
    """Manage user settings"""
    permission_classes=[IsAuthenticated]

    @extend_schema(
            tags=['Auth'],
            summary='Update user preferences',
            description="""
            Update user language and timezone preferences.

            **Validation:**
            - `language` must be one of the supported languages defined in the project settings (en, kk, ru).
            - Non-valid language codes will result in a 400 Bad Request with a message indicating the supported languages.

            **authorization required:** Bearer JWT token

            **Language behavior:**
            - The response messages are localized based on the user's current language preference. If the user updates
            - Welcome email content is localized based on the updated `language` field. Supported languages are defined in the project settings.    
            """,
            request=LanguageSerializer,
            responses={
                200: OpenApiResponse(
                    description='Successfully updated language',
                    examples=[
                        OpenApiExample(
                            'Success Example',
                            value={
                                'message': 'Language successfully updated',
                                'language': 'en',
                            }
                        )
                    ]
                ),
                400: OpenApiResponse(description='Invalid language code'),
                401: OpenApiResponse(description='Unauthorized'),
            },
            examples=[
                OpenApiExample(
                    'Update Language Request',
                    value={
                        'language': 'kk'
                    }
                )
            ]
        )
    @action(detail=False, methods=['patch'], url_path='language')
    def update_language(self, request):
        """Patch /api/auth/preferences/language/ - update language"""
        serializer = LanguageSerializer(data=request.data)

        if serializer.is_valid():
            request.user.language = serializer.validated_data['language']
            request.user.save()

            logger.info('User %s change language to %s',
                        request.user.email, request.user.language)
            
            return Response({
                'message': _('Language sucsecfully update'),
                'language': request.user.language
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
            tags=['Auth'],
            summary='Update user timezone',
            description="""
            Update user timezone preference.

            **Validation:**
            - `timezone` must be a valid timezone string recognized by the pytz library (e.g., "UTC", "America/New_York", "Asia/Almaty").
            - Invalid timezone strings will result in a 400 Bad Request with a message indicating the error.

            **authorization required:** Bearer JWT token

            **Language behavior:**
            - The response messages are localized based on the user's current language preference. If the user updates
            - Welcome email content is localized based on the updated `language` field. Supported languages are defined in the project settings.    
            """,
            request=TimezoneSerializer,
            responses={
                200: OpenApiResponse(
                    description='Successfully updated timezone',
                    examples=[
                        OpenApiExample(
                            'Success Example',
                            value={
                                'message': 'Timezone successfully updated',
                                'timezone': 'UTC'
                            }
                        )
                    ]
                ),
                400: OpenApiResponse(description='Invalid timezone string'),
                401: OpenApiResponse(description='Unauthorized'),
            },
            examples=[
                OpenApiExample(
                    'Update Timezone Request',
                    value={
                        'timezone': 'Asia/Almaty'
                    }
                )
            ]
    )
    @action(detail=False, methods=['patch'], url_path='timezone')
    def update_timezone(self, request):
        """PATCH /api/auth/preferences/timezone/ - update timezone"""
        serializer = TimezoneSerializer(data=request.data)

        if serializer.is_valid():
            request.user.timezone = serializer.validated_data['timezone']
            request.user.save()

            logger.info('User %s change timezone to %s',
                        request.user.email, request.user.timezone)
            
            return Response({
                'message': _('Timezone successfully update'),
                'timezone': request.user.timezone
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)