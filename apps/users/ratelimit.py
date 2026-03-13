from functools import wraps
import redis
from django.conf import settings
from rest_framework.response import Response
from rest_framework import status

# connection to redis
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True
)

def rate_limit(key_prefix: str, max_requests: int, window_seconds: int):
    """
    Decorator for limiting the number of requests

    :param key_prefix: Redis key prefix (e.g., 'register')
    :param max_requests: Maximum number of requests
    :param window_seconds: Time window in seconds
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            # Универсальный поиск объекта request в переданных аргументах
            request = None
            for arg in args:
                if hasattr(arg, 'META'):
                    request = arg
                    break
            
            if request is None:
                request = kwargs.get('request')

            if request:
                # Let's determine the key (by IP or by user)
                if hasattr(request.user, 'id') and request.user.is_authenticated:
                    identifier = f'user_{request.user.id}'
                else:
                    # GET IP address
                    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                    if x_forwarded_for:
                        ip = x_forwarded_for.split(',')[0]
                    else:
                        ip = request.META.get('REMOTE_ADDR')
                    identifier = f'ip_{ip}'
                
                # Generating a key for Redis
                redis_key = f'ratelimit:{key_prefix}:{identifier}'

                # we get the current number of requests
                current = redis_client.get(redis_key)

                if current is None:
                    # First request - install the meter
                    redis_client.setex(redis_key, window_seconds, 1)
                elif int(current) >= max_requests:
                    # limit exceeded
                    return Response(
                        {'detail': 'Too many requests. Try again later.'},
                        status=status.HTTP_429_TOO_MANY_REQUESTS
                    )
                else:
                    # increase the counter
                    redis_client.incr(redis_key)

            # perform an original function
            return view_func(*args, **kwargs)
        return wrapper
    return decorator