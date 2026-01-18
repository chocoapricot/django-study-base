from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.http import url_has_allowed_host_and_scheme
from apps.system.logs.utils import log_model_action
from apps.system.logs.models import AppLog
from apps.common.constants import Constants
from .models import ConnectStaff, ConnectClient, ConnectStaffAgree
from apps.master.models import StaffAgreement
from .forms import StaffAgreeForm
from django.urls import reverse

@login_required
def connect_staff_list(request):
    """スタッフ接続一覧"""
    # 管理者の場合は全ての接続、そうでない場合は自分宛の接続を表示
    if request.user.is_staff:
        connections = ConnectStaff.objects.all()
    else:
        connections = ConnectStaff.objects.filter(email=request.user.email)
    
    # 検索機能
    search_query = request.GET.get('q', '')
    if search_query:
        connections = connections.filter(
            Q(corporate_number__icontains=search_query)
        )
    
    # ステータスフィルター
    status_filter = request.GET.get('status', '')
    if status_filter:
        connections = connections.filter(status=status_filter)
    
    # ページネーション
    paginator = Paginator(connections, 20)
    page_number = request.GET.get('page')
    connections = paginator.get_page(page_number)
    
    # 会社情報を取得（法人番号から）
    from apps.company.models import Company
    companies = {}
    for conn in connections:
        if conn.corporate_number not in companies:
            try:
                company = Company.objects.get(corporate_number=conn.corporate_number)
                companies[conn.corporate_number] = company
            except Company.DoesNotExist:
                companies[conn.corporate_number] = None
    
    return render(request, 'connect/staff_list.html', {
        'connections': connections,
        'companies': companies,
        'search_query': search_query,
        'status_filter': status_filter,
    })


@login_required
@require_POST
def connect_staff_approve(request, pk):
    """スタッフ接続を承認"""
    connection = get_object_or_404(ConnectStaff, pk=pk)

    if not (request.user.is_staff or connection.email == request.user.email):
        messages.error(request, 'この申請を承認する権限がありません。')
        return redirect('connect:staff_list')

    # 有効な同意書を取得
    required_agreements = StaffAgreement.objects.filter(
        corporation_number=connection.corporate_number,
        is_active=True
    )
    if required_agreements.exists():
        # 同意済みのものを取得
        agreed_pks = ConnectStaffAgree.objects.filter(
            email=connection.email,
            corporate_number=connection.corporate_number,
            is_agreed=True
        ).values_list('staff_agreement__pk', flat=True)

        # 未同意のものを特定
        unagreed_agreements = required_agreements.exclude(pk__in=agreed_pks)
        if unagreed_agreements.exists():
            # 未同意の同意書があれば、同意画面にリダイレクト
            return redirect(reverse('connect:staff_agree', kwargs={'pk': pk}))

    if connection.status == Constants.CONNECT_STATUS.PENDING:
        connection.approve(request.user)
        
        from apps.staff.models import Staff
        try:
            staff = Staff.objects.get(email=connection.email)
            AppLog.objects.create(
                user=request.user,
                model_name='ConnectStaff',
                object_id=str(staff.pk),
                object_repr=f'{staff} - 接続承認',
                action='update'
            )
        except Staff.DoesNotExist:
            log_model_action(request.user, 'update', connection)
        
        from .utils import grant_permissions_on_connection_request, grant_profile_permissions, grant_staff_contract_confirmation_permission
        from django.contrib.auth import get_user_model
        User = get_user_model()

        grant_permissions_on_connection_request(connection.email)
        
        try:
            user = User.objects.get(email=connection.email)
            grant_profile_permissions(user)
            grant_staff_contract_confirmation_permission(user)
        except User.DoesNotExist:
            print(f"[ERROR] 権限付与対象のユーザーが見つかりません: {connection.email}")
        
        messages.success(request, '接続申請を承認しました。')
    else:
        messages.info(request, 'この申請は既に承認済みです。')

    next_url = request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    
    return redirect('connect:staff_list')


