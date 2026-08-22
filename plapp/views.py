# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django import forms
from django.utils import timezone
from django.db.models import Sum
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from .models import user, tasks, finances  #  кастомные модели
from django.contrib.auth.hashers import make_password, check_password

# --- КАСТОМНЫЕ ФОРМЫ ДЛЯ ТВОЕЙ МОДЕЛИ user ---
class MyRegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="Пароль")

    class Meta:
        model = user
        fields = ['username', 'email', 'password']


class MyLoginForm(forms.Form):
    username = forms.CharField(label="Имя пользователя")
    password = forms.CharField(widget=forms.PasswordInput, label="Пароль")


# --- ИСПРАВЛЕННЫЕ КОНТРОЛЛЕРЫ АВТОРИЗАЦИИ ---
def register_view(request):
    if request.method == 'POST':
        form = MyRegisterForm(request.POST)
        if form.is_valid():
            # Сохраняем в ТВОЮ таблицу user
            new_user = form.save(commit=False)
            new_user.password_hash = make_password(form.cleaned_data['password'])
            new_user.save()

            # Запоминаем пользователя в сессии
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


# --- ИСПРАВЛЕННЫЙ ДАШБОРД ---
def dashboard_view(request, user_id):
    # Получаем объект ИМЕННО ТВОЕЙ модели user
    current_custom_user = get_object_or_404(user, id=user_id)

    # Чтобы Django не ругался на типы данных, передаем в фильтры сам объект current_custom_user
    hot_work_tasks = tasks.objects.filter(
        user_id=current_custom_user,  # Передаем объект, а не цифру
        due_date__lte=timezone.now().date(),
        category_id__name='Работа'
    ).exclude(status='completed').order_by('priority')

    total_expenses = finances.objects.filter(
        user=current_custom_user,
        category__type='expense'
    ).aggregate(total=Sum('amount'))['total'] or 0

    all_active_tasks = tasks.active_objects.filter(user_id=current_custom_user)

    paginator = Paginator(all_active_tasks, 5)
    page = request.GET.get('page')
    try:
        tasks_page = paginator.page(page)
    except PageNotAnInteger:
        tasks_page = paginator.page(1)
    except EmptyPage:
        tasks_page = paginator.page(paginator.num_pages)

    # Передаем нашего кастомного юзера в шаблон как 'current_user'
    context = {
        'current_user': current_custom_user,
        'hot_tasks': hot_work_tasks,
        'total_expenses': total_expenses,
        'tasks_page': tasks_page,
    }
    return render(request, 'dashboard.html', context)


def task_detail_view(request, pk):
    task = get_object_or_404(tasks, pk=pk)
    return render(request, 'task_details.html', {'task': task})