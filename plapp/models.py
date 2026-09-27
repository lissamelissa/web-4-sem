from django.db import models
from django.urls import reverse
from simple_history.models import HistoricalRecords


class ActiveTaskManager(models.Manager):
    def get_queryset(self):
        # Возвращает только активные задачи
        return super().get_queryset().filter(status='active')


class user(models.Model):
    class Role(models.TextChoices):
        USER = 'user', 'User'
        ADMIN = 'admin', 'Admin'

    id = models.AutoField(primary_key=True, verbose_name="ID")
    username = models.CharField(max_length=50, unique=True, verbose_name="Имя пользователя")
    email = models.CharField(max_length=100, unique=True, verbose_name="Email")
    password_hash = models.CharField(max_length=255, verbose_name="Пароль")
    avatar_path = models.CharField(max_length=255, blank=True, null=True, verbose_name="Аватар")

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER, verbose_name="Роль")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата изменения")

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False


class task_categories(models.Model):
    id = models.AutoField(primary_key=True, verbose_name="ID")
    name = models.CharField(max_length=100, verbose_name="Название")
    color = models.CharField(max_length=7, default="#FFFFFF", verbose_name="Цвет")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Категория задачи"
        verbose_name_plural = "Категории задач"


class tasks(models.Model):
    class Priority(models.TextChoices):
        LOW = 'low', 'Низкий'
        MEDIUM = 'medium', 'Средний'
        HIGH = 'high', 'Высокий'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Активна'
        COMPLETED = 'completed', 'Завершена'

    id = models.AutoField(primary_key=True, verbose_name="ID")
    user_id = models.ForeignKey(user, on_delete=models.CASCADE, related_name="tasks", verbose_name="Пользователь")

    # Пункт 3 (пятое задание): django-simple-history. Задачи меняют статус,
    # приоритет и дедлайн многократно за свою жизнь — история показывает,
    # кто и когда именно это менял.
    history = HistoricalRecords()

    title = models.CharField(max_length=255, verbose_name="Название")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")

    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM, verbose_name="Приоритет")

    category_id = models.ForeignKey(task_categories, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Категория")

    # Пункт 1 (четвёртое задание): обычный models.ManyToManyField (без through).
    # В отличие от category_id (одна основная категория через FK), сюда можно
    # добавить сколько угодно дополнительных категорий одной задаче.
    extra_categories = models.ManyToManyField(
        task_categories,
        related_name='extra_tasks',
        blank=True,
        verbose_name="Доп. категории",
    )

    due_date = models.DateField(null=True, blank=True, verbose_name="Дедлайн")

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, verbose_name="Статус")

    image_path = models.ImageField(upload_to='tasks/', blank=True, null=True, verbose_name="Изображение")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    objects = models.Manager()  # Стандартный менеджер (tasks.objects.all())
    active_objects = ActiveTaskManager()  # Наш кастомный менеджер (tasks.active_objects.all())

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('task_detail', kwargs={'pk': self.pk})

    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"
        ordering = ['-created_at', 'priority']


class favorites(models.Model):
    user = models.ForeignKey(user, on_delete=models.CASCADE, verbose_name="Пользователь")
    task = models.ForeignKey(tasks, on_delete=models.CASCADE, verbose_name="Задача")
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата добавления")

    def __str__(self):
        return f"{self.user} → {self.task}"

    class Meta:
        unique_together = ('user', 'task')
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"


class finance_categories(models.Model):
    class Type(models.TextChoices):
        INCOME = 'income', 'Доход'
        EXPENSE = 'expense', 'Расход'

    id = models.AutoField(primary_key=True, verbose_name="ID")
    name = models.CharField(max_length=100, verbose_name="Название")
    type = models.CharField(max_length=10, choices=Type.choices, verbose_name="Тип")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Категория финансов"
        verbose_name_plural = "Категории финансов"


