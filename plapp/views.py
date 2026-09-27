# views.py
import calendar

from django.shortcuts import render, redirect, get_object_or_404
from django import forms
from django.utils import timezone
from django.db.models import Sum, Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from django.http import HttpResponseRedirect
from django.urls import reverse

from .models import user, tasks, finances, goals, task_categories, goal_categories, favorites
from .forms import TaskForm, GoalForm, TaskSearchForm, FinanceForm

MONTH_NAMES_RU = {
    1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
    5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
    9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь',
}


# --- ФОРМЫ АВТОРИЗАЦИИ ---
class MyRegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Пароль")

    class Meta:
        model = user
        fields = ['username', 'email', 'password']


class MyLoginForm(forms.Form):
    username = forms.CharField(label="Имя пользователя")
    password = forms.CharField(widget=forms.PasswordInput, label="Пароль")


# --- АВТОРИЗАЦИЯ / РЕГИСТРАЦИЯ ---
def register_view(request):
    if request.method == 'POST':
        form = MyRegisterForm(request.POST)
        if form.is_valid():
            new_user = form.save(commit=False)
            new_user.password_hash = make_password(form.cleaned_data['password'])
            new_user.save()
            request.session['custom_user_id'] = new_user.id
            return redirect('home_page', user_id=new_user.id)
    else:
        form = MyRegisterForm()
    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = MyLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            try:
                user_obj = user.objects.get(username=username)
                if not check_password(password, user_obj.password_hash):
                    raise user.DoesNotExist
                request.session['custom_user_id'] = user_obj.id
                return redirect('home_page', user_id=user_obj.id)
            except (user.DoesNotExist, user.MultipleObjectsReturned):
                # MultipleObjectsReturned подстраховывает на случай, если в базе
                # всё же окажутся старые дубли username, созданные до unique=True.
                messages.error(request, "Неверное имя или пароль.")
    else:
        form = MyLoginForm()
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    if 'custom_user_id' in request.session:
        del request.session['custom_user_id']
    return redirect('login')


def home_view(request):
    user_id = request.session.get('custom_user_id')
    if user_id:
        return redirect('home_page', user_id=user_id)
    return redirect('login')


# --- ГЛАВНАЯ СТРАНИЦА (виджеты) ---
def home_page_view(request, user_id):
    # get_object_or_404 внутри вызывает QuerySet.get() — пример get().
    current_user = get_object_or_404(user, id=user_id)
    today = timezone.now().date()

    # --- Виджет 1: компактный календарь текущего месяца ---
    month_tasks = tasks.objects.filter(
        user_id=current_user, due_date__year=today.year, due_date__month=today.month
    ).values('id', 'due_date')  # values() — нужны только даты, без лишних полей

    tasks_by_day = set()
    for t in month_tasks:
        tasks_by_day.add(t['due_date'].day)

    cal = calendar.Calendar(firstweekday=0)
    mini_weeks = []
    for week in cal.monthdayscalendar(today.year, today.month):
        row = []
        for day_num in week:
            if day_num == 0:
                row.append(None)
            else:
                row.append({
                    'day': day_num,
                    'has_tasks': day_num in tasks_by_day,
                    'is_today': day_num == today.day,
                })
        mini_weeks.append(row)

    # filter() + exclude() + order_by() — три разных типа запроса в одной цепочке
    upcoming_tasks = tasks.objects.filter(
        user_id=current_user, due_date__gte=today
    ).exclude(status='completed').order_by('due_date')[:5]  # + limiting queryset

    # distinct() — какие приоритеты вообще встречаются среди ближайших задач
    priority_codes = tasks.objects.filter(
        user_id=current_user, due_date__gte=today
    ).exclude(status='completed').values_list('priority', flat=True).distinct()
    priority_labels = dict(tasks.Priority.choices)
    upcoming_priorities = [priority_labels.get(p, p) for p in priority_codes]

    # --- Виджет 2: топ целей по ближайшему дедлайну ---
    top_goals = goals.objects.filter(
        user=current_user, status='active'
    ).exclude(deadline__isnull=True).order_by('deadline')[:5]

    # --- Виджет 3: финансы ---
    recent_finances = finances.objects.filter(user=current_user).order_by('-operation_date')[:5]

    # Агрегатная функция (Sum) с условием — считаем баланс одним запросом.
    balance = finances.objects.filter(user=current_user).aggregate(
        income=Sum('amount', filter=Q(category__type='income')),
        expense=Sum('amount', filter=Q(category__type='expense')),
    )
    total_balance = (balance['income'] or 0) - (balance['expense'] or 0)

    # --- Виджет 4: избранные задачи (таблица favorites, наконец, используется) ---
    favorite_tasks = tasks.objects.filter(favorites__user=current_user).select_related('category_id')[:5]

    # all() — полный список категорий, показываем как справочные чипы
    all_categories = task_categories.objects.all()

    # --- Поиск на главной странице ---
    search_query = request.GET.get('q', '').strip()
    search_results = None
    if search_query:
        search_results = tasks.objects.filter(user_id=current_user).filter(
            Q(title__icontains=search_query) | Q(description__icontains=search_query)
        )[:10]

    context = {
        'current_user': current_user,
        'mini_weeks': mini_weeks,
        'weekday_names': ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'],
        'month_name': MONTH_NAMES_RU.get(today.month, today.month),
        'upcoming_tasks': upcoming_tasks,
        'upcoming_priorities': upcoming_priorities,
        'top_goals': top_goals,
        'recent_finances': recent_finances,
        'total_balance': total_balance,
        'favorite_tasks': favorite_tasks,
        'all_categories': all_categories,
        'search_query': search_query,
        'search_results': search_results,
    }
    return render(request, 'home_page.html', context)


