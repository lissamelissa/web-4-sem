# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django import forms
from django.utils import timezone
from django.db.models import Sum
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password

from .models import user, tasks, finances, goals, task_categories, goal_categories
from .forms import TaskForm, GoalForm


# --- ФОРМЫ АВТОРИЗАЦИИ (модель user — своя, не AbstractUser, поэтому формы простые) ---
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
            return redirect('dashboard', user_id=new_user.id)
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
                return redirect('dashboard', user_id=user_obj.id)
            except user.DoesNotExist:
                messages.error(request, "Неверное имя или пароль.")
    else:
        form = MyLoginForm()
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    if 'custom_user_id' in request.session:
        del request.session['custom_user_id']
    return redirect('login')


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

    # Пункт 8 (select_related): список задач дашборда обращается к category_id
    # в шаблоне — тянем категорию сразу JOIN'ом, а не N+1 запросами.
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
    # select_related на одиночном объекте — тоже валидный и более наглядный
    # пример: без него task.user_id и task.category_id в шаблоне дали бы
    # два лишних запроса к БД.
    task = get_object_or_404(
        tasks.objects.select_related('user_id', 'category_id'),
        pk=pk
    )
    return render(request, 'task_details.html', {'task': task})


# --- CRUD ЗАДАЧ (пункт 1) ---
def task_create_view(request, user_id):
    current_user = get_object_or_404(user, id=user_id)
    if request.method == 'POST':
        form = TaskForm(request.POST, request.FILES)
        if form.is_valid():
            task = form.save(commit=False)
            task.user_id = current_user
            task.save()
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


# --- ЦЕЛИ + M2M через through (пункт 7) ---
def goals_list_view(request, user_id):
    current_user = get_object_or_404(user, id=user_id)
    # Пункт 9 (prefetch_related): у каждой цели своя выборка категорий (M2M).
    # Без prefetch_related шаблон дал бы отдельный запрос на goal.categories.all
    # для КАЖДОЙ цели в списке — классический N+1.
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
            # У through-модели goal_categories есть своё поле (added_at),
            # поэтому goal.categories.set(...) недоступен напрямую —
            # создаём связи через саму промежуточную модель.
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

def home_view(request):
    user_id = request.session.get('custom_user_id')
    if user_id:
        return redirect('dashboard', user_id=user_id)
    return redirect('login')
def goal_delete_view(request, pk):
    goal = get_object_or_404(goals, pk=pk)
    owner_id = goal.user_id
    if request.method == 'POST':
        goal.delete()
        messages.success(request, "Цель удалена.")
        return redirect('goals_list', user_id=owner_id)
    return render(request, 'goal_confirm_delete.html', {'goal': goal})