class finances(models.Model):
    id = models.AutoField(primary_key=True, verbose_name="ID")
    user = models.ForeignKey(user, on_delete=models.CASCADE, verbose_name="Пользователь")
    category = models.ForeignKey(finance_categories, on_delete=models.CASCADE, verbose_name="Категория")

    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма")
    operation_date = models.DateField(verbose_name="Дата операции")

    comment = models.CharField(max_length=255, blank=True, null=True, verbose_name="Комментарий")

    receipt = models.FileField(upload_to='receipts/', blank=True, null=True, verbose_name="Чек")

    # Финансовые записи по природе требуют аудита: если сумму или дату
    # операции задним числом поменяли/удалили — это должно быть видно.
    history = HistoricalRecords()

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")

    def __str__(self):
        return f"{self.amount} ({self.category})"

    class Meta:
        verbose_name = "Финансовая запись"
        verbose_name_plural = "Финансы"


class goals(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Активна'
        ACHIEVED = 'achieved', 'Достигнута'

    id = models.AutoField(primary_key=True, verbose_name="ID")
    user = models.ForeignKey(user, on_delete=models.CASCADE, verbose_name="Пользователь")

    # current_value обновляется со временем — история показывает динамику
    # приближения к цели, а не только текущий срез.
    history = HistoricalRecords()

    title = models.CharField(max_length=255, verbose_name="Название")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")

    target_value = models.DecimalField(max_digits=10, decimal_places=0, verbose_name="Цель")
    current_value = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name="Прогресс")

    deadline = models.DateField(null=True, blank=True, verbose_name="Дедлайн")

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, verbose_name="Статус")

    image_path = models.CharField(max_length=255, blank=True, null=True, verbose_name="Изображение")

    source_url = models.URLField(blank=True, null=True, verbose_name="Ссылка на источник")

    categories = models.ManyToManyField(
        task_categories,
        through='goal_categories',
        related_name='goals',
        blank=True,
        verbose_name="Категории",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.current_value is not None and self.target_value is not None:
            if self.current_value >= self.target_value and self.status != self.Status.ACHIEVED:
                self.status = self.Status.ACHIEVED
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Цель"
        verbose_name_plural = "Цели"


class goal_categories(models.Model):
    """Промежуточная (through) таблица для goals.categories."""
    goal = models.ForeignKey(goals, on_delete=models.CASCADE, related_name='category_links', verbose_name="Цель")
    category = models.ForeignKey(task_categories, on_delete=models.CASCADE, related_name='goal_links', verbose_name="Категория")
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата привязки")

    def __str__(self):
        return f"{self.goal} — {self.category}"

    class Meta:
        unique_together = ('goal', 'category')
        verbose_name = "Категория цели"
        verbose_name_plural = "Категории целей"


class habits(models.Model):
    class Frequency(models.TextChoices):
        DAILY = 'daily', 'Ежедневно'
        WEEKLY = 'weekly', 'Еженедельно'
        MONTHLY = 'monthly', 'Ежемесячно'

    id = models.AutoField(primary_key=True, verbose_name="ID")
    user = models.ForeignKey(user, on_delete=models.CASCADE, verbose_name="Пользователь")

    name = models.CharField(max_length=255, verbose_name="Название")

    frequency = models.CharField(max_length=10, choices=Frequency.choices, default=Frequency.DAILY, verbose_name="Частота")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Привычка"
        verbose_name_plural = "Привычки"


class habit_logs(models.Model):
    class Status(models.TextChoices):
        DONE = 'done', 'Выполнено'
        SKIPPED = 'skipped', 'Пропущено'

    id = models.AutoField(primary_key=True, verbose_name="ID")
    habit = models.ForeignKey(habits, on_delete=models.CASCADE, verbose_name="Привычка")

    log_date = models.DateField(verbose_name="Дата")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DONE, verbose_name="Статус")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")

    def __str__(self):
        return f"{self.habit} ({self.log_date})"

    class Meta:
        unique_together = ('habit', 'log_date')
        verbose_name = "Лог привычки"
        verbose_name_plural = "Логи привычек"
