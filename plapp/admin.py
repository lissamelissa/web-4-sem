from django.contrib import admin
from .models import *

class FavoriteInline(admin.TabularInline):
    model = favorites
    extra = 1
    raw_id_fields = ('task',)


@admin.register(user)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'role', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('username', 'email')
    list_display_links = ('id', 'username')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [FavoriteInline]


@admin.register(task_categories)
class TaskCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'color')
    search_fields = ('name',)


@admin.register(tasks)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'user_id',
        'priority',
        'status',
        'status_label',
        'due_date'
    )

    list_filter = ('status', 'priority', 'due_date')
    search_fields = ('title', 'description')

    list_display_links = ('id', 'title')

    readonly_fields = ('created_at', 'updated_at')

    date_hierarchy = 'created_at'

    raw_id_fields = ('user_id', 'category_id')

    @admin.display(description="Статус")
    def status_label(self, obj):
        return "✔ Завершена" if obj.status == 'completed' else "⏳ Активна"



@admin.register(favorites)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'task', 'added_at')
    list_filter = ('added_at',)
    search_fields = ('user__username', 'task__title')
    raw_id_fields = ('user', 'task')



@admin.register(finance_categories)
class FinanceCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'type')
    list_filter = ('type',)
    search_fields = ('name',)



@admin.register(finances)
class FinanceAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'category', 'amount', 'operation_date')
    list_filter = ('operation_date', 'category')
    search_fields = ('comment',)

    date_hierarchy = 'operation_date'

    raw_id_fields = ('user', 'category')



@admin.register(goals)
class GoalAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'title',
        'user',
        'target_value',
        'current_value',
        'status',
        'deadline'
    )

    list_filter = ('status', 'deadline')
    search_fields = ('title',)

    readonly_fields = ('created_at', 'updated_at')

    raw_id_fields = ('user',)



@admin.register(habits)
class HabitAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'frequency', 'created_at')
    list_filter = ('frequency',)
    search_fields = ('name',)

    raw_id_fields = ('user',)


@admin.register(habit_logs)
class HabitLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'habit', 'log_date', 'status')
    list_filter = ('status', 'log_date')

    date_hierarchy = 'log_date'

    raw_id_fields = ('habit',)