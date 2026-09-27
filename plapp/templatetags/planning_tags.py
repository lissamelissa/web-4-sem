# templatetags/planning_tags.py
from django import template
from django.utils import timezone
from ..models import tasks

register = template.Library()

@register.simple_tag
def current_time_str(format_string="%H:%M"):
    return timezone.now().strftime(format_string)

# ИСПРАВЛЕНИЕ: Тег теперь ищет в контексте 'current_user' (нашу модель)
@register.simple_tag(takes_context=True)
def welcome_user(context):
    custom_user = context.get('current_user')
    if custom_user:
        return f"Рады видеть вас снова, {custom_user.username}!"
    return "Привет, Гость! Продуктивного планирования!"

@register.simple_tag
def get_high_priority_tasks(user_obj):
    # Сюда прилетит правильный объект кастомного юзера
    return tasks.objects.filter(user_id=user_obj, priority='high', status='active')[:3]
