import django_filters

from .models import tasks, goals, finances


class TaskFilter(django_filters.FilterSet):
    """
    Фильтрация задач (пункт 6 задания — по аналогии с "цена/категория/
    производитель" для товаров): здесь роль "цены" играет диапазон дедлайна,
    "категории" — category_id, "производителя" — priority/status.
    """
    due_date_after = django_filters.DateFilter(field_name='due_date', lookup_expr='gte')
    due_date_before = django_filters.DateFilter(field_name='due_date', lookup_expr='lte')
    search = django_filters.CharFilter(field_name='title', lookup_expr='icontains')

    class Meta:
        model = tasks
        fields = {
            'priority': ['exact'],
            'status': ['exact'],
            'category_id': ['exact'],
        }


class GoalFilter(django_filters.FilterSet):
    deadline_after = django_filters.DateFilter(field_name='deadline', lookup_expr='gte')
    deadline_before = django_filters.DateFilter(field_name='deadline', lookup_expr='lte')
    category = django_filters.NumberFilter(field_name='categories__id')

    class Meta:
        model = goals
        fields = {
            'status': ['exact'],
        }


class FinanceFilter(django_filters.FilterSet):
    amount_min = django_filters.NumberFilter(field_name='amount', lookup_expr='gte')
    amount_max = django_filters.NumberFilter(field_name='amount', lookup_expr='lte')
    date_after = django_filters.DateFilter(field_name='operation_date', lookup_expr='gte')
    date_before = django_filters.DateFilter(field_name='operation_date', lookup_expr='lte')
    type = django_filters.CharFilter(field_name='category__type')

    class Meta:
        model = finances
        fields = {
            'category': ['exact'],
        }
