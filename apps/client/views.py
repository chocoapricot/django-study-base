# 連絡履歴 詳細
from django.contrib.auth.decorators import permission_required

@permission_required('client.view_clientcontacted', raise_exception=True)
def client_contacted_detail(request, pk):
    from .models import ClientContacted
    contacted = get_object_or_404(ClientContacted, pk=pk)
    client = contacted.client
    return render(request, 'client/client_contacted_detail.html', {'contacted': contacted, 'client': client})
from django.contrib.auth.decorators import login_required, permission_required
def client_contacted_detail(request, pk):
    contacted = get_object_or_404(ClientContacted, pk=pk)
    client = contacted.client
    return render(request, 'client/client_contacted_detail.html', {'contacted': contacted, 'client': client})
import logging
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.db import models
from django.http import JsonResponse
# クライアント連絡履歴用インポート
from .models import Client, ClientContacted, ClientDepartment, ClientUser, ClientFile
from .forms import ClientForm, ClientContactedForm, ClientDepartmentForm, ClientUserForm, ClientFileForm
# from apps.api.helpers import fetch_company_info  # API呼び出し関数をインポート

# ロガーの作成
logger = logging.getLogger('client')

@login_required
@permission_required('client.view_client', raise_exception=True)
def client_list(request):
    sort = request.GET.get('sort', 'corporate_number')
    query = request.GET.get('q', '').strip()
    regist_form_client = request.GET.get('regist_form_client', '').strip()
    
    clients = Client.objects.all()
    
    # キーワード検索
    if query:
        clients = clients.filter(
            Q(name__icontains=query)
            | Q(name_furigana__icontains=query)
            | Q(address__icontains=query)
            | Q(memo__icontains=query)
        )
    
    # 登録区分での絞り込み
    if regist_form_client:
        clients = clients.filter(regist_form_client=regist_form_client)
    
    # ソート可能なフィールドを追加
    sortable_fields = [
        'corporate_number', '-corporate_number',
        'name', '-name',
        'address', '-address',
    ]
    if sort in sortable_fields:
        clients = clients.order_by(sort)
    
    # 登録区分のドロップダウンデータを取得
    from apps.system.settings.models import Dropdowns
    regist_form_options = Dropdowns.objects.filter(
        category='regist_form_client', 
        active=True
    ).order_by('disp_seq')
    
    paginator = Paginator(clients, 10)
    page_number = request.GET.get('page')
    clients_pages = paginator.get_page(page_number)
    
    return render(request, 'client/client_list.html', {
        'clients': clients_pages, 
        'query': query,
        'regist_form_client': regist_form_client,
        'regist_form_options': regist_form_options
    })

@login_required
@permission_required('client.add_client', raise_exception=True)
def client_create(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('client:client_list')
    else:
        form = ClientForm()
    return render(request, 'client/client_form.html', {'form': form})

@login_required
@permission_required('client.view_client', raise_exception=True)
def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk)
    form = ClientForm(instance=client)
    # 連絡履歴（最新5件）
    contacted_list = client.contacted_histories.all()[:5]
    # 組織一覧（最新5件）
    departments = client.departments.all()[:5]
    departments_count = client.departments.count()
    # 担当者一覧（最新5件）
    users = client.users.all()[:5]
    users_count = client.users.count()
    # ファイル情報（最新5件）
    files = client.files.order_by('-uploaded_at')[:5]
    # AppLogに詳細画面アクセスを記録
    from apps.system.logs.utils import log_view_detail
    from apps.system.logs.models import AppLog
    log_view_detail(request.user, client)
    # 変更履歴（AppLogから取得、最新5件）- クライアント、組織、担当者、ファイルの変更を含む
    change_logs = AppLog.objects.filter(
        models.Q(model_name='Client', object_id=str(client.pk)) |
        models.Q(model_name='ClientDepartment', object_repr__startswith=f'{client.name} - ') |
        models.Q(model_name='ClientUser', object_repr__startswith=f'{client.name} - ') |
        models.Q(model_name='ClientFile', object_repr__startswith=f'{client.name} - '),
        action__in=['create', 'update', 'delete']
    ).order_by('-timestamp')[:5]
    change_logs_count = AppLog.objects.filter(
        models.Q(model_name='Client', object_id=str(client.pk)) |
        models.Q(model_name='ClientDepartment', object_repr__startswith=f'{client.name} - ') |
        models.Q(model_name='ClientUser', object_repr__startswith=f'{client.name} - ') |
        models.Q(model_name='ClientFile', object_repr__startswith=f'{client.name} - '),
        action__in=['create', 'update', 'delete']
    ).count()
    return render(request, 'client/client_detail.html', {
        'client': client,
        'form': form,
        'contacted_list': contacted_list,
        'departments': departments,
        'departments_count': departments_count,
        'users': users,
        'users_count': users_count,
        'files': files,
        'change_logs': change_logs,
        'change_logs_count': change_logs_count,
    })