@login_required
def staff_agree(request, pk):
    """スタッフの同意取得画面"""
    connection = get_object_or_404(ConnectStaff, pk=pk)

    # 会社情報を取得
    from apps.company.models import Company
    try:
        company = Company.objects.get(corporate_number=connection.corporate_number)
    except Company.DoesNotExist:
        company = None

    required_agreements = StaffAgreement.objects.filter(
        corporation_number=connection.corporate_number,
        is_active=True
    )
    agreed_pks = ConnectStaffAgree.objects.filter(
        email=connection.email,
        corporate_number=connection.corporate_number,
        is_agreed=True
    ).values_list('staff_agreement__pk', flat=True)
    unagreed_agreements = required_agreements.exclude(pk__in=agreed_pks)

    if not unagreed_agreements.exists():
        messages.info(request, "すべての必要な同意は完了しています。")
        return redirect('connect:staff_list')

    if request.method == 'POST':
        form = StaffAgreeForm(request.POST, agreements_queryset=unagreed_agreements)
        if form.is_valid():
            for agreement in form.cleaned_data['agreements']:
                ConnectStaffAgree.objects.update_or_create(
                    email=connection.email,
                    corporate_number=connection.corporate_number,
                    staff_agreement=agreement,
                    defaults={'is_agreed': True}
                )

            # nextパラメータがあればそちらにリダイレクト
            next_url = request.GET.get('next')
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)

            # 同意が得られたので、再度承認処理を試みる
            return connect_staff_approve(request, pk)
    else:
        form = StaffAgreeForm(agreements_queryset=unagreed_agreements)

    return render(request, 'connect/staff_agree.html', {
        'form': form,
        'connection': connection,
        'company': company,
        'unagreed_agreements': unagreed_agreements,
    })


@login_required
@require_POST
def connect_staff_unapprove(request, pk):
    """スタッフ接続を未承認に戻す"""
    connection = get_object_or_404(ConnectStaff, pk=pk)
    
    # 権限チェック：管理者または申請対象者本人のみ未承認に戻すことが可能
    if not (request.user.is_staff or connection.email == request.user.email):
        messages.error(request, 'この申請を変更する権限がありません。')
        return redirect('connect:staff_list')
    
    if connection.status == Constants.CONNECT_STATUS.APPROVED:
        connection.unapprove()
        
        # スタッフの変更履歴に記録するため、スタッフIDを取得
        from apps.staff.models import Staff
        try:
            staff = Staff.objects.get(email=connection.email)
            # スタッフの変更履歴として記録
            AppLog.objects.create(
                user=request.user,
                model_name='ConnectStaff',
                object_id=str(staff.pk),
                object_repr=f'{staff} - 接続承認取り消し',
                action='update'
            )
        except Staff.DoesNotExist:
            # スタッフが見つからない場合は通常のログ記録
            log_model_action(request.user, 'update', connection)
        
        messages.success(request, '接続申請を未承認に戻しました。')
    else:
        messages.info(request, 'この申請は未承認です。')

    next_url = request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    
    return redirect('connect:staff_list')

@login_required
@permission_required('connect.view_connectclient', raise_exception=True)
def connect_client_list(request):
    """クライアント接続一覧"""
    # 管理者の場合は全ての接続、そうでない場合は自分宛の接続を表示
    if request.user.is_staff:
        connections = ConnectClient.objects.all()
    else:
        connections = ConnectClient.objects.filter(email=request.user.email)
    
    # 検索機能
    search_query = request.GET.get('q', '')
    if search_query:
        connections = connections.filter(
            Q(corporate_number__icontains=search_query)
        )
    
    # ステータスフィルター
    status_filter = request.GET.get('status', '')
    if status_filter:
        connections = connections.filter(status=status_filter)
    
    # ページネーション
    paginator = Paginator(connections, 20)
    page_number = request.GET.get('page')
    connections = paginator.get_page(page_number)
    
    # 会社情報を取得（法人番号から）
    from apps.company.models import Company
    companies = {}
    for conn in connections:
        if conn.corporate_number not in companies:
            try:
                company = Company.objects.get(corporate_number=conn.corporate_number)
                companies[conn.corporate_number] = company
            except Company.DoesNotExist:
                companies[conn.corporate_number] = None
    
    return render(request, 'connect/client_list.html', {
        'connections': connections,
        'companies': companies,
        'search_query': search_query,
        'status_filter': status_filter,
    })


