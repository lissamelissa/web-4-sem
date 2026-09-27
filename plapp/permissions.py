from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """
    Доступ только пользователям с ролью admin (см. user.Role в models.py).
    Используется там, где действие — привилегия администратора: управление
    справочниками категорий, сводная статистика по всем пользователям и т.п.
    """

    message = "Действие доступно только администратору."

    def has_permission(self, request, view):
        current_user = request.user
        return bool(
            current_user
            and getattr(current_user, 'is_authenticated', False)
            and current_user.role == current_user.Role.ADMIN
        )


class IsOwnerOrAdmin(BasePermission):
    """
    Владелец объекта (задачи/цели/финансовой записи) может читать и изменять
    только свои данные; администратор — видит и модерирует данные всех
    пользователей. Имя поля-владельца в разных моделях разное (`user_id` у
    tasks, `user` у goals/finances), поэтому проверяем оба варианта.
    """

    owner_field_candidates = ('user_id', 'user')

    def has_object_permission(self, request, view, obj):
        current_user = request.user
        if not (current_user and getattr(current_user, 'is_authenticated', False)):
            return False
        if current_user.role == current_user.Role.ADMIN:
            return True
        for field in self.owner_field_candidates:
            if hasattr(obj, field):
                return getattr(obj, field) == current_user
        return False
