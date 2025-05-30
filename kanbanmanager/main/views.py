# main/views.py

import json
from django.shortcuts        import render, redirect, get_object_or_404
from django.http             import JsonResponse
from django.contrib          import messages
from django.contrib.auth     import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms     import PasswordChangeForm
from django.views.decorators.http import require_POST
from django.utils            import timezone
from django.db.models        import Count

from .models    import Company, Status, CompanyStatusHistory
from .forms     import CompanyForm, CompanyStatusHistoryForm, CommentForm


# ─── AJAX для Kanban ─────────────────────────────────────────────────────────
@login_required
@require_POST
def move_company(request):
    cid     = request.POST.get('company_id')
    sid     = request.POST.get('status_id') or None

    # staff — без ограничений, иначе только свои в своём регионе
    if request.user.is_staff:
        company = get_object_or_404(Company, pk=cid)
    else:
        company = get_object_or_404(
            Company,
            pk=cid,
            owner=request.user,
            region=request.user.profile.region
        )

    status = get_object_or_404(Status, pk=sid) if sid else None

    # Запись в историю и обновление статуса
    CompanyStatusHistory.objects.create(company=company, status=status)
    company.status = status
    company.save(update_fields=['status'])
    return JsonResponse({'result': 'ok'})


@login_required
@require_POST
def reorder_companies(request):
    payload   = json.loads(request.body)
    sid       = payload.get('status_id') or None
    new_order = payload.get('order', [])

    for idx, cid in enumerate(new_order):
        try:
            c = Company.objects.get(pk=cid)
            if not request.user.is_staff:
                if c.owner != request.user or c.region != request.user.profile.region:
                    continue
        except Company.DoesNotExist:
            continue

        c.status   = Status.objects.get(pk=sid) if sid else None
        c.position = idx
        c.save(update_fields=['status', 'position'])

    return JsonResponse({'result': 'ok'})

from .models import REGION_CHOICES

# ─── Список компаний ─────────────────────────────────────────────────────────
@login_required
def index(request):
    # --- Базовый queryset с учётом роли ---
    qs = Company.objects.all() if request.user.is_staff \
         else Company.objects.filter(region=request.user.profile.region)

    # --- Парсим GET-параметры ---
    q      = request.GET.get('q', '').strip()
    st_id  = request.GET.get('status')
    region = request.GET.get('region')
    overdue = request.GET.get('overdue') == '1'

    # --- Поиск по названию ---
    if q:
        qs = qs.filter(name__icontains=q)

    # --- Фильтр по статусу ---
    if st_id:
        qs = qs.filter(status_id=st_id)

    # --- Фильтр по региону (для staff) ---
    if request.user.is_staff and region:
        qs = qs.filter(region=region)

    # --- Преобразуем в список и рассчитываем дни/просрочку ---
    companies = []
    now = timezone.now()
    for c in qs.order_by('position'):
        last = c.history.first()
        c.days_in_status = (now - last.changed_at).days if last else None
        c.is_overdue = bool(
            last and c.status and c.status.duration_days
            and c.days_in_status is not None
            and c.days_in_status > c.status.duration_days
        )
        # если включён фильтр "только просроченные" — пропускаем непрошедшие
        if overdue and not c.is_overdue:
            continue
        companies.append(c)

    # --- Передаём в шаблон ---
    return render(request, 'main/index.html', {
        'title':     'Список компаний',
        'companies': companies,
        'statuses':  Status.objects.order_by('order'),
        'regions':   REGION_CHOICES,
    })


# ─── Kanban-доска ─────────────────────────────────────────────────────────────
@login_required
def board(request):
    if request.user.is_staff:
        qs = Company.objects.all().order_by('position')
    else:
        qs = Company.objects.filter(region=request.user.profile.region) \
                            .order_by('position')

    companies = list(qs)
    statuses  = Status.objects.order_by('order')

    now = timezone.now()
    for c in companies:
        last = c.history.first()
        c.is_overdue = bool(
            last and c.status and c.status.duration_days and
            (now - last.changed_at).days > c.status.duration_days
        )

    if request.GET.get('overdue') == '1':
        companies = [c for c in companies if c.is_overdue]

    # Группируем по статусам
    groups = {st.id: [] for st in statuses}
    groups[None] = []
    for c in companies:
        groups.setdefault(c.status_id, []).append(c)

    board_data = [(st, groups.get(st.id, [])) for st in statuses]
    if groups[None]:
        board_data.append((None, groups[None]))

    return render(request, 'main/board.html', {
        'title':      'Kanban Board',
        'board_data': board_data,
    })


# ─── CRUD компаний ────────────────────────────────────────────────────────────
@login_required
def add_company(request):
    if request.method == 'POST':
        form = CompanyForm(request.POST, user=request.user)
        if form.is_valid():
            c = form.save(commit=False)
            c.owner = request.user
            if not request.user.is_staff:
                c.region = request.user.profile.region
            c.save()
            return redirect('main:index')
    else:
        form = CompanyForm(user=request.user)

    return render(request, 'main/company_form.html', {
        'title': 'Добавить компанию',
        'form':  form,
    })