@login_required
@permission_required('connect.change_connectclient', raise_exception=True)
@require_POST
def connect_client_approve(request, pk):
    """クライアント接続を承認"""
    connection = get_object_or_404(ConnectClient, pk=pk)
    
    # 権限チェック：管理者または申請対象者本人のみ承認可能
    if not (request.user.is_staff or connection.email == request.user.email):
        messages.error(request, 'この申請を承認する権限がありません。')
        return redirect('connect:client_list')
    
    if connection.status == Constants.CONNECT_STATUS.PENDING:
        connection.approve(request.user)
        
        # クライアント担当者の変更履歴に記録するため、担当者IDを取得
        from apps.client.models import ClientUser
        try:
            client_user = ClientUser.objects.get(email=connection.email)
            # クライアント担当者の変更履歴として記録
            AppLog.objects.create(
                user=request.user,
                model_name='ConnectClient',
                object_id=str(client_user.pk),
                object_repr=f'{client_user} - 接続承認',
                action='update'
            )
        except ClientUser.DoesNotExist:
            # クライアント担当者が見つからない場合は通常のログ記録
            log_model_action(request.user, 'update', connection)
        


        messages.success(request, 'クライアント接続申請を承認しました。')
    else:
        messages.info(request, 'この申請は既に承認済みです。')

    next_url = request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    
    return redirect('connect:client_list')


@login_required
@permission_required('connect.change_connectclient', raise_exception=True)
@require_POST
def connect_client_unapprove(request, pk):
    """クライアント接続を未承認に戻す"""
    connection = get_object_or_404(ConnectClient, pk=pk)
    
    # 権限チェック：管理者または申請対象者本人のみ未承認に戻すことが可能
    if not (request.user.is_staff or connection.email == request.user.email):
        messages.error(request, 'この申請を変更する権限がありません。')
        return redirect('connect:client_list')
    
    if connection.status == Constants.CONNECT_STATUS.APPROVED:
        connection.unapprove()
        
        # クライアント担当者の変更履歴に記録するため、担当者IDを取得
        from apps.client.models import ClientUser
        try:
            client_user = ClientUser.objects.get(email=connection.email)
            # クライアント担当者の変更履歴として記録
            AppLog.objects.create(
                user=request.user,
                model_name='ConnectClient',
                object_id=str(client_user.pk),
                object_repr=f'{client_user} - 接続承認取り消し',
                action='update'
            )
        except ClientUser.DoesNotExist:
            # クライアント担当者が見つからない場合は通常のログ記録
            log_model_action(request.user, 'update', connection)
        
        messages.success(request, 'クライアント接続申請を未承認に戻しました。')
    else:
        messages.info(request, 'この申請は未承認です。')

    next_url = request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    
    return redirect('connect:client_list')


@login_required
def connect_index(request):
    """接続管理のトップページ"""
    # ログインユーザー宛の申請数を取得
    staff_pending_count = ConnectStaff.objects.filter(email=request.user.email, status='pending').count()
    staff_approved_count = ConnectStaff.objects.filter(email=request.user.email, status='approved').count()

    client_pending_count = ConnectClient.objects.filter(email=request.user.email, status='pending').count()
    client_approved_count = ConnectClient.objects.filter(email=request.user.email, status='approved').count()

    # --------------------------------------------------------------------------
    # 接続申請一覧
    # --------------------------------------------------------------------------
    # Get filter values
    type_filter = request.GET.get('type', '')
    status_filter = request.GET.get('status', '')

    # Base querysets
    if request.user.is_staff:
        staff_connections = ConnectStaff.objects.all()
        client_connections = ConnectClient.objects.all()
    else:
        staff_connections = ConnectStaff.objects.filter(email=request.user.email)
        client_connections = ConnectClient.objects.filter(email=request.user.email)

    # Apply status filter
    if status_filter:
        staff_connections = staff_connections.filter(status=status_filter)
        client_connections = client_connections.filter(status=status_filter)

    # Prepare connection list based on type filter
    all_connections = []
    if type_filter == 'staff' or not type_filter:
        for conn in staff_connections:
            conn.type = 'staff'
            conn.domain_value = 1
            all_connections.append(conn)

    if type_filter == 'client' or not type_filter:
        for conn in client_connections:
            conn.type = 'client'
            conn.domain_value = 10
            all_connections.append(conn)

    # 作成日時で降順にソート
    all_connections.sort(key=lambda x: x.created_at, reverse=True)

    # 会社情報を取得（法人番号から）
    from apps.company.models import Company
    companies = {}
    for conn in all_connections:
        if conn.corporate_number not in companies:
            try:
                company = Company.objects.get(corporate_number=conn.corporate_number)
                companies[conn.corporate_number] = company
            except Company.DoesNotExist:
                companies[conn.corporate_number] = None
    
    return render(request, 'connect/index.html', {
        'staff_pending_count': staff_pending_count,
        'staff_approved_count': staff_approved_count,
        'client_pending_count': client_pending_count,
        'client_approved_count': client_approved_count,
        'all_connections': all_connections,
        'companies': companies,
        'type_filter': type_filter,
        'status_filter': status_filter,
    })