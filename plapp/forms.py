from django import forms
from django.utils import timezone

from .models import tasks, goals, task_categories, finances


class TaskForm(forms.ModelForm):
    class Meta:
        model = tasks
        # Пункт (fields): явный список полей формы.
        fields = [
            'title', 'description', 'priority', 'category_id',
            'extra_categories', 'due_date', 'status', 'image_path',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Название задачи'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'category_id': forms.Select(attrs={'class': 'form-select'}),
            'extra_categories': forms.CheckboxSelectMultiple(attrs={'class': 'checkbox-list'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'category_id': 'Категория',
            'extra_categories': 'Дополнительные категории',
        }
        # help_texts — подсказки под полем
        help_texts = {
            'due_date': 'Если не указать дедлайн, задача не попадёт в календарь на главной странице.',
            'priority': 'От этого зависит, попадёт ли задача в блок «Важные задачи» на дашборде.',
        }
        # error_messages — свой текст ошибки вместо стандартного Django-текста
        error_messages = {
            'title': {
                'required': 'Название задачи обязательно — иначе непонятно, что делать.',
                'max_length': 'Слишком длинное название, сократите его.',
            },
        }

    def clean_due_date(self):
        due_date = self.cleaned_data.get('due_date')
        if due_date and due_date < timezone.now().date():
            raise forms.ValidationError("Дедлайн не может быть в прошлом.")
        return due_date

    def save(self, commit=True):
        # Паттерн commit=False -> доп. логика -> save().
        task = super().save(commit=False)
        if not task.status:
            task.status = tasks.Status.ACTIVE
        if commit:
            task.save()
            # save_m2m() обязателен: extra_categories — обычный M2M, Django
            # откладывает запись связей до тех пор, пока у задачи не будет pk.
            self.save_m2m()
        return task


class GoalForm(forms.ModelForm):
    categories = forms.ModelMultipleChoiceField(
        queryset=task_categories.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'checkbox-list'}),
        required=False,
        label="Категории",
    )

    class Meta:
        model = goals
        # Пункт (exclude): здесь вместо fields используем exclude — перечисляем,
        # какие поля модели НЕ показывать в форме, а не какие показывать.
        # 'categories' исключать не обязательно (M2M с through Django и так не
        # генерирует автоматически), но 'user'/служебные даты — обязательно.
        exclude = ['user', 'image_path', 'created_at', 'updated_at']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'target_value': forms.NumberInput(attrs={'class': 'form-input'}),
            'current_value': forms.NumberInput(attrs={'class': 'form-input'}),
            'deadline': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'source_url': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://...'}),
        }
        labels = {
            'source_url': 'Ссылка на источник',
        }

    def clean_target_value(self):
        target = self.cleaned_data.get('target_value')
        if target is not None and target <= 0:
            raise forms.ValidationError("Целевое значение должно быть больше нуля.")
        return target


class TaskSearchForm(forms.Form):
    """Форма поиска/фильтрации на странице-таблице задач."""

    # forms.CharField(widget=forms.Textarea) — текстовое поле поиска
    # сделано textarea, а не обычным text input, чтобы можно было
    # вставить многословный кусок описания и искать по нему.
    query = forms.CharField(
        required=False,
        label="Поиск по названию или описанию",
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-textarea search-textarea', 'placeholder': 'Например: подготовить отчёт'}),
        help_text="Ищет без учёта регистра (icontains) и по названию, и по описанию.",
    )
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'Все статусы')] + list(tasks.Status.choices),
        label="Статус",
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Media:
        # class Media — подключаем свой CSS именно для этой формы.
        # Media не обязана включать js: одного css достаточно, чтобы
        # продемонстрировать требование.
        css = {'all': ('plapp/css/task_search.css',)}


class FinanceForm(forms.ModelForm):
    class Meta:
        model = finances
        fields = ['category', 'amount', 'operation_date', 'comment', 'receipt']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'operation_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'comment': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Необязательно'}),
        }
        labels = {
            'category': 'Категория',
            'operation_date': 'Дата операции',
            'receipt': 'Чек (необязательно)',
        }