@login_required
def edit_company(request, pk):
    """
    staff видит любую компанию,
    обычный пользователь — только компании своего региона.
    """
    filters = {'pk': pk}
    if not request.user.is_staff:
        filters['region'] = request.user.profile.region

    company = get_object_or_404(Company, **filters)

    if request.method == 'POST':
        form = CompanyForm(request.POST, instance=company, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('main:index')
    else:
        form = CompanyForm(instance=company, user=request.user)

    return render(request, 'main/company_form.html', {
        'title': 'Редактировать компанию',
        'form':  form,
    })


@login_required
def delete_company(request, pk):
    filters = {'pk': pk}
    if not request.user.is_staff:
        filters['region'] = request.user.profile.region

    company = get_object_or_404(Company, **filters)

    if request.method == 'POST':
        company.delete()
        return redirect('main:index')

    return render(request, 'main/company_confirm_delete.html', {
        'title':   'Удалить компанию',
        'company': company,
    })


@login_required
def company_detail(request, pk):
    filters = {'pk': pk}
    if not request.user.is_staff:
        filters['region'] = request.user.profile.region

    company = get_object_or_404(Company, **filters)

    # Обработка комментариев остаётся без изменений…
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            com = form.save(commit=False)
            com.company = company
            com.author  = request.user
            com.save()
            return redirect('main:company_detail', pk=pk)
    else:
        form = CommentForm()

    # Считаем дни в статусе
    last_change   = company.history.first()
    days_in_status = (timezone.now() - last_change.changed_at).days if last_change else None

    return render(request, 'main/company_detail.html', {
        'company':        company,
        'form':           form,
        'days_in_status': days_in_status,
    })

# ─── CRUD для истории статусов ───────────────────────────────────────────────
@login_required
def add_status_history(request, company_id):
    if request.user.is_staff:
        company = get_object_or_404(Company, pk=company_id)
    else:
        company = get_object_or_404(
            Company,
            pk=company_id,
            region=request.user.profile.region
        )

    if request.method == 'POST':
        form = CompanyStatusHistoryForm(request.POST)
        if form.is_valid():
            h = form.save(commit=False)
            h.company = company
            h.save()
            return redirect('main:company_detail', pk=company_id)
    else:
        form = CompanyStatusHistoryForm()

    return render(request, 'main/history_form.html', {
        'title':   f'Добавить историю для {company.name}',
        'form':    form,
        'company': company,
    })


@login_required
def edit_status_history(request, history_id):
    # находим запись истории, проверяя регион компании
    if request.user.is_staff:
        h = get_object_or_404(CompanyStatusHistory, pk=history_id)
    else:
        h = get_object_or_404(
            CompanyStatusHistory,
            pk=history_id,
            company__region=request.user.profile.region
        )

    if request.method == 'POST':
        form = CompanyStatusHistoryForm(request.POST, instance=h)
        if form.is_valid():
            form.save()
            return redirect('main:company_detail', pk=h.company.pk)
    else:
        form = CompanyStatusHistoryForm(instance=h)

    return render(request, 'main/history_form.html', {
        'title':   f'Редактировать историю для {h.company.name}',
        'form':    form,
        'company': h.company,
    })



@login_required
def delete_status_history(request, history_id):
    # аналогично — только по региону
    if request.user.is_staff:
        h = get_object_or_404(CompanyStatusHistory, pk=history_id)
    else:
        h = get_object_or_404(
            CompanyStatusHistory,
            pk=history_id,
            company__region=request.user.profile.region
        )

    company = h.company
    latest  = CompanyStatusHistory.objects.filter(company=company).order_by('-changed_at').first()

    if h.pk == latest.pk:
        messages.error(request, "Нельзя удалить текущую запись истории.")
        return redirect('main:company_detail', pk=company.pk)

    if request.method == 'POST':
        h.delete()
        messages.success(request, "Запись истории удалена.")
        return redirect('main:company_detail', pk=company.pk)

    return render(request, 'main/history_confirm_delete.html', {
        'title':   f'Удалить историю для «{company.name}»',
        'history': h,
        'company': company,
    })

# ─── Профиль пользователя ───────────────────────────────────────────────────
@login_required
def profile(request):
    user = request.user
    qs   = Company.objects.all() if user.is_staff else Company.objects.filter(region=user.profile.region)

    total   = qs.count()
    overdue = 0
    now     = timezone.now()
    for c in qs:
        last = c.history.first()
        if last and last.status and last.status.duration_days:
            if (now - last.changed_at).days > last.status.duration_days:
                overdue += 1

    by_status = (
        qs.values('status__name')
          .annotate(count=Count('id'))
          .order_by('status__name')
    )

    if request.method == 'POST':
        pwd_form = PasswordChangeForm(user, request.POST)
        if pwd_form.is_valid():
            pwd_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Пароль изменён.')
            return redirect('main:profile')
    else:
        pwd_form = PasswordChangeForm(user)

    return render(request, 'main/profile.html', {
        'title':    'Мой профиль',
        'total':    total,
        'overdue':  overdue,
        'by_status': by_status,
        'pwd_form': pwd_form,
    })


# main/views.py
from django.shortcuts import render, redirect
from .forms import SignUpForm
from django.contrib.auth import login

def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("main:index")
    else:
        form = SignUpForm()
    return render(request, "main/signup.html", {"form": form, "title": "Регистрация"})
