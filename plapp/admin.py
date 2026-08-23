import os
from io import BytesIO

from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .models import *


# --- Пункт 1 (третье задание): генерация PDF в админке ---

# Стандартные шрифты reportlab (Helvetica и т.д.) не поддерживают кириллицу,
# поэтому подключаем реальный TTF-шрифт с рабочей машины.
_CYRILLIC_FONT_CANDIDATES = [
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    str(settings.BASE_DIR / "plapp" / "static" / "fonts" / "DejaVuSans.ttf"),
]


def _register_cyrillic_font():
    for path in _CYRILLIC_FONT_CANDIDATES:
        if os.path.exists(path):
            if 'CyrillicFont' not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont('CyrillicFont', path))
            return 'CyrillicFont'
    # Ни один шрифт не найден — вернётся Helvetica, кириллица не отобразится.
    return 'Helvetica'


@admin.action(description="Экспортировать выбранные задачи в PDF")
def export_tasks_pdf(modeladmin, request, queryset):
    font_name = _register_cyrillic_font()

    buffer = BytesIO()
    doc = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    doc.setFont(font_name, 16)
    doc.drawString(20 * mm, height - 20 * mm, "Список задач")

    doc.setFont(font_name, 10)
    y = height - 32 * mm
    for task in queryset.order_by('priority'):
        line = (
            f"{task.title} — {task.get_priority_display()} — "
            f"до {task.due_date.strftime('%d.%m.%Y') if task.due_date else '—'} — "
            f"{task.get_status_display()}"
        )
        doc.drawString(20 * mm, y, line[:110])
        y -= 8 * mm
        if y < 20 * mm:
            doc.showPage()
            doc.setFont(font_name, 10)
            y = height - 20 * mm

    doc.save()
    buffer.seek(0)

    response = HttpResponse(buffer.read(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="tasks.pdf"'
    return response


class FavoriteInline(admin.TabularInline):
    model = favorites
    extra = 1
    raw_id_fields = ('task',)


class GoalCategoryInline(admin.TabularInline):
    model = goal_categories
    extra = 1


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

    actions = [export_tasks_pdf]

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
    list_display = ('id', 'user', 'category', 'amount', 'operation_date', 'receipt')
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

    inlines = [GoalCategoryInline]


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