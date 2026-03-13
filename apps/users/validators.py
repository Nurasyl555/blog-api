import pytz
from rest_framework import serializers
from django.conf import settings
from django.utils.translation import gettext_lazy as _

def validate_language(value: str) -> str:
    """
    Check validate language
    """
    supported_languages = [lang[0] for lang in settings.LANGUAGES]
    if value not in supported_languages:
        error_msg = _('language "{value}" not supported. accessible: {accessible}')
        raise serializers.ValidationError(
            error_msg.format(value=value, accessible=", ".join(supported_languages))
        )
    return value

def validate_timezone(value: str) -> str:
    """Check timezone is valid"""
    if value not in pytz.all_timezones:
        error_msg = _('Timezone "{value}" wrong. Use IANA timezone')
        raise serializers.ValidationError(error_msg.format(value=value))
    return value
