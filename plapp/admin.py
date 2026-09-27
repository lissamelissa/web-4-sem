import os
from io import BytesIO

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.hashers import make_password
from django.http import HttpResponse

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from simple_history.admin import SimpleHistoryAdmin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from import_export.formats.base_formats import CSV, XLSX

from .models import *


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


# Excel определяет кодировку CSV по BOM-метке в начале файла; без неё кириллица
# показывается кракозябрами на русской локали Windows. utf-8-sig добавляет эту метку.
class UTF8CSV(CSV):
    encoding = 'utf-8-sig'


# --- Пункт 4 (пятое задание): django-import-export — ресурсы для экспорта ---
class TaskResource(resources.ModelResource):
    class Meta:
        model = tasks
        fields = ('id', 'title', 'description', 'priority', 'category_id__name',
                   'due_date', 'status', 'user_id__username', 'created_at')
        export_order = fields


class FinanceResource(resources.ModelResource):
    class Meta:
        model = finances
        fields = ('id', 'user__username', 'category__name', 'amount',
                   'operation_date', 'comment')
        export_order = fields


class FavoriteInline(admin.TabularInline):
    model = favorites
    extra = 1
    raw_id_fields = ('task',)


class GoalCategoryInline(admin.TabularInline):
    model = goal_categories
    extra = 1


class UserAdminForm(forms.ModelForm):
    # Поле в форме называется так же, как в модели, но рендерится как обычное
    # поле пароля и никогда не показывает уже сохранённый хэш.
    password_hash = forms.CharField(
        label="Пароль",
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Оставьте пустым, чтобы не менять текущий пароль. "
                   "Введённое значение будет автоматически захешировано.",
    )

    class Meta:
        model = user
        fields = '__all__'


class UserAdmin(admin.ModelAdmin):
    form = UserAdminForm
    list_display = ('id', 'username', 'email', 'role', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('username', 'email')
    list_display_links = ('id', 'username')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [FavoriteInline]

    def save_model(self, request, obj, form, change):
        new_password = form.cleaned_data.get('password_hash')
        if new_password:
            obj.password_hash = make_password(new_password)
        elif change:
            obj.password_hash = user.objects.get(pk=obj.pk).password_hash
        else:
            obj.password_hash = make_password(None)
        super().save_model(request, obj, form, change)


admin.site.register(user, UserAdmin)


@admin.register(task_categories)
class TaskCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'color')
    search_fields = ('name',)


@admin.register(tasks)
class TaskAdmin(SimpleHistoryAdmin, ImportExportModelAdmin):
    # SimpleHistoryAdmin — добавляет кнопку "History" на странице объекта.
    # ImportExportModelAdmin — добавляет кнопки "Импорт"/"Экспорт" в списке.
    resource_classes = [TaskResource]
    formats = [UTF8CSV, XLSX]

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
    filter_horizontal = ('extra_categories',)

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
class FinanceAdmin(SimpleHistoryAdmin, ImportExportModelAdmin):
    resource_classes = [FinanceResource]
    formats = [UTF8CSV, XLSX]

    list_display = ('id', 'user', 'category', 'amount', 'operation_date', 'receipt')
    list_filter = ('operation_date', 'category')
    search_fields = ('comment',)

    date_hierarchy = 'operation_date'

    raw_id_fields = ('user', 'category')


@admin.register(goals)
class GoalAdmin(SimpleHistoryAdmin):
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