# クライアント変更履歴一覧
@login_required
@permission_required('client.view_client', raise_exception=True)
def client_change_history_list(request, pk):
    client = get_object_or_404(Client, pk=pk)
    from apps.system.logs.models import AppLog
    # クライアント、組織、担当者、ファイルの変更履歴を含む
    logs = AppLog.objects.filter(
        models.Q(model_name='Client', object_id=str(client.pk)) |
        models.Q(model_name='ClientDepartment', object_repr__startswith=f'{client.name} - ') |
        models.Q(model_name='ClientUser', object_repr__startswith=f'{client.name} - ') |
        models.Q(model_name='ClientFile', object_repr__startswith=f'{client.name} - '),
        action__in=['create', 'update', 'delete']
    ).order_by('-timestamp')
    paginator = Paginator(logs, 20)
    page = request.GET.get('page')
    logs_page = paginator.get_page(page)
    return render(request, 'client/client_change_history_list.html', {'client': client, 'logs': logs_page})

# クライアント連絡履歴 登録
@login_required
@permission_required('client.add_clientcontacted', raise_exception=True)
def client_contacted_create(request, client_pk):
    from django.utils import timezone
    client = get_object_or_404(Client, pk=client_pk)
    if request.method == 'POST':
        form = ClientContactedForm(request.POST, client=client)
        if form.is_valid():
            contacted = form.save(commit=False)
            contacted.client = client
            contacted.save()
            return redirect('client:client_detail', pk=client.pk)
    else:
        # デフォルトで現在時刻を設定
        form = ClientContactedForm(client=client, initial={'contacted_at': timezone.now()})
    return render(request, 'client/client_contacted_form.html', {'form': form, 'client': client})

# クライアント連絡履歴 一覧
@login_required
@permission_required('client.view_clientcontacted', raise_exception=True)
def client_contacted_list(request, client_pk):
    client = get_object_or_404(Client, pk=client_pk)
    contacted_qs = client.contacted_histories.all().order_by('-contacted_at')
    paginator = Paginator(contacted_qs, 20)
    page = request.GET.get('page')
    logs = paginator.get_page(page)
    return render(request, 'client/client_contacted_list.html', {'client': client, 'logs': logs})

# クライアント連絡履歴 編集
@login_required
@permission_required('client.change_clientcontacted', raise_exception=True)
def client_contacted_update(request, pk):
    contacted = get_object_or_404(ClientContacted, pk=pk)
    client = contacted.client
    if request.method == 'POST':
        form = ClientContactedForm(request.POST, instance=contacted, client=client)
        if form.is_valid():
            form.save()
            return redirect('client:client_detail', pk=client.pk)
    else:
        form = ClientContactedForm(instance=contacted, client=client)
    return render(request, 'client/client_contacted_form.html', {'form': form, 'client': client, 'contacted': contacted})

@login_required
@permission_required('client.delete_clientcontacted', raise_exception=True)
def client_contacted_delete(request, pk):
    contacted = get_object_or_404(ClientContacted, pk=pk)
    client = contacted.client
    if request.method == 'POST':
        contacted.delete()
        return redirect('client:client_detail', pk=client.pk)
    return render(request, 'client/client_contacted_confirm_delete.html', {'contacted': contacted, 'client': client})

