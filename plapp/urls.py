# planning/urls.py
from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Главный дашборд (требует ID пользователя, например: /dashboard/1/)
    path('dashboard/<int:user_id>/', views.dashboard_view, name='dashboard'),

    # Детальная страница задачи (используется в get_absolute_url, например: /task/5/)
    path('task/<int:pk>/', views.task_detail_view, name='task_detail'),

    # Авторизация и регистрация
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)