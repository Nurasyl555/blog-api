# settings/conf.py
from decouple import config

SECRET_KEY = config('BLOG_SECRET_KEY', default='django-insecure-temporary-key-change-this')
DEBUG = config('BLOG_DEBUG', default=True, cast=bool)