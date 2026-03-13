from django.utils import translation, timezone
from django.conf import settings
import pytz


class UserLanguageTimezoneMiddleware:
    """
    MIddleware for define language and timezone users

    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # define language
        lang = None

        #1 if user is au
        if request.user.is_authenticated:
            lang = request.user.language

            try :
                user_tz = pytz.timezone(request.user.timezone)
                timezone.activate(user_tz)
            except pytz.exceptions.UnknownTimeZoneError:
                timezone.activate(pytz.UTC)

        # Parametr ?lang = in URl
        if not lang:
            lang = request.GET.get('lang')

        
        if lang and lang in [l[0] for l in settings.LANGUAGES]:
            translation.activate(lang)
            request.lANGUAGE_CODE = lang
        
        response = self.get_response(request)

        translation.deactivate()

        return response
         