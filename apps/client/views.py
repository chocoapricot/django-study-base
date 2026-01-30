# 連絡履歴 詳細
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.decorators import login_required, permission_required
import logging
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.db import models
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.core.files.base import ContentFile
from apps.system.logs.utils import log_model_action
from apps.contract.utils import generate_teishokubi_notification_pdf
from apps.company.views import get_current_company
# クライアント連絡履歴用インポート
from .models import Client, ClientContacted, ClientDepartment, ClientUser, ClientFile, ClientContactSchedule
from .forms import ClientForm, ClientContactedForm, ClientDepartmentForm, ClientUserForm, ClientFileForm, ClientContactScheduleForm
from apps.master.models import ClientTag
# from apps.api.helpers import fetch_company_info  # API呼び出し関数をインポート

# ロガーの作成
logger = logging.getLogger('client')

@login_required
@permission_required('client.view_clientcontacted', raise_exception=True)
def client_contacted_detail(request, pk):
    contacted = get_object_or_404(ClientContacted, pk=pk)
    client = contacted.client
    return render(request, 'client/client_contacted_detail.html', {'contacted': contacted, 'client': client})


@login_required
@permission_required('client.view_client', raise_exception=True)
def client_list(request):
    sort = request.GET.get('sort', 'corporate_number')
    query = request.GET.get('q', '').strip()
    client_regist_status = request.GET.get('regist_status', '').strip()
    tag_filter = request.GET.get('tag', '').strip()
    
    clients = Client.objects.all().prefetch_related('tags')
    
    # キーワード検索
    if query:
        if query.startswith('contact_date:'):
            date_str = query.replace('contact_date:', '')
            client_ids = ClientContactSchedule.objects.filter(contact_date=date_str).values_list('client_id', flat=True)
            clients = clients.filter(id__in=client_ids)
        elif query.startswith('contact_date_before:'):
            date_str = query.replace('contact_date_before:', '')
            client_ids = ClientContactSchedule.objects.filter(contact_date__lt=date_str).values_list('client_id', flat=True)
            clients = clients.filter(id__in=client_ids)
        else:
            clients = clients.filter(
                Q(name__icontains=query)
                | Q(name_furigana__icontains=query)
                | Q(address__icontains=query)
                | Q(memo__icontains=query)
            )
    
    # 登録区分での絞り込み
    if client_regist_status:
        clients = clients.filter(regist_status_id=client_regist_status)
    
    # タグでの絞り込み
    if tag_filter:
        clients = clients.filter(tags=tag_filter)

    # ソート可能なフィールドを追加
    sortable_fields = [
        'corporate_number', '-corporate_number',
        'name', '-name',
        'address', '-address',
    ]
    if sort in sortable_fields:
        clients = clients.order_by(sort)
    
    # 登録区分のドロップダウンデータを取得
    from apps.master.models import ClientRegistStatus
    regist_status_options = ClientRegistStatus.objects.filter(is_active=True).order_by('display_order')
    
    # タグのドロップダウンデータを取得
    from apps.master.models import ClientTag
    client_tag_options = ClientTag.objects.filter(is_active=True).order_by('display_order', 'name')
    for option in client_tag_options:
        option.is_selected = (tag_filter == str(option.pk))

    paginator = Paginator(clients, 10)
    page_number = request.GET.get('page')
    clients_pages = paginator.get_page(page_number)

    # 各クライアントに「接続承認済み担当者がいるか」「未承認の接続申請があるか」「連絡予定があるか」フラグを付与
    from apps.connect.models import ConnectClient
    from .models import ClientContactSchedule
    company = get_current_company(request)
    corporate_number = company.corporate_number if company else None
    today = timezone.localdate()
    
    for client in clients_pages:
        client.has_connected_approved_user = False
        client.has_pending_connection_request = False
        client.has_contact_schedule = ClientContactSchedule.objects.filter(client=client, contact_date__gte=today).exists()
        if corporate_number:
            # 承認済みユーザーがいるか
            if ConnectClient.objects.filter(
                corporate_number=corporate_number,
                email__in=client.users.values_list('email', flat=True),
                status='approved'
            ).exists():
                client.has_connected_approved_user = True

            # 未承認の申請があるか
            if ConnectClient.objects.filter(
                corporate_number=corporate_number,
                email__in=client.users.values_list('email', flat=True),
                status='pending'
            ).exists():
                client.has_pending_connection_request = True

    return render(request, 'client/client_list.html', {
        'clients': clients_pages, 
        'query': query,
        'regist_status_filter': client_regist_status,
        'regist_status_options': regist_status_options,
        'tag_filter': tag_filter,
        'client_tag_options': client_tag_options,
    })