@login_required
@permission_required('client.change_client', raise_exception=True)
def client_update(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            return redirect('client:client_detail', pk=client.pk)
    else:
        form = ClientForm(instance=client)
    return render(request, 'client/client_form.html', {'form': form})

@login_required
@permission_required('client.delete_client', raise_exception=True)
def client_delete(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        client.delete()
        return redirect('client:client_list')
    return render(request, 'client/client_confirm_delete.html', {'client': client})
# views.py



# クライアント組織 CRUD
@login_required
@permission_required('client.add_clientdepartment', raise_exception=True)
def client_department_create(request, client_pk):
    client = get_object_or_404(Client, pk=client_pk)
    if request.method == 'POST':
        form = ClientDepartmentForm(request.POST)
        if form.is_valid():
            department = form.save(commit=False)
            department.client = client
            department.save()
            # 変更履歴を記録
            from apps.system.logs.utils import log_model_action
            log_model_action(request.user, 'create', department)
            return redirect('client:client_detail', pk=client.pk)
    else:
        form = ClientDepartmentForm()
    return render(request, 'client/client_department_form.html', {'form': form, 'client': client, 'show_client_info': True})

@login_required
@permission_required('client.view_clientdepartment', raise_exception=True)
def client_department_list(request, client_pk):
    client = get_object_or_404(Client, pk=client_pk)
    departments = client.departments.all()
    return render(request, 'client/client_department_list.html', {'client': client, 'departments': departments})

@login_required
@permission_required('client.change_clientdepartment', raise_exception=True)
def client_department_update(request, pk):
    department = get_object_or_404(ClientDepartment, pk=pk)
    client = department.client
    if request.method == 'POST':
        form = ClientDepartmentForm(request.POST, instance=department)
        if form.is_valid():
            form.save()
            # 変更履歴を記録
            from apps.system.logs.utils import log_model_action
            log_model_action(request.user, 'update', department)
            return redirect('client:client_detail', pk=client.pk)
    else:
        form = ClientDepartmentForm(instance=department)
    return render(request, 'client/client_department_form.html', {'form': form, 'client': client, 'department': department, 'show_client_info': True})

@login_required
@permission_required('client.delete_clientdepartment', raise_exception=True)
def client_department_delete(request, pk):
    department = get_object_or_404(ClientDepartment, pk=pk)
    client = department.client
    if request.method == 'POST':
        # 変更履歴を記録（削除前に記録）
        from apps.system.logs.utils import log_model_action
        log_model_action(request.user, 'delete', department)
        department.delete()
        return redirect('client:client_detail', pk=client.pk)
    return render(request, 'client/client_department_confirm_delete.html', {'department': department, 'client': client, 'show_client_info': True})

# クライアント担当者 CRUD
@login_required
@permission_required('client.add_clientuser', raise_exception=True)
def client_user_create(request, client_pk):
    client = get_object_or_404(Client, pk=client_pk)
    if request.method == 'POST':
        form = ClientUserForm(request.POST, client=client)
        if form.is_valid():
            user = form.save(commit=False)
            user.client = client
            user.save()
            # 変更履歴を記録
            from apps.system.logs.utils import log_model_action
            log_model_action(request.user, 'create', user)
            return redirect('client:client_detail', pk=client.pk)
    else:
        form = ClientUserForm(client=client)
    return render(request, 'client/client_user_form.html', {'form': form, 'client': client, 'show_client_info': True})

@login_required
@permission_required('client.view_clientuser', raise_exception=True)
def client_user_list(request, client_pk):
    client = get_object_or_404(Client, pk=client_pk)
    users = client.users.all()
    return render(request, 'client/client_user_list.html', {'client': client, 'users': users, 'show_client_info': True})

@login_required
@permission_required('client.change_clientuser', raise_exception=True)
def client_user_update(request, pk):
    user = get_object_or_404(ClientUser, pk=pk)
    client = user.client
    if request.method == 'POST':
        form = ClientUserForm(request.POST, instance=user, client=client)
        if form.is_valid():
            form.save()
            # 変更履歴を記録
            from apps.system.logs.utils import log_model_action
            log_model_action(request.user, 'update', user)
            return redirect('client:client_detail', pk=client.pk)
    else:
        form = ClientUserForm(instance=user, client=client)
    return render(request, 'client/client_user_form.html', {'form': form, 'client': client, 'user': user, 'show_client_info': True})

@login_required
@permission_required('client.delete_clientuser', raise_exception=True)
def client_user_delete(request, pk):
    user = get_object_or_404(ClientUser, pk=pk)
    client = user.client
    if request.method == 'POST':
        # 変更履歴を記録（削除前に記録）
        from apps.system.logs.utils import log_model_action
        log_model_action(request.user, 'delete', user)
        user.delete()
        return redirect('client:client_detail', pk=client.pk)
    return render(request, 'client/client_user_confirm_delete.html', {'user': user, 'client': client, 'show_client_info': True})

# ===== クライアントファイル関連ビュー =====

# クライアントファイル一覧
@login_required
@permission_required('client.view_clientfile', raise_exception=True)
def client_file_list(request, client_pk):
    client = get_object_or_404(Client, pk=client_pk)
    files = client.files.order_by('-uploaded_at')
    
    paginator = Paginator(files, 20)
    page = request.GET.get('page')
    files_page = paginator.get_page(page)
    
    return render(request, 'client/client_file_list.html', {
        'client': client,
        'files': files_page
    })

# クライアントファイル単体アップロード
@login_required
@permission_required('client.add_clientfile', raise_exception=True)
def client_file_create(request, client_pk):
    client = get_object_or_404(Client, pk=client_pk)
    if request.method == 'POST':
        form = ClientFileForm(request.POST, request.FILES)
        if form.is_valid():
            client_file = form.save(commit=False)
            client_file.client = client
            client_file.save()
            from django.contrib import messages
            messages.success(request, 'ファイルをアップロードしました。')
            return redirect('client:client_detail', pk=client.pk)
    else:
        form = ClientFileForm()
    
    return render(request, 'client/client_file_form.html', {
        'form': form,
        'client': client
    })



# クライアントファイル削除
@login_required
@permission_required('client.delete_clientfile', raise_exception=True)
def client_file_delete(request, pk):
    client_file = get_object_or_404(ClientFile, pk=pk)
    client = client_file.client
    
    if request.method == 'POST':
        # ファイルも物理削除
        if client_file.file:
            client_file.file.delete(save=False)
        client_file.delete()
        from django.contrib import messages
        messages.success(request, 'ファイルを削除しました。')
        return redirect('client:client_file_list', client_pk=client.pk)
    
    return render(request, 'client/client_file_confirm_delete.html', {
        'client_file': client_file,
        'client': client
    })

# クライアントファイルダウンロード
@login_required
@permission_required('client.view_clientfile', raise_exception=True)
def client_file_download(request, pk):
    from django.http import FileResponse, Http404
    client_file = get_object_or_404(ClientFile, pk=pk)
    
    try:
        response = FileResponse(
            client_file.file.open('rb'),
            as_attachment=True,
            filename=client_file.original_filename
        )
        return response
    except FileNotFoundError:
        raise Http404("ファイルが見つかりません。")