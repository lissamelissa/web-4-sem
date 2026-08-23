from django import forms
from django.utils import timezone

from .models import tasks, goals, task_categories


class TaskForm(forms.ModelForm):
    class Meta:
        model = tasks
        fields = ['title', 'description', 'priority', 'category_id', 'due_date', 'status', 'image_path']
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
        due_date = self.cleaned_data.get('due_date')
        if due_date and due_date < timezone.now().date():
            raise forms.ValidationError("Дедлайн не может быть в прошлом.")
        return due_date

    def save(self, commit=True):
        task = super().save(commit=False)
        if not task.status:
            task.status = tasks.Status.ACTIVE
        if commit:
            task.save()
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
        # Пункт 3 (третье задание, URLField): source_url добавлен в форму —
        # рендерится как обычное текстовое поле с валидацией URL "из коробки".
        fields = ['title', 'description', 'target_value', 'current_value', 'deadline', 'status', 'source_url']
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