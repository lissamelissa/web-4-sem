from django.urls import path
from rest_framework.routers import DefaultRouter

from .api_views import (
    AdminStatsView,
    ApiLoginView,
    ApiLogoutView,
    ApiRegisterView,
    FinanceCategoryViewSet,
    FinanceViewSet,
    GoalViewSet,
    MeView,
    TaskCategoryViewSet,
    TaskViewSet,
)

router = DefaultRouter()
router.register('tasks', TaskViewSet, basename='api-task')
router.register('task-categories', TaskCategoryViewSet, basename='api-task-category')
router.register('goals', GoalViewSet, basename='api-goal')
router.register('finances', FinanceViewSet, basename='api-finance')
router.register('finance-categories', FinanceCategoryViewSet, basename='api-finance-category')

urlpatterns = [
    path('auth/register/', ApiRegisterView.as_view(), name='api-register'),
    path('auth/login/', ApiLoginView.as_view(), name='api-login'),
    path('auth/logout/', ApiLogoutView.as_view(), name='api-logout'),
    path('auth/me/', MeView.as_view(), name='api-me'),
    path('admin/stats/', AdminStatsView.as_view(), name='api-admin-stats'),
] + router.urls