def toggle_favorite_view(request, user_id, pk):
    # Бизнес-логика: переключатель "избранное" с явным использованием get()
    # и обработкой уникальности пары (user, task).
    current_user = get_object_or_404(user, id=user_id)
    task = get_object_or_404(tasks, pk=pk)

    if request.method == 'POST':
        try:
            existing = favorites.objects.get(user=current_user, task=task)  # get()
            existing.delete()
            messages.success(request, "Убрано из избранного.")
        except favorites.DoesNotExist:
            favorites.objects.create(user=current_user, task=task)
            messages.success(request, "Добавлено в избранное.")

    next_url = request.POST.get('next') or reverse('home_page', kwargs={'user_id': current_user.id})
    return HttpResponseRedirect(next_url)


# --- ПОЛНОЭКРАННЫЙ КАЛЕНДАРЬ ---
def calendar_view(request, user_id):
    current_user = get_object_or_404(user, id=user_id)
    today = timezone.now().date()

    try:
        year = int(request.GET.get('year', today.year))
        month = int(request.GET.get('month', today.month))
        if not (1 <= month <= 12):
            raise ValueError
    except (TypeError, ValueError):
        year, month = today.year, today.month

    month_tasks = tasks.objects.filter(
        user_id=current_user,
        due_date__year=year,
        due_date__month=month,
    ).values('id', 'title', 'due_date', 'status', 'priority').order_by('due_date')

    tasks_by_day = {}
    for t in month_tasks:
        tasks_by_day.setdefault(t['due_date'].day, []).append(t)

    cal = calendar.Calendar(firstweekday=0)
    weeks = []
    for week in cal.monthdayscalendar(year, month):
        week_data = []
        for day_num in week:
            if day_num == 0:
                week_data.append(None)
            else:
                week_data.append({
                    'day': day_num,
                    'tasks': tasks_by_day.get(day_num, []),
                    'is_today': (day_num == today.day and month == today.month and year == today.year),
                })
        weeks.append(week_data)

    overdue_count = tasks.objects.filter(
        user_id=current_user, due_date__lt=today
    ).exclude(status='completed').count()

    prev_month, prev_year = (12, year - 1) if month == 1 else (month - 1, year)
    next_month, next_year = (1, year + 1) if month == 12 else (month + 1, year)

    context = {
        'current_user': current_user,
        'weeks': weeks,
        'weekday_names': ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'],
        'month_name': MONTH_NAMES_RU.get(month, month),
        'year': year,
        'prev_year': prev_year, 'prev_month': prev_month,
        'next_year': next_year, 'next_month': next_month,
        'overdue_count': overdue_count,
    }
    return render(request, 'calendar_page.html', context)


