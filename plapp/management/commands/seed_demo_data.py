import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from django.utils import timezone

from plapp.models import (
    user, task_categories, tasks, favorites,
    finance_categories, finances, goals, goal_categories,
    habits, habit_logs,
)

TASK_CATEGORY_NAMES = [
    "Работа", "Учёба", "Дом", "Здоровье", "Финансы",
    "Саморазвитие", "Спорт", "Хобби", "Семья", "Путешествия",
]

FINANCE_CATEGORY_NAMES_INCOME = [
    "Зарплата", "Фриланс", "Подарки", "Инвестиции", "Возврат долга",
]
FINANCE_CATEGORY_NAMES_EXPENSE = [
    "Аренда", "Продукты", "Транспорт", "Развлечения", "Кафе и рестораны",
    "Здоровье", "Одежда", "Связь", "Подписки", "Прочее",
]

TASK_TITLES = [
    "Подготовить отчёт", "Сходить в спортзал", "Купить продукты",
    "Прочитать книгу", "Позвонить клиенту", "Сделать бэкап данных",
    "Оплатить коммуналку", "Написать код фичи", "Убраться дома",
    "Записаться к врачу", "Спланировать отпуск", "Проверить почту",
    "Обновить резюме", "Полить цветы", "Сделать зарядку",
]

GOAL_TITLES = [
    "Прочитать 10 книг", "Накопить на отпуск", "Изучить Python",
    "Пробежать полумарафон", "Выучить 500 слов", "Сдать экзамен",
    "Похудеть на 5 кг", "Найти новую работу", "Собрать портфолио",
    "Пройти курс по Django",
]

HABIT_NAMES = [
    "Пить 2 литра воды", "Читать 20 минут", "Медитация",
    "Утренняя зарядка", "Ложиться спать до 23:00", "Считать калории",
    "Учить английский", "Проверять финансы", "Гулять 30 минут", "Вести дневник",
]


class Command(BaseCommand):
    help = "Наполняет базу данных демонстрационными записями (минимум 10 на таблицу)."

    def handle(self, *args, **options):
        random.seed(42)
        today = timezone.now().date()

        # --- Пользователи ---
        users = []
        for i in range(1, 11):
            u, _ = user.objects.get_or_create(
                username=f"user{i}",
                defaults={
                    'email': f"user{i}@example.com",
                    'password_hash': make_password("password123"),
                }
            )
            users.append(u)
        self.stdout.write(self.style.SUCCESS(f"Пользователей: {user.objects.count()}"))

        # --- Категории задач ---
        categories = []
        for name in TASK_CATEGORY_NAMES:
            c, _ = task_categories.objects.get_or_create(
                name=name, defaults={'color': '#%06x' % random.randint(0, 0xFFFFFF)}
            )
            categories.append(c)
        self.stdout.write(self.style.SUCCESS(f"Категорий задач: {task_categories.objects.count()}"))

        # --- Категории финансов ---
        income_cats, expense_cats = [], []
        for name in FINANCE_CATEGORY_NAMES_INCOME:
            c, _ = finance_categories.objects.get_or_create(name=name, defaults={'type': 'income'})
            income_cats.append(c)
        for name in FINANCE_CATEGORY_NAMES_EXPENSE:
            c, _ = finance_categories.objects.get_or_create(name=name, defaults={'type': 'expense'})
            expense_cats.append(c)
        self.stdout.write(self.style.SUCCESS(f"Категорий финансов: {finance_categories.objects.count()}"))

        # --- Задачи (создаются заново при каждом запуске команды) ---
        created_tasks = []
        if tasks.objects.count() < 15:
            for u in users:
                for i in range(3):
                    title = random.choice(TASK_TITLES)
                    t = tasks.objects.create(
                        user_id=u,
                        title=title,
                        description=f"Автосгенерированная задача: {title.lower()}.",
                        priority=random.choice(['low', 'medium', 'high']),
                        category_id=random.choice(categories),
                        due_date=today + timedelta(days=random.randint(-5, 20)),
                        status=random.choice(['active', 'active', 'active', 'completed']),
                    )
                    t.extra_categories.set(random.sample(categories, k=random.randint(0, 2)))
                    created_tasks.append(t)
        else:
            created_tasks = list(tasks.objects.all())
        self.stdout.write(self.style.SUCCESS(f"Задач: {tasks.objects.count()}"))

        # --- Избранное ---
        for _ in range(20):
            u = random.choice(users)
            t = random.choice(created_tasks)
            favorites.objects.get_or_create(user=u, task=t)
        self.stdout.write(self.style.SUCCESS(f"Избранного: {favorites.objects.count()}"))

        # --- Финансы ---
        if finances.objects.count() < 15:
            for u in users:
                for i in range(2):
                    cat = random.choice(income_cats + expense_cats)
                    finances.objects.create(
                        user=u,
                        category=cat,
                        amount=random.randint(500, 50000),
                        operation_date=today - timedelta(days=random.randint(0, 60)),
                        comment=random.choice(["", "Плановая операция", "REF-1023", "Разовая трата"]),
                    )
        self.stdout.write(self.style.SUCCESS(f"Финансовых операций: {finances.objects.count()}"))

        # --- Цели ---
        if goals.objects.count() < 10:
            for u in users:
                title = random.choice(GOAL_TITLES)
                target = random.randint(5, 100)
                g = goals.objects.create(
                    user=u,
                    title=title,
                    description=f"Автосгенерированная цель: {title.lower()}.",
                    target_value=target,
                    current_value=random.randint(0, target),
                    deadline=today + timedelta(days=random.randint(10, 120)),
                    source_url="https://example.com",
                )
                for c in random.sample(categories, k=random.randint(1, 3)):
                    goal_categories.objects.get_or_create(goal=g, category=c)
        self.stdout.write(self.style.SUCCESS(f"Целей: {goals.objects.count()}"))
        self.stdout.write(self.style.SUCCESS(f"Связей цель-категория: {goal_categories.objects.count()}"))

        # --- Привычки и логи ---
        for u in users:
            for name in random.sample(HABIT_NAMES, k=1):
                h, _ = habits.objects.get_or_create(
                    user=u, name=name, defaults={'frequency': random.choice(['daily', 'weekly', 'monthly'])}
                )
                for d in range(3):
                    habit_logs.objects.get_or_create(
                        habit=h,
                        log_date=today - timedelta(days=d),
                        defaults={'status': random.choice(['done', 'skipped'])}
                    )
        self.stdout.write(self.style.SUCCESS(f"Привычек: {habits.objects.count()}"))
        self.stdout.write(self.style.SUCCESS(f"Логов привычек: {habit_logs.objects.count()}"))

        self.stdout.write(self.style.SUCCESS("Готово! База наполнена демо-данными."))