@login_required
@permission_required('client.view_client', raise_exception=True)
def client_export(request):
    """クライアントデータのエクスポート（CSV/Excel）"""
    from django.http import HttpResponse
    from .resources import ClientResource
    import datetime
    
    # 検索条件を取得（client_listと同じロジック）
    query = request.GET.get('q', '').strip()
    client_regist_status = request.GET.get('regist_status', '').strip()
    tag_filter = request.GET.get('tag', '').strip()
    format_type = request.GET.get('format', 'csv')
    
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
    if client_regist_status:
        try:
            client_regist_status_int = int(client_regist_status)
            clients = clients.filter(regist_status_id=client_regist_status_int)
        except ValueError:
            pass  # 無効な値の場合はフィルタリングしない

    # タグでの絞り込み
    if tag_filter:
        clients = clients.filter(tags=tag_filter)
    
    # ソート
    clients = clients.order_by('corporate_number')
    
    # リソースを使ってエクスポート
    resource = ClientResource()
    dataset = resource.export(clients)
    
    # ファイル名を生成（日時付き）
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if format_type == 'excel':
        response = HttpResponse(
            dataset.xlsx,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="clients_{timestamp}.xlsx"'
    else:  # CSV
        # BOMを追加してExcelで正しく表示されるようにする
        csv_data = '\ufeff' + dataset.csv
        response = HttpResponse(csv_data, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="clients_{timestamp}.csv"'
    
    return response

@login_required
@permission_required('client.add_client', raise_exception=True)
def client_create(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save()
            messages.success(request, f'クライアント「{client.name}」を作成しました。')
            return redirect('client:client_detail', pk=client.pk)
    else:
        form = ClientForm()
    return render(request, 'client/client_form.html', {'form': form})

@login_required
@permission_required('client.view_client', raise_exception=True)
def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk)
    form = ClientForm(instance=client)
    # 連絡履歴と予定を統合
    all_contacts = []
    
    # 最近の履歴を取得
    for c in client.contacted_histories.all()[:10]:
        all_contacts.append({
            'type': 'history',
            'pk': c.pk,
            'contact_type': c.contact_type,
            'content': c.content,
            'created_by': c.created_by,
            'at': c.contacted_at,
            'is_schedule': False,
        })
    
    # 最近の予定を取得
    for s in client.contact_schedules.all()[:10]:
        import datetime
        # DateFieldをDateTimeField的に扱ってソート可能にする
        dt = timezone.make_aware(datetime.datetime.combine(s.contact_date, datetime.time.min))
        all_contacts.append({
            'type': 'schedule',
            'pk': s.pk,
            'contact_type': s.contact_type,
            'content': s.content,
            'created_by': s.created_by,
            'at': dt, # ソート用
            'display_date': s.contact_date, # 表示用
            'is_schedule': True,
        })
    
    # 日付の降順でソート
    all_contacts.sort(key=lambda x: x['at'], reverse=True)
    contacted_combined_list = all_contacts[:5]

    # クライアント契約（最新5件）
    from apps.contract.models import ClientContract
    client_contracts = ClientContract.objects.filter(client=client).order_by('-start_date')[:5]
    client_contracts_count = ClientContract.objects.filter(client=client).count()
    # 組織一覧（最新5件）
    departments = client.departments.all()[:5]
    departments_count = client.departments.count()
    # 担当者一覧（最新5件）
    client_users = client.users.all()[:5]
    # 各担当者が接続承認済みか、未承認の接続申請があるかを付与
    from apps.connect.models import ConnectClient
    from django.db.models import Q
    
    company = get_current_company(request)
    corporate_number = company.corporate_number if company else None
    today = timezone.localdate()
    
    if corporate_number:
        for user in client_users:
            user.is_connected_approved = False
            user.has_pending_connection_request = False
            if user.email:
                user.is_connected_approved = ConnectClient.objects.filter(
                    corporate_number=corporate_number,
                    email=user.email,
                    status='approved'
                ).exists()
                user.has_pending_connection_request = ConnectClient.objects.filter(
                    corporate_number=corporate_number,
                    email=user.email,
                    status='pending'
                ).exists()
            
            # 派遣先責任者として指定されているか確認
            user.is_client_responsible = ClientContract.objects.filter(
                client=client,
                haken_info__responsible_person_client=user,
                start_date__lte=today,
            ).filter(
                Q(end_date__gte=today) | Q(end_date__isnull=True)
            ).exists()
            
            # 派遣先苦情申出先として指定されているか確認
            user.is_client_complaint_officer = ClientContract.objects.filter(
                client=client,
                haken_info__complaint_officer_client=user,
                start_date__lte=today,
            ).filter(
                Q(end_date__gte=today) | Q(end_date__isnull=True)
            ).exists()
            
            # 派遣先指揮命令者として指定されているか確認
            user.is_client_commander = ClientContract.objects.filter(
                client=client,
                haken_info__commander=user,
                start_date__lte=today,
            ).filter(
                Q(end_date__gte=today) | Q(end_date__isnull=True)
            ).exists()
    else:
        for user in client_users:
            user.is_connected_approved = False
            user.has_pending_connection_request = False
            user.is_client_responsible = False
            user.is_client_complaint_officer = False
            user.is_client_commander = False
    users_count = client.users.count()
    # ファイル情報（最新5件）
    files = client.files.order_by('-uploaded_at')[:5]
    # AppLogに詳細画面アクセスを記録
    from apps.system.logs.utils import log_view_detail
    from apps.system.logs.models import AppLog
    log_view_detail(request.user, client)
    # 変更履歴（AppLogから取得、最新5件）- クライアント、組織、担当者、ファイルの変更を含む
    department_ids = list(client.departments.values_list('pk', flat=True))
    user_ids = list(client.users.values_list('pk', flat=True))
    file_ids = list(client.files.values_list('pk', flat=True))

    change_logs_query = AppLog.objects.filter(
        models.Q(model_name='Client', object_id=str(client.pk)) |
        models.Q(model_name='ClientDepartment', object_id__in=[str(pk) for pk in department_ids]) |
        models.Q(model_name='ClientUser', object_id__in=[str(pk) for pk in user_ids]) |
        models.Q(model_name='ClientFile', object_id__in=[str(pk) for pk in file_ids]),
        action__in=['create', 'update', 'delete']
    )
    
    change_logs = change_logs_query.order_by('-timestamp')[:5]
    change_logs_count = change_logs_query.count()

    return render(request, 'client/client_detail.html', {
        'client': client,
        'form': form,
        'contacted_combined_list': contacted_combined_list,
        'client_contracts': client_contracts,
        'client_contracts_count': client_contracts_count,
        'departments': departments,
        'departments_count': departments_count,
        'client_users': client_users,
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
    from django.db import models

    # Get IDs of all related objects
    department_ids = list(client.departments.values_list('pk', flat=True))
    user_ids = list(client.users.values_list('pk', flat=True))
    file_ids = list(client.files.values_list('pk', flat=True))

    # クライアント、組織、担当者、ファイルの変更履歴を含む
    logs = AppLog.objects.filter(
        models.Q(model_name='Client', object_id=str(client.pk)) |
        models.Q(model_name='ClientDepartment', object_id__in=[str(pk) for pk in department_ids]) |
        models.Q(model_name='ClientUser', object_id__in=[str(pk) for pk in user_ids]) |
        models.Q(model_name='ClientFile', object_id__in=[str(pk) for pk in file_ids]),
        action__in=['create', 'update', 'delete']
    ).order_by('-timestamp')
    
    paginator = Paginator(logs, 20)
    page = request.GET.get('page')
    logs_page = paginator.get_page(page)

    context = {
        'object': client,
        'client': client,
        'change_logs': logs_page,
        'page_title': 'クライアント関連 変更履歴一覧',
        'back_url_name': 'client:client_detail',
        'info_card_path': 'client/_client_info_card.html',
    }
    return render(request, 'common/common_change_history_list.html', context)

# クライアント連絡履歴 登録
@login_required
@permission_required('client.add_clientcontacted', raise_exception=True)
def client_contacted_create(request, client_pk):
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
            log_model_action(request.user, 'update', contacted)
            messages.success(request, '連絡履歴を更新しました。')
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
            # 変更があったかどうかをチェック
            if form.has_changed():
                client = form.save()
                log_model_action(request.user, 'update', client)
                messages.success(request, f'クライアント「{client.name}」を更新しました。')
            else:
                messages.info(request, '変更はありませんでした。')
            return redirect('client:client_detail', pk=client.pk)
    else:
        form = ClientForm(instance=client)
    return render(request, 'client/client_form.html', {'form': form})

@login_required
@permission_required('client.delete_client', raise_exception=True)
def client_delete(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        client_name = client.name
        client.delete()
        messages.success(request, f'クライアント「{client_name}」を削除しました。')
        return redirect('client:client_list')
    return render(request, 'client/client_confirm_delete.html', {'client': client})
# views.py



# クライアント組織 CRUD
@login_required
@permission_required('client.add_clientdepartment', raise_exception=True)
def client_department_create(request, client_pk):
    client = get_object_or_404(Client, pk=client_pk)
    if request.method == 'POST':
        form = ClientDepartmentForm(request.POST, client=client)
        if form.is_valid():
            department = form.save(commit=False)
            department.client = client
            department.save()
            # 変更履歴を記録
            from apps.system.logs.utils import log_model_action
            log_model_action(request.user, 'create', department)
            return redirect('client:client_detail', pk=client.pk)
    else:
        form = ClientDepartmentForm(client=client)
    return render(request, 'client/client_department_form.html', {'form': form, 'client': client, 'show_client_info': True})

@login_required
@permission_required('client.view_clientdepartment', raise_exception=True)
def client_department_list(request, client_pk):
    client = get_object_or_404(Client, pk=client_pk)
    departments = client.departments.all()
    return render(request, 'client/client_department_list.html', {'client': client, 'departments': departments})


# クライアント組織 変更履歴一覧
@login_required
@permission_required('client.view_clientdepartment', raise_exception=True)
def client_department_change_history_list(request, pk):
    department = get_object_or_404(ClientDepartment, pk=pk)
    client = department.client
    from apps.system.logs.models import AppLog

    logs = AppLog.objects.filter(
        model_name='ClientDepartment',
        object_id=str(pk),
        action__in=['create', 'update', 'delete']
    ).order_by('-timestamp')

    paginator = Paginator(logs, 20)
    page = request.GET.get('page')
    logs_page = paginator.get_page(page)

    return render(request, 'client/client_department_change_history_list.html', {
        'client': client,
        'department': department,
        'logs': logs_page
    })


# クライアント組織詳細
@login_required
@permission_required('client.view_clientdepartment', raise_exception=True)
def client_department_detail(request, pk):
    """クライアント組織詳細"""
    department = get_object_or_404(ClientDepartment, pk=pk)
    client = department.client

    # AppLogに詳細画面アクセスを記録
    from apps.system.logs.utils import log_view_detail
    from apps.system.logs.models import AppLog
    log_view_detail(request.user, department)

    # この組織に所属する担当者
    users_in_department = department.users.all()
    users_count = users_in_department.count()
    
    # 各担当者にバッジ情報を追加
    from django.db.models import Q
    from apps.contract.models import ClientContract
    
    today = timezone.localdate()
    
    for user in users_in_department:
        # 派遣先責任者として指定されているか確認
        user.is_client_responsible = ClientContract.objects.filter(
            client=client,
            haken_info__responsible_person_client=user,
            start_date__lte=today,
        ).filter(
            Q(end_date__gte=today) | Q(end_date__isnull=True)
        ).exists()
        
        # 派遣先苦情申出先として指定されているか確認
        user.is_client_complaint_officer = ClientContract.objects.filter(
            client=client,
            haken_info__complaint_officer_client=user,
            start_date__lte=today,
        ).filter(
            Q(end_date__gte=today) | Q(end_date__isnull=True)
        ).exists()
        
        # 派遣先指揮命令者として指定されているか確認
        user.is_client_commander = ClientContract.objects.filter(
            client=client,
            haken_info__commander=user,
            start_date__lte=today,
        ).filter(
            Q(end_date__gte=today) | Q(end_date__isnull=True)
        ).exists()

    # 変更履歴（AppLogから取得）
    change_logs_query = AppLog.objects.filter(
        model_name='ClientDepartment',
        object_id=str(department.pk),
        action__in=['create', 'update', 'delete']
    )
    change_logs = change_logs_query.order_by('-timestamp')[:5]
    change_logs_count = change_logs_query.count()

    return render(request, 'client/client_department_detail.html', {
        'department': department,
        'client': client,
        'users_in_department': users_in_department,
        'users_count': users_count,
        'change_logs': change_logs,
        'change_logs_count': change_logs_count,
    })


@login_required
@permission_required('client.change_clientdepartment', raise_exception=True)
def client_department_update(request, pk):
    department = get_object_or_404(ClientDepartment, pk=pk)
    client = department.client
    if request.method == 'POST':
        form = ClientDepartmentForm(request.POST, instance=department, client=client)
        if form.is_valid():
            form.save()
            # 変更履歴を記録
            from apps.system.logs.utils import log_model_action
            log_model_action(request.user, 'update', department)
            return redirect('client:client_detail', pk=client.pk)
    else:
        form = ClientDepartmentForm(instance=department, client=client)
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
    client_users = client.users.all()
    # 各担当者が接続承認済みか、未承認の接続申請があるかを付与
    from apps.connect.models import ConnectClient
    from django.db.models import Q
    from apps.contract.models import ClientContract
    
    company = get_current_company(request)
    corporate_number = company.corporate_number if company else None
    today = timezone.localdate()
    
    if corporate_number:
        for user in client_users:
            user.is_connected_approved = False
            user.has_pending_connection_request = False
            if user.email:
                user.is_connected_approved = ConnectClient.objects.filter(
                    corporate_number=corporate_number,
                    email=user.email,
                    status='approved'
                ).exists()
                user.has_pending_connection_request = ConnectClient.objects.filter(
                    corporate_number=corporate_number,
                    email=user.email,
                    status='pending'
                ).exists()
            
            # 派遣先責任者として指定されているか確認
            user.is_client_responsible = ClientContract.objects.filter(
                client=client,
                haken_info__responsible_person_client=user,
                start_date__lte=today,
            ).filter(
                Q(end_date__gte=today) | Q(end_date__isnull=True)
            ).exists()
            
            # 派遣先苦情申出先として指定されているか確認
            user.is_client_complaint_officer = ClientContract.objects.filter(
                client=client,
                haken_info__complaint_officer_client=user,
                start_date__lte=today,
            ).filter(
                Q(end_date__gte=today) | Q(end_date__isnull=True)
            ).exists()
            
            # 派遣先指揮命令者として指定されているか確認
            user.is_client_commander = ClientContract.objects.filter(
                client=client,
                haken_info__commander=user,
                start_date__lte=today,
            ).filter(
                Q(end_date__gte=today) | Q(end_date__isnull=True)
            ).exists()
    else:
        for user in client_users:
            user.is_connected_approved = False
            user.has_pending_connection_request = False
            user.is_client_responsible = False
            user.is_client_complaint_officer = False
            user.is_client_commander = False
    return render(request, 'client/client_user_list.html', {'client': client, 'client_users': client_users, 'show_client_info': True})

@login_required
@permission_required('client.change_clientuser', raise_exception=True)
def client_user_update(request, pk):
    client_user = get_object_or_404(ClientUser, pk=pk)
    client = client_user.client
    if request.method == 'POST':
        form = ClientUserForm(request.POST, instance=client_user, client=client)
        if form.is_valid():
            form.save()
            # 変更履歴を記録
            from apps.system.logs.utils import log_model_action
            log_model_action(request.user, 'update', client_user)
            return redirect('client:client_detail', pk=client.pk)
    else:
        form = ClientUserForm(instance=client_user, client=client)
    return render(request, 'client/client_user_form.html', {'form': form, 'client': client, 'client_user': client_user, 'show_client_info': True})

@login_required
@permission_required('client.delete_clientuser', raise_exception=True)
def client_user_delete(request, pk):
    client_user = get_object_or_404(ClientUser, pk=pk)
    client = client_user.client
    if request.method == 'POST':
        # 変更履歴を記録（削除前に記録）
        from apps.system.logs.utils import log_model_action
        log_model_action(request.user, 'delete', client_user)
        client_user.delete()
        return redirect('client:client_detail', pk=client.pk)
    return render(request, 'client/client_user_confirm_delete.html', {'client_user': client_user, 'client': client, 'show_client_info': True})

# クライアント担当者詳細
@login_required
@permission_required('client.view_clientuser', raise_exception=True)
def client_user_detail(request, pk):
    """クライアント担当者詳細"""
    client_user = get_object_or_404(ClientUser, pk=pk)
    client = client_user.client
    
    company = get_current_company(request)

    # 接続申請の状況を確認
    connect_request = None
    if client_user.email and company and company.corporate_number:
        from apps.connect.models import ConnectClient
        connect_request = ConnectClient.objects.filter(
            corporate_number=company.corporate_number,
            email=client_user.email
        ).first()
    
    # 接続申請の切り替え処理
    if request.method == 'POST' and 'toggle_connect_request' in request.POST:
        if client_user.email and company and company.corporate_number:
            from apps.connect.models import ConnectClient
            from apps.system.logs.utils import log_model_action
            
            existing_request = ConnectClient.objects.filter(
                corporate_number=company.corporate_number,
                email=client_user.email
            ).first()
            
            if existing_request:
                # 既存の申請を削除
                existing_request.delete()
                
                # グループ削除チェック
                from apps.connect.utils import remove_user_from_client_group_if_no_requests
                remove_user_from_client_group_if_no_requests(client_user.email)
                
                messages.success(request, 'クライアント接続申請を取り消しました。')
                connect_request = None
            else:
                # 新しい申請を作成
                connect_request = ConnectClient.objects.create(
                    corporate_number=company.corporate_number,
                    email=client_user.email,
                    created_by=request.user,
                    updated_by=request.user
                )
                log_model_action(request.user, 'create', connect_request)
                
                # 既存ユーザーがいる場合は権限を付与
                from apps.connect.utils import grant_client_permissions_on_connection_request
                grant_client_permissions_on_connection_request(client_user.email)
                
                messages.success(request, f'クライアント担当者「{client_user.name}」への接続申請を送信しました。')
        else:
            messages.error(request, 'メールアドレスまたは法人番号が設定されていません。')
        
        return redirect('client:client_user_detail', pk=pk)
    
    # AppLogに詳細画面アクセスを記録
    from apps.system.logs.utils import log_view_detail
    from apps.system.logs.models import AppLog
    log_view_detail(request.user, client_user)
    
    # 変更履歴（AppLogから取得、最新5件）
    change_logs = AppLog.objects.filter(
        model_name='ClientUser',
        object_id=str(client_user.pk),
        action__in=['create', 'update', 'delete']
    ).order_by('-timestamp')[:5]
    
    # 関連するクライアント契約を取得
    from django.db.models import Q
    from apps.contract.models import ClientContract
    
    today = timezone.localdate()
    
    # 派遣先責任者、苦情申出先、指揮命令者として指定されているクライアント契約を統合取得
    related_contracts = ClientContract.objects.filter(
        Q(haken_info__responsible_person_client=client_user) |
        Q(haken_info__complaint_officer_client=client_user) |
        Q(haken_info__commander=client_user),
        client=client,
        start_date__lte=today,
    ).filter(
        Q(end_date__gte=today) | Q(end_date__isnull=True)
    ).select_related('client', 'haken_info').distinct().order_by('start_date')

    # 各契約に役割情報を追加
    for contract in related_contracts:
        contract.is_responsible_role = (contract.haken_info.responsible_person_client == client_user)
        contract.is_complaint_role = (contract.haken_info.complaint_officer_client == client_user)
        contract.is_commander_role = (contract.haken_info.commander == client_user)
    
    return render(request, 'client/client_user_detail.html', {
        'client_user': client_user,
        'client': client,
        'connect_request': connect_request,
        'change_logs': change_logs,
        'related_contracts': related_contracts,
    })

# クライアント担当者メール送信
@login_required
@permission_required('client.view_clientuser', raise_exception=True)
def client_user_mail_send(request, pk):
    """クライアント担当者メール送信"""
    from .models import ClientUser
    user = get_object_or_404(ClientUser, pk=pk)
    client = user.client
    
    # メールアドレスが設定されていない場合はエラー
    if not user.email:
        from django.contrib import messages
        messages.error(request, 'この担当者にはメールアドレスが設定されていません。')
        return redirect('client:client_user_list', client_pk=client.pk)
    
    from .forms_mail import ClientUserMailForm
    
    if request.method == 'POST':
        form = ClientUserMailForm(client_user=user, user=request.user, data=request.POST)
        if form.is_valid():
            success, message = form.send_mail()
            from django.contrib import messages
            if success:
                messages.success(request, message)
                return redirect('client:client_user_list', client_pk=client.pk)
            else:
                messages.error(request, message)
    else:
        form = ClientUserMailForm(client_user=user, user=request.user)
    
    context = {
        'form': form,
        'client_user': user,
        'client': client,
        'title': f'{user.name} へのメール送信',
        'show_client_info': True,
    }
    return render(request, 'client/client_user_mail_send.html', context)

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
        # ファイルの存在確認
        if not client_file.file or not client_file.file.name:
            messages.error(request, f'ファイル「{client_file.original_filename}」の情報が見つかりません。')
            return redirect('client:client_detail', pk=client_file.client.pk)
        
        # 物理ファイルの存在確認
        import os
        if not os.path.exists(client_file.file.path):
            messages.error(request, f'ファイル「{client_file.original_filename}」が見つかりません。ファイルが削除されている可能性があります。')
            return redirect('client:client_detail', pk=client_file.client.pk)
        
        response = FileResponse(
            client_file.file.open('rb'),
            as_attachment=True,
            filename=client_file.original_filename
        )
        return response
    except (FileNotFoundError, OSError, ValueError) as e:
        messages.error(request, f'ファイル「{client_file.original_filename}」のダウンロードに失敗しました。ファイルが削除されている可能性があります。')
        return redirect('client:client_detail', pk=client_file.client.pk)
    except Exception as e:
        messages.error(request, f'ファイルのダウンロード中にエラーが発生しました: {str(e)}')
        return redirect('client:client_detail', pk=client_file.client.pk)


@login_required
@permission_required('contract.change_clientcontract', raise_exception=True)
def issue_teishokubi_notification_from_department(request, pk):
    """クライアント組織から抵触日通知書を発行する"""
    department = get_object_or_404(ClientDepartment, pk=pk)

    # 派遣事業所でない場合はエラー
    if not department.is_haken_office:
        messages.error(request, 'この組織は派遣事業所ではないため、抵触日通知書を発行できません。')
        return redirect('client:client_department_detail', pk=pk)

    # 抵触日が設定されているか確認
    if not department.haken_jigyosho_teishokubi:
        messages.error(request, '派遣事業所の抵触日が設定されていません。')
        return redirect('client:client_department_detail', pk=pk)

    issued_at = timezone.now()
    # 組織オブジェクトを渡して、透かしなしで生成
    pdf_content, pdf_filename, document_title = generate_teishokubi_notification_pdf(department, request.user, issued_at)

    if pdf_content:
        # 発行履歴は保存しない
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{pdf_filename}"'
        return response
    else:
        messages.error(request, "抵触日通知書のPDFの生成に失敗しました。")
        return redirect('client:client_department_detail', pk=pk)


# クライアント連絡予定 登録
@login_required
@permission_required('client.add_clientcontactschedule', raise_exception=True)
def client_contact_schedule_create(request, client_pk):
    client = get_object_or_404(Client, pk=client_pk)
    if request.method == 'POST':
        form = ClientContactScheduleForm(request.POST, client=client)
        if form.is_valid():
            contact_schedule = form.save(commit=False)
            contact_schedule.client = client
            contact_schedule.save()
            return redirect('client:client_detail', pk=client.pk)
    else:
        form = ClientContactScheduleForm(client=client, initial={'contact_date': timezone.now()})
    return render(request, 'client/client_contact_schedule_form.html', {'form': form, 'client': client})

# クライアント連絡予定 一覧
@login_required
@permission_required('client.view_clientcontactschedule', raise_exception=True)
def client_contact_schedule_list(request, client_pk):
    client = get_object_or_404(Client, pk=client_pk)
    contact_schedule_qs = client.contact_schedules.all().order_by('-contact_date')
    paginator = Paginator(contact_schedule_qs, 20)
    page = request.GET.get('page')
    schedules = paginator.get_page(page)
    return render(request, 'client/client_contact_schedule_list.html', {'client': client, 'schedules': schedules})

# クライアント連絡予定 詳細
@login_required
@permission_required('client.view_clientcontactschedule', raise_exception=True)
def client_contact_schedule_detail(request, pk):
    schedule = get_object_or_404(ClientContactSchedule, pk=pk)
    client = schedule.client

    from .forms_mail import ClientMailForm

    # メールアドレスが設定されている担当者がいるか確認
    has_email_users = ClientUser.objects.filter(client=client, email__isnull=False).exclude(email='').exists()

    if request.method == 'POST':
        if 'register_history' in request.POST:
            form = ClientContactedForm(request.POST, client=client)
            if form.is_valid():
                contacted = form.save(commit=False)
                contacted.client = client
                contacted.save()
                # 予定を削除
                schedule.delete()
                messages.success(request, '連絡履歴を登録し、対応予定を完了（削除）しました。')
                return redirect('client:client_detail', pk=client.pk)
            # バリデーションエラー時はmail_formを初期化
            mail_form = ClientMailForm(client=client, user=request.user)
        elif 'send_mail' in request.POST:
            mail_form = ClientMailForm(client=client, user=request.user, data=request.POST)
            if mail_form.is_valid():
                success, message = mail_form.send_mail()
                if success:
                    # 予定を削除
                    schedule.delete()
                    messages.success(request, f'{message} および連絡予定を完了（削除）しました。')
                    return redirect('client:client_detail', pk=client.pk)
                else:
                    messages.error(request, message)
            # バリデーションエラー時はformを初期化
            initial_data = {
                'department': schedule.department,
                'user': schedule.user,
                'contact_type': schedule.contact_type,
                'content': schedule.content,
                'detail': schedule.detail,
                'contacted_at': timezone.now()
            }
            form = ClientContactedForm(client=client, initial=initial_data)
        else:
            return redirect('client:client_contact_schedule_detail', pk=pk)
    else:
        # 予定の内容を初期値としてセット
        initial_data = {
            'department': schedule.department,
            'user': schedule.user,
            'contact_type': schedule.contact_type,
            'content': schedule.content,
            'detail': schedule.detail,
            'contacted_at': timezone.now()
        }
        form = ClientContactedForm(client=client, initial=initial_data)

        # メール初期値
        initial_mail_data = {
            'subject': f"ご連絡: {schedule.content}",
            'body': schedule.detail if schedule.detail else "",
        }
        # 予定に紐づく担当者にメールアドレスがあれば、初期選択とする
        if schedule.user and schedule.user.email:
            initial_mail_data['to_user'] = schedule.user

        mail_form = ClientMailForm(client=client, user=request.user, initial=initial_mail_data)

    from apps.system.logs.utils import log_view_detail
    log_view_detail(request.user, schedule)
    return render(request, 'client/client_contact_schedule_detail.html', {
        'schedule': schedule,
        'client': client,
        'form': form,
        'mail_form': mail_form,
        'has_email_users': has_email_users
    })

# クライアント連絡予定 編集
@login_required
@permission_required('client.change_clientcontactschedule', raise_exception=True)
def client_contact_schedule_update(request, pk):
    schedule = get_object_or_404(ClientContactSchedule, pk=pk)
    client = schedule.client
    if request.method == 'POST':
        form = ClientContactScheduleForm(request.POST, instance=schedule, client=client)
        if form.is_valid():
            form.save()
            messages.success(request, '連絡予定を更新しました。')
            return redirect('client:client_detail', pk=client.pk)
    else:
        form = ClientContactScheduleForm(instance=schedule, client=client)
    return render(request, 'client/client_contact_schedule_form.html', {'form': form, 'client': client, 'schedule': schedule})

# クライアント連絡予定 削除
@login_required
@permission_required('client.delete_clientcontactschedule', raise_exception=True)
def client_contact_schedule_delete(request, pk):
    schedule = get_object_or_404(ClientContactSchedule, pk=pk)
    client = schedule.client
    if request.method == 'POST':
        schedule.delete()
        return redirect('client:client_detail', pk=client.pk)
    return render(request, 'client/client_contact_schedule_confirm_delete.html', {'schedule': schedule, 'client': client})

@login_required
@permission_required('client.change_client', raise_exception=True)
def client_tag_edit(request, pk):
    """クライアントタグ編集ビュー"""
    client = get_object_or_404(Client, pk=pk)
    all_tags = ClientTag.objects.filter(is_active=True).order_by('display_order')
    
    if request.method == 'POST':
        tag_ids = request.POST.getlist('tags')
        # 現在のタグ名を取得（ログ用）
        old_tags = ", ".join([t.name for t in client.tags.all()])
        
        # タグの更新
        client.tags.set(tag_ids)
        
        # 新しいタグ名を取得（ログ用）
        new_tags = ", ".join([t.name for t in client.tags.all()])
        
        # 変更があった場合のみログを記録
        if old_tags != new_tags:
            from apps.system.logs.utils import log_model_action
            from apps.system.logs.models import AppLog
            # 基本的な更新ログ
            log_model_action(request.user, 'update', client)
            # 詳細な変更ログ
            AppLog.objects.create(
                user=request.user,
                action='update',
                model_name='Client',
                object_id=str(client.pk),
                object_repr=f"タグを変更しました: [{old_tags}] -> [{new_tags}]"
            )
            messages.success(request, 'クライアントのタグを更新しました。')
        
        return redirect('client:client_detail', pk=client.pk)
    
    current_tag_ids = list(client.tags.values_list('pk', flat=True))
    
    return render(request, 'client/client_tag_edit.html', {
        'client': client,
        'all_tags': all_tags,
        'current_tag_ids': current_tag_ids,
    })
