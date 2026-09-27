# plapp/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),

    # Главная страница (виджеты)
    path('home/<int:user_id>/', views.home_page_view, name='home_page'),

    # Полноэкранный календарь
    path('calendar/<int:user_id>/', views.calendar_view, name='calendar_view'),

    # Избранное
    path('favorite/toggle/<int:user_id>/<int:pk>/', views.toggle_favorite_view, name='toggle_favorite'),

    # Дашборд
    path('dashboard/<int:user_id>/', views.dashboard_view, name='dashboard'),

    # Задачи
    path('task/<int:pk>/', views.task_detail_view, name='task_detail'),
    path('task/add/<int:user_id>/', views.task_create_view, name='task_create'),
    path('task/<int:pk>/edit/', views.task_edit_view, name='task_edit'),
    path('task/<int:pk>/delete/', views.task_delete_view, name='task_delete'),

    # Таблица задач + bulk-действия
    path('tasks-table/<int:user_id>/', views.tasks_table_view, name='tasks_table'),
    path('tasks-table/<int:user_id>/bulk/', views.tasks_bulk_action_view, name='tasks_bulk_action'),

    # Таблица финансов
    path('finances-table/<int:user_id>/', views.finances_table_view, name='finances_table'),
    path('finance/add/<int:user_id>/', views.finance_create_view, name='finance_create'),
    path('finance/<int:pk>/edit/', views.finance_edit_view, name='finance_edit'),
    path('finance/<int:pk>/delete/', views.finance_delete_view, name='finance_delete'),

    # Цели
    path('goals/<int:user_id>/', views.goals_list_view, name='goals_list'),
    path('goals/add/<int:user_id>/', views.goal_create_view, name='goal_create'),
    path('goals/<int:pk>/edit/', views.goal_edit_view, name='goal_edit'),
    path('goals/<int:pk>/delete/', views.goal_delete_view, name='goal_delete'),

    # Авторизация и регистрация
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]
