from django import forms
from django.utils import timezone

from .models import tasks, goals, task_categories


class TaskForm(forms.ModelForm):
    class Meta:
        model = tasks
        fields = ['title', 'description', 'priority', 'category_id', 'due_date', 'status', 'image_path']
        # Пункт 4: Meta.widgets — задаём конкретные виджеты и HTML-атрибуты
        # прямо из формы модели, не трогая саму модель.
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Название задачи'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'category_id': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'category_id': 'Категория',
        }

    def clean_due_date(self):
        # Пункт 5: clean_<fieldname>() — валидация конкретного поля формы.
        due_date = self.cleaned_data.get('due_date')
        if due_date and due_date < timezone.now().date():
            raise forms.ValidationError("Дедлайн не может быть в прошлом.")
        return due_date

    def save(self, commit=True):
        # Пункт 6: save(commit=True) — паттерн из учебника (стр. 288).
        # Сначала получаем объект без записи в БД, довешиваем на него
        # логику по умолчанию, и только потом (если commit=True) сохраняем.
        task = super().save(commit=False)
        if not task.status:
            task.status = tasks.Status.ACTIVE
        if commit:
            task.save()
        return task


class GoalForm(forms.ModelForm):
    # Поле не из модели напрямую (в Meta.fields нет 'categories'), потому что
    # М2M с through нельзя редактировать через стандартный ModelForm —
    # категории обрабатываются вручную во view (через таблицу goal_categories).
    categories = forms.ModelMultipleChoiceField(
        queryset=task_categories.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'checkbox-list'}),
        required=False,
        label="Категории",
    )

    class Meta:
        model = goals
        fields = ['title', 'description', 'target_value', 'current_value', 'deadline', 'status']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'target_value': forms.NumberInput(attrs={'class': 'form-input'}),
            'current_value': forms.NumberInput(attrs={'class': 'form-input'}),
            'deadline': forms.DateInput(attrs={'type': 'date', 'class': 'form-input'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_target_value(self):
        target = self.cleaned_data.get('target_value')
        if target is not None and target <= 0:
            raise forms.ValidationError("Целевое значение должно быть больше нуля.")
        return target