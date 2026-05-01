from ..base import *

# Production settings
DEBUG = False

# ALLOWED_HOSTS - важно для nginx proxy
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*']  # В реальном проде указывай конкретные домены

# Database (SQLite для демо, в реальном проде PostgreSQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db' / 'db.sqlite3',
    }
}

# Static files (собираются в staticfiles/)
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_URL = '/static/'

# Media files
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'

# Security (для реального прода раскомментируй)
# SECURE_SSL_REDIRECT = True
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
# SECURE_HSTS_SECONDS = 31536000
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True