# --- ДАШБОРД ---
def dashboard_view(request, user_id):
    current_custom_user = get_object_or_404(user, id=user_id)

    hot_work_tasks = tasks.objects.filter(
        user_id=current_custom_user,
        due_date__lte=timezone.now().date(),
        category_id__name='Работа'
    ).exclude(status='completed').order_by('priority')

    total_expenses = finances.objects.filter(
        user=current_custom_user,
        category__type='expense'
    ).aggregate(total=Sum('amount'))['total'] or 0

    all_active_tasks = tasks.active_objects.filter(
        user_id=current_custom_user
    ).select_related('category_id')

    paginator = Paginator(all_active_tasks, 5)
    page = request.GET.get('page')
    try:
        tasks_page = paginator.page(page)
    except PageNotAnInteger:
        tasks_page = paginator.page(1)
    except EmptyPage:
        tasks_page = paginator.page(paginator.num_pages)

    context = {
        'current_user': current_custom_user,
        'hot_tasks': hot_work_tasks,
        'total_expenses': total_expenses,
        'tasks_page': tasks_page,
    }
    return render(request, 'dashboard.html', context)


def task_detail_view(request, pk):
    task = get_object_or_404(
        tasks.objects.select_related('user_id', 'category_id').prefetch_related('extra_categories'),
        pk=pk
    )
    is_favorited = favorites.objects.filter(user=task.user_id, task=task).exists()
    return render(request, 'task_details.html', {'task': task, 'is_favorited': is_favorited})


# --- CRUD ЗАДАЧ ---
def task_create_view(request, user_id):
    current_user = get_object_or_404(user, id=user_id)
    if request.method == 'POST':
        form = TaskForm(request.POST, request.FILES)
        if form.is_valid():
            task = form.save(commit=False)
            task.user_id = current_user
            task.save()
            form.save_m2m()
            messages.success(request, "Задача создана.")
            return redirect('dashboard', user_id=current_user.id)
    else:
        form = TaskForm()
    return render(request, 'task_form.html', {'form': form, 'current_user': current_user, 'mode': 'create'})


def task_edit_view(request, pk):
    task = get_object_or_404(tasks, pk=pk)
    if request.method == 'POST':
        form = TaskForm(request.POST, request.FILES, instance=task)
        if form.is_valid():
            task = form.save()
            messages.success(request, "Задача обновлена.")
            return redirect('task_detail', pk=task.pk)
    else:
        form = TaskForm(instance=task)
    return render(request, 'task_form.html', {'form': form, 'current_user': task.user_id, 'mode': 'edit'})


def task_delete_view(request, pk):
    task = get_object_or_404(tasks, pk=pk)
    owner_id = task.user_id.id
    if request.method == 'POST':
        task.delete()
        messages.success(request, "Задача удалена.")
        return redirect('dashboard', user_id=owner_id)
    return render(request, 'task_confirm_delete.html', {'task': task})


# --- ТАБЛИЦА ЗАДАЧ С ПОИСКОМ И BULK-ДЕЙСТВИЯМИ ---
def tasks_table_view(request, user_id):
    current_user = get_object_or_404(user, id=user_id)
    search_form = TaskSearchForm(request.GET or None)

    queryset = tasks.objects.filter(user_id=current_user).select_related('category_id').prefetch_related('extra_categories')

    if search_form.is_valid():
        query = search_form.cleaned_data.get('query')
        status_filter = search_form.cleaned_data.get('status')
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            )
        if status_filter:
            queryset = queryset.filter(status=status_filter)

    queryset = queryset.order_by('due_date')

    context = {
        'current_user': current_user,
        'search_form': search_form,
        'task_list': queryset,
        'total_count': queryset.count(),
    }
    return render(request, 'tasks_table.html', context)


def tasks_bulk_action_view(request, user_id):
    current_user = get_object_or_404(user, id=user_id)
    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_tasks')
        action = request.POST.get('bulk_action')

        target_qs = tasks.objects.filter(user_id=current_user, pk__in=selected_ids)

        if action == 'complete':
            updated = target_qs.update(status=tasks.Status.COMPLETED)
            messages.success(request, f"Отмечено выполненными: {updated}.")
        elif action == 'delete':
            deleted_count, _ = target_qs.delete()
            messages.success(request, f"Удалено задач: {deleted_count}.")

    return HttpResponseRedirect(reverse('tasks_table', kwargs={'user_id': current_user.id}))


