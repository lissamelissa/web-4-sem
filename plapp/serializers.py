from django.utils import timezone
from rest_framework import serializers

from .models import (
    user,
    task_categories,
    tasks,
    goals,
    goal_categories,
    finance_categories,
    finances,
    favorites,
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = user
        fields = ['id', 'username', 'email', 'role', 'created_at']
        read_only_fields = ['id', 'role', 'created_at']


# --- КАТЕГОРИИ ЗАДАЧ ---

class TaskCategorySerializer(serializers.ModelSerializer):
    # Пункт 4.1 (SerializerMethodField): количество задач в категории.
    # TaskCategoryViewSet.get_queryset() уже аннотирует tasks_count через
    # annotate(Count(...)) одним JOIN-запросом — тут просто отдаём готовое
    # значение; .count() ниже — лишь safety-fallback, если сериализатор
    # вызвали на неаннотированном объекте (например, в GoalSerializer).
    tasks_count = serializers.SerializerMethodField()

    class Meta:
        model = task_categories
        fields = ['id', 'name', 'color', 'tasks_count']

    def get_tasks_count(self, obj):
        if hasattr(obj, 'tasks_count'):
            return obj.tasks_count
        return obj.tasks.count()

    def validate_name(self, value):
        # Бизнес-правило: название категории уникально без учёта регистра.
        qs = task_categories.objects.filter(name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Категория с таким названием уже существует.")
        return value


# --- ЗАДАЧИ ---

class TaskSerializer(serializers.ModelSerializer):
    category_detail = TaskCategorySerializer(source='category_id', read_only=True)

    # Пункт 4.1 (SerializerMethodField): вычисляемые поля, которых нет
    # напрямую в модели.
    is_overdue = serializers.SerializerMethodField()
    is_favorite = serializers.SerializerMethodField()

    class Meta:
        model = tasks
        fields = [
            'id', 'title', 'description', 'priority',
            'category_id', 'category_detail',
            'due_date', 'status', 'image_path',
            'is_overdue', 'is_favorite',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_is_overdue(self, obj):
        return bool(
            obj.due_date
            and obj.due_date < timezone.now().date()
            and obj.status != tasks.Status.COMPLETED
        )

    def get_is_favorite(self, obj):
        # Пункт 4.2 (передача данных через контекст): TaskViewSet передаёт
        # `request` в контекст сериализатора (это делает DRF автоматически
        # для GenericAPIView/ViewSet), а здесь мы им пользуемся, чтобы понять,
        # добавил ли ИМЕННО ТЕКУЩИЙ пользователь эту задачу в избранное —
        # без контекста сериализатор в принципе не смог бы это вычислить.
        request = self.context.get('request')
        current_user = getattr(request, 'user', None)
        if not current_user or not getattr(current_user, 'is_authenticated', False):
            return False
        return favorites.objects.filter(user=current_user, task=obj).exists()

    def validate_due_date(self, value):
        # Бизнес-правило (см. также TaskForm.clean_due_date в forms.py —
        # то же правило продублировано для API).
        if value and value < timezone.now().date():
            raise serializers.ValidationError("Дедлайн не может быть в прошлом.")
        return value


# --- ЦЕЛИ (M2M через through-модель goal_categories) ---

class GoalSerializer(serializers.ModelSerializer):
    progress_percent = serializers.SerializerMethodField()
    categories_detail = serializers.SerializerMethodField()
    category_ids = serializers.PrimaryKeyRelatedField(
        queryset=task_categories.objects.all(),
        many=True,
        write_only=True,
        required=False,
    )

    class Meta:
        model = goals
        fields = [
            'id', 'title', 'description',
            'target_value', 'current_value',
            'deadline', 'status', 'source_url',
            'progress_percent', 'categories_detail', 'category_ids',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']

    def get_progress_percent(self, obj):
        # Пункт 4.1: если GoalViewSet уже аннотировал progress_percent
        # (annotate на уровне БД — см. api_views.py), используем его;
        # иначе считаем в Python как fallback.
        if getattr(obj, 'progress_percent', None) is not None:
            return round(float(obj.progress_percent), 1)
        if not obj.target_value:
            return 0.0
        return round(float(obj.current_value) / float(obj.target_value) * 100, 1)

    def get_categories_detail(self, obj):
        links = obj.category_links.select_related('category').all()
        return TaskCategorySerializer(
            [link.category for link in links], many=True, context=self.context,
        ).data

    def validate_target_value(self, value):
        if value <= 0:
            raise serializers.ValidationError("Целевое значение должно быть больше нуля.")
        return value

    def validate_current_value(self, value):
        if value < 0:
            raise serializers.ValidationError("Прогресс не может быть отрицательным.")
        return value

    def create(self, validated_data):
        categories = validated_data.pop('category_ids', [])
        goal = goals.objects.create(**validated_data)
        for category in categories:
            goal_categories.objects.create(goal=goal, category=category)
        return goal

    def update(self, instance, validated_data):
        categories = validated_data.pop('category_ids', None)
        instance = super().update(instance, validated_data)
        if categories is not None:
            goal_categories.objects.filter(goal=instance).delete()
            for category in categories:
                goal_categories.objects.create(goal=instance, category=category)
        return instance


# --- ФИНАНСЫ ---

class FinanceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = finance_categories
        fields = ['id', 'name', 'type']


class FinanceSerializer(serializers.ModelSerializer):
    category_detail = FinanceCategorySerializer(source='category', read_only=True)

    class Meta:
        model = finances
        fields = [
            'id', 'category', 'category_detail',
            'amount', 'operation_date', 'comment', 'receipt',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Сумма должна быть больше нуля.")
        return value

    def validate_operation_date(self, value):
        if value > timezone.now().date():
            raise serializers.ValidationError("Дата операции не может быть в будущем.")
        return value
