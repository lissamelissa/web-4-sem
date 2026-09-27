from django.contrib.auth.hashers import check_password, make_password
from django.db.models import Case, Count, ExpressionWrapper, F, FloatField, Q, Value, When
from rest_framework import permissions as drf_permissions
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from .filters import FinanceFilter, GoalFilter, TaskFilter
from .models import (
    favorites,
    finance_categories,
    finances,
    goals,
    task_categories,
    tasks,
)
from .models import user as UserModel
from .permissions import IsAdminRole, IsOwnerOrAdmin
from .serializers import (
    FinanceCategorySerializer,
    FinanceSerializer,
    GoalSerializer,
    TaskCategorySerializer,
    TaskSerializer,
    UserSerializer,
)


# ---------------------------------------------------------------------------
# Аутентификация через API (тот же request.session, что и у обычных views —
# см. plapp/authentication.py). Нужна отдельно от views.py, потому что там
# обработчики отдают HTML-редиректы, а API должно отвечать JSON.
# ---------------------------------------------------------------------------

class ApiRegisterView(APIView):
    permission_classes = [drf_permissions.AllowAny]

    def post(self, request):
        data = request.data
        email = data.get('email', '')
        username = data.get('username', '')
        password = data.get('password', '')

        if not username or not email or not password:
            return Response({'detail': 'username, email и password обязательны.'}, status=400)
        if UserModel.objects.filter(email=email).exists():
            return Response({'email': 'Пользователь с таким email уже существует.'}, status=400)

        new_user = UserModel.objects.create(
            username=username,
            email=email,
            password_hash=make_password(password),
        )
        request.session['custom_user_id'] = new_user.id
        return Response(UserSerializer(new_user).data, status=201)


class ApiLoginView(APIView):
    permission_classes = [drf_permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        try:
            current_user = UserModel.objects.get(username=username)
        except UserModel.DoesNotExist:
            return Response({'detail': 'Неверное имя или пароль.'}, status=400)
        if not check_password(password, current_user.password_hash):
            return Response({'detail': 'Неверное имя или пароль.'}, status=400)

        request.session['custom_user_id'] = current_user.id
        return Response(UserSerializer(current_user).data)


class ApiLogoutView(APIView):
    def post(self, request):
        request.session.pop('custom_user_id', None)
        return Response(status=204)


class MeView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


# ---------------------------------------------------------------------------
# Справочники: чтение доступно любому авторизованному, изменение — только
# роли admin (см. IsAdminRole и раздел "Роли" в ТЗ).
# ---------------------------------------------------------------------------

class TaskCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = TaskCategorySerializer

    def get_queryset(self):
        # Аннотация (п.5 задания): количество задач в каждой категории
        # считается одним JOIN-запросом (annotate), а не N дополнительными
        # запросами (по одному на категорию) при обращении к tasks_count.
        return task_categories.objects.annotate(
            tasks_count=Count('tasks', distinct=True)
        ).order_by('name')

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminRole()]
        return [drf_permissions.IsAuthenticated()]


class FinanceCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = FinanceCategorySerializer
    queryset = finance_categories.objects.all().order_by('name')

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAdminRole()]
        return [drf_permissions.IsAuthenticated()]


# ---------------------------------------------------------------------------
# Задачи: обычный пользователь видит и правит только свои, admin — все.
# ---------------------------------------------------------------------------

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [drf_permissions.IsAuthenticated, IsOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = TaskFilter
    ordering_fields = ['due_date', 'priority', 'created_at']

    def get_queryset(self):
        current_user = self.request.user
        # select_related (п.3 задания): category_id и user_id тянутся одним
        # JOIN'ом. Без этого TaskSerializer.category_detail и is_favorite
        # дали бы N+1 запросов — по два лишних на КАЖДУЮ задачу в списке.
        qs = tasks.objects.select_related('category_id', 'user_id')
        if current_user.role == UserModel.Role.ADMIN:
            return qs.order_by('-created_at')
        return qs.filter(user_id=current_user).order_by('-created_at')

    def perform_create(self, serializer):
        # Владелец задачи — всегда текущий пользователь, а не то, что придёт
        # в теле запроса (иначе можно было бы создать задачу от чужого лица).
        serializer.save(user_id=self.request.user)

    @action(detail=True, methods=['post'], url_path='toggle-favorite')
    def toggle_favorite(self, request, pk=None):
        task = self.get_object()
        favorite, created = favorites.objects.get_or_create(user=request.user, task=task)
        if not created:
            favorite.delete()
            return Response({'is_favorite': False})
        return Response({'is_favorite': True})


# ---------------------------------------------------------------------------
# Цели: та же логика владения, что и у задач.
# ---------------------------------------------------------------------------

class GoalViewSet(viewsets.ModelViewSet):
    serializer_class = GoalSerializer
    permission_classes = [drf_permissions.IsAuthenticated, IsOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_class = GoalFilter

    def get_queryset(self):
        current_user = self.request.user
        qs = goals.objects.select_related('user').prefetch_related(
            'category_links__category'
        ).annotate(
            # Аннотация (п.5): процент выполнения цели считается на уровне
            # БД, с защитой от деления на ноль через Case/When, а не в
            # Python-цикле по каждому объекту после выборки.
            progress_percent=Case(
                When(target_value=0, then=Value(0.0)),
                default=ExpressionWrapper(
                    F('current_value') * 100.0 / F('target_value'),
                    output_field=FloatField(),
                ),
                output_field=FloatField(),
            )
        )
        if current_user.role == UserModel.Role.ADMIN:
            return qs.order_by('-created_at')
        return qs.filter(user=current_user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ---------------------------------------------------------------------------
# Финансы: та же логика владения.
# ---------------------------------------------------------------------------

class FinanceViewSet(viewsets.ModelViewSet):
    serializer_class = FinanceSerializer
    permission_classes = [drf_permissions.IsAuthenticated, IsOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_class = FinanceFilter

    def get_queryset(self):
        current_user = self.request.user
        qs = finances.objects.select_related('category', 'user')
        if current_user.role == UserModel.Role.ADMIN:
            return qs.order_by('-operation_date')
        return qs.filter(user=current_user).order_by('-operation_date')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ---------------------------------------------------------------------------
# Сводная статистика по пользователям — привилегия администратора.
# ---------------------------------------------------------------------------

class AdminStatsView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        # Аннотация (п.5): три агрегата на каждого пользователя одним
        # запросом с JOIN'ами (Count с filter=Q(...) для условного счёта),
        # вместо отдельного запроса на пользователя в цикле.
        stats = UserModel.objects.annotate(
            total_tasks=Count('tasks', distinct=True),
            completed_tasks=Count(
                'tasks', filter=Q(tasks__status=tasks.Status.COMPLETED), distinct=True
            ),
            total_goals=Count('goal', distinct=True),
        ).values('id', 'username', 'role', 'total_tasks', 'completed_tasks', 'total_goals')
        return Response(list(stats))
