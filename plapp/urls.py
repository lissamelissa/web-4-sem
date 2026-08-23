# plapp/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Главный дашборд
    path('dashboard/<int:user_id>/', views.dashboard_view, name='dashboard'),
    path('', views.home_view, name='home'),
    # Задачи
    path('task/<int:pk>/', views.task_detail_view, name='task_detail'),
    path('task/add/<int:user_id>/', views.task_create_view, name='task_create'),
    path('task/<int:pk>/edit/', views.task_edit_view, name='task_edit'),
    path('task/<int:pk>/delete/', views.task_delete_view, name='task_delete'),

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