# --- ТАБЛИЦА ФИНАНСОВ ---
def finances_table_view(request, user_id):
    current_user = get_object_or_404(user, id=user_id)

    search_query = request.GET.get('q', '').strip()

    queryset = finances.objects.filter(user=current_user).select_related('category')
    if search_query:
        queryset = queryset.filter(comment__contains=search_query)

    has_records = queryset.exists()
    recent_records = queryset.order_by('-operation_date')[:20]

    total_income = queryset.filter(category__type='income').aggregate(total=Sum('amount'))['total'] or 0
    total_expense = queryset.filter(category__type='expense').aggregate(total=Sum('amount'))['total'] or 0

    used_categories = queryset.values_list('category__name', flat=True).distinct()

    context = {
        'current_user': current_user,
        'records': recent_records,
        'has_records': has_records,
        'total_income': total_income,
        'total_expense': total_expense,
        'used_categories': used_categories,
        'search_query': search_query,
    }
    return render(request, 'finances_table.html', context)


def finance_create_view(request, user_id):
    current_user = get_object_or_404(user, id=user_id)
    if request.method == 'POST':
        form = FinanceForm(request.POST, request.FILES)
        if form.is_valid():
            record = form.save(commit=False)
            record.user = current_user
            record.save()
            messages.success(request, "Операция добавлена.")
            return redirect('finances_table', user_id=current_user.id)
    else:
        form = FinanceForm()
    return render(request, 'finance_form.html', {'form': form, 'current_user': current_user, 'mode': 'create'})


def finance_edit_view(request, pk):
    record = get_object_or_404(finances, pk=pk)
    if request.method == 'POST':
        form = FinanceForm(request.POST, request.FILES, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, "Операция обновлена.")
            return redirect('finances_table', user_id=record.user_id)
    else:
        form = FinanceForm(instance=record)
    return render(request, 'finance_form.html', {'form': form, 'current_user': record.user, 'mode': 'edit'})


def finance_delete_view(request, pk):
    record = get_object_or_404(finances, pk=pk)
    owner_id = record.user_id
    if request.method == 'POST':
        record.delete()
        messages.success(request, "Операция удалена.")
        return redirect('finances_table', user_id=owner_id)
    return render(request, 'finance_confirm_delete.html', {'record': record})


# --- ЦЕЛИ + M2M через through ---
def goals_list_view(request, user_id):
    current_user = get_object_or_404(user, id=user_id)
    user_goals = goals.objects.filter(user=current_user).prefetch_related('categories').order_by('-created_at')
    return render(request, 'goals_list.html', {'goals': user_goals, 'current_user': current_user})


def goal_create_view(request, user_id):
    current_user = get_object_or_404(user, id=user_id)
    if request.method == 'POST':
        form = GoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = current_user
            goal.save()
            for category in form.cleaned_data['categories']:
                goal_categories.objects.create(goal=goal, category=category)
            messages.success(request, "Цель создана.")
            return redirect('goals_list', user_id=current_user.id)
    else:
        form = GoalForm()
    return render(request, 'goal_form.html', {'form': form, 'current_user': current_user, 'mode': 'create'})


def goal_edit_view(request, pk):
    goal = get_object_or_404(goals, pk=pk)
    if request.method == 'POST':
        form = GoalForm(request.POST, instance=goal)
        if form.is_valid():
            goal = form.save()
            goal_categories.objects.filter(goal=goal).delete()
            for category in form.cleaned_data['categories']:
                goal_categories.objects.create(goal=goal, category=category)
            messages.success(request, "Цель обновлена.")
            return redirect('goals_list', user_id=goal.user_id)
    else:
        form = GoalForm(
            instance=goal,
            initial={'categories': task_categories.objects.filter(goal_links__goal=goal)}
        )
    return render(request, 'goal_form.html', {'form': form, 'current_user': goal.user, 'mode': 'edit'})


def goal_delete_view(request, pk):
    goal = get_object_or_404(goals, pk=pk)
    owner_id = goal.user_id
    if request.method == 'POST':
        goal.delete()
        messages.success(request, "Цель удалена.")
        return redirect('goals_list', user_id=owner_id)
    return render(request, 'goal_confirm_delete.html', {'goal': goal})
