from django.utils import translation
from django.conf import settings

class LanguageQueryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        lang_code = request.GET.get('lang')
        supported_languages = [lang[0] for lang in settings.LANGUAGES]

        # Если передали ?lang= и он есть в списке доступных (ru, kk, en)
        if lang_code and lang_code in supported_languages:
            # Безопасно оборачиваем весь ответ в нужный язык
            with translation.override(lang_code):
                request.LANGUAGE_CODE = lang_code
                return self.get_response(request)

        # Если ?lang= нет, отдаем работу другим Middleware (твоему UserLanguageTimezoneMiddleware)
        return self.get_response(request)