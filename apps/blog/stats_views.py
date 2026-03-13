import asyncio
import logging
import httpx
from asgiref.sync import async_to_sync  
from django.db.models import Count
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from .models import Post, Category, Tag, Comment
from .serializers import PostListSerializer, CategorySerializer, TagSerializer
from apps.users.models import User

logger = logging.getLogger(__name__)

@extend_schema(
    tags=['Stats'],
    summary='Get blog statistics',
    description="""
    Retrieve statistics about the blog, including total counts of posts, comments, and categories, as well as current exchange rates and time in Almaty.

    **Data from the database:**
    - Total number of posts
    - Total number of comments
    - Total number of categories

    **Data from external APIs:**
    - Current exchange rates for USD to KZT, RUB, and EUR
    - Current time in Almaty 

    **Asynchronous processing:**
    - Two external API calls are made concurrently to optimize response time.
    - Proper error handling is implemented to ensure that if one API call fails, the other data can still be returned.
    - Logging is included to track the flow of data and any potential issues during the API calls.

    ** Authentication:**
    - This endpoint is publicly accessible and does not require authentication.    
    """,
    responses={
        200: OpenApiResponse(
            description='Successful Response',
            examples=[
                OpenApiExample(
                    'Successful Response',
                    value={
                        'blog': {
                            'total_posts': 100,
                            'total_comments': 250,
                            'total_categories': 5
                        },
                        'exchange_rates': {
                            'KZT': 425.50,
                            'RUB': 75.30,
                            'EUR': 0.85
                        },
                        'current_time': '2024-06-01T12:00:00+06:00'
                    }
                )
            ]
        ),
        500: OpenApiResponse(
            description='Error Response',
            examples=[
                OpenApiExample(
                    'Error Response',
                    value={'error': 'Failed to fetch statistics'}
                )
            ]
        )
    }
)
@api_view(['GET'])
@permission_classes([AllowAny])
def stats_view(request): # <-- Убрали async
    
    logger.info('statistics request')

    # Обычные синхронные запросы к БД (без await)
    blog_stats = {
        'total_posts': Post.objects.count(),
        'total_comments': Comment.objects.count(),
        'total_categories': Category.objects.count(),
    }

    # Оборачиваем асинхронные HTTP-запросы во внутреннюю функцию
    async def fetch_external_data():
        async with httpx.AsyncClient(timeout=10.0) as client:
            return await asyncio.gather(
                fetch_exchange_rate(client),
                fetch_almaty_time(client),
                return_exceptions=True
            )

    try:
        # Запускаем нашу асинхронную функцию синхронно с помощью async_to_sync
        exchange_data, time_data = async_to_sync(fetch_external_data)()
        
        # Проверяем на ошибки
        if isinstance(exchange_data, Exception):
            logger.error(f"Failed to fetch exchange rate: {exchange_data}")
            exchange_data = None
        if isinstance(time_data, Exception):
            logger.error('Failed to fetch time: %s', time_data)
            time_data = None

        response_data = {
            'blog': blog_stats,
            'exchange_rates': exchange_data,
            'current_time': time_data or None
        }
        
        logger.info('statistics response: %s', response_data)
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error in stats_view: {e}")
        return Response({'error': 'Failed to fetch statistics'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Вспомогательные функции оставляем асинхронными
async def fetch_exchange_rate(client: httpx.AsyncClient) -> dict:
    """Fetch exchange rates from external API"""
    logger.info('Fetching exchange rates')

    url = 'https://api.exchangerate-api.com/v4/latest/USD'

    response = await client.get(url)
    response.raise_for_status()
    data = response.json()
    rates = data.get('rates', {})

    result = {
        'KZT': rates.get('KZT'),
        'RUB': rates.get('RUB'),
        'EUR': rates.get('EUR'),
    }
    logger.debug('Exchange rates fetched: %s', result)
    return result

async def fetch_almaty_time(client: httpx.AsyncClient) -> str:
    """Fetch current time in Almaty from external API"""
    logger.info('Fetching current time in Almaty')

    url = 'http://worldtimeapi.org/api/timezone/Asia/Almaty'

    response = await client.get(url)
    response.raise_for_status()
    data = response.json()
    current_time = data.get('datetime')

    logger.debug('Current time in Almaty fetched: %s', current_time)
    return current_time