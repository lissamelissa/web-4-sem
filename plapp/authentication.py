from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import user as UserModel


class CustomUserSessionAuthentication(BaseAuthentication):
    """
    Аутентификация API поверх УЖЕ существующей сессионной системы приложения.

    Модель `user` — своя (не django.contrib.auth.User), поэтому обычный
    SessionAuthentication из DRF не подходит. views.login_view /
    views.register_view кладут id пользователя в request.session
    ['custom_user_id'] — этим же ключом пользуется и API: POST /api/auth/login/
    делает то же самое, и дальше Postman/браузер просто переиспользуют cookie
    сессии для всех запросов к /api/.

    Примечание (для ТЗ): в учебных целях CSRF-проверка для API не включается
    (DRF сам оборачивает APIView в csrf_exempt) — в продакшене для
    cookie-based аутентификации так делать нельзя, нужен либо CSRF-токен,
    либо токен/JWT-аутентификация.
    """

    def authenticate(self, request):
        user_id = request.session.get('custom_user_id')
        if not user_id:
            return None
        try:
            current_user = UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            raise AuthenticationFailed('Пользователь текущей сессии не найден.')
        return (current_user, None)
