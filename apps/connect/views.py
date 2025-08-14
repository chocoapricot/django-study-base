from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q
from apps.system.logs.utils import log_model_action
from .models import ConnectStaff, ConnectClient


@login_required
def connect_staff_list(request):
    """スタッフ接続一覧（ログインユーザー宛の申請）"""
    # ログインユーザーのメールアドレス宛の申請を取得
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
    connection = get_object_or_404(ConnectStaff, pk=pk, email=request.user.email)
    
    if connection.status == 'pending':
        connection.approve(request.user)
        log_model_action(request.user, 'update', connection)
        
        # 承認時に権限を付与
        from .utils import grant_permissions_on_connection_request
        grant_permissions_on_connection_request(connection.email)
        
        messages.success(request, '接続申請を承認しました。')
    else:
        messages.info(request, 'この申請は既に承認済みです。')
    
    return redirect('connect:staff_list')


@login_required
@require_POST
def connect_staff_unapprove(request, pk):
    """スタッフ接続を未承認に戻す"""
    connection = get_object_or_404(ConnectStaff, pk=pk, email=request.user.email)
    
    if connection.status == 'approved':
        connection.unapprove()
        log_model_action(request.user, 'update', connection)
        messages.success(request, '接続申請を未承認に戻しました。')
    else:
        messages.info(request, 'この申請は未承認です。')
    
    return redirect('connect:staff_list')


@login_required
@permission_required('staff.view_staff', raise_exception=True)
@require_POST
def create_staff_connection(request):
    """スタッフ詳細画面から接続申請を作成"""
    staff_id = request.POST.get('staff_id')
    
    if not staff_id:
        messages.error(request, 'スタッフIDが指定されていません。')
        return redirect('staff:staff_list')
    
    try:
        from apps.staff.models import Staff
        staff = Staff.objects.get(pk=staff_id)
        
        if not staff.email:
            messages.error(request, 'このスタッフにはメールアドレスが設定されていません。')
            return redirect('staff:staff_detail', pk=staff_id)
        
        # 会社の法人番号を取得
        from apps.company.models import Company
        company = Company.objects.first()
        if not company or not company.corporate_number:
            messages.error(request, '会社の法人番号が設定されていません。')
            return redirect('staff:staff_detail', pk=staff_id)
        
        # 既存の申請があるかチェック
        existing_connection = ConnectStaff.objects.filter(
            corporate_number=company.corporate_number,
            email=staff.email
        ).first()
        
        if existing_connection:
            messages.warning(request, 'この組み合わせの接続申請は既に存在します。')
            return redirect('staff:staff_detail', pk=staff_id)
        
        # 新しい接続申請を作成
        connection = ConnectStaff.objects.create(
            corporate_number=company.corporate_number,
            email=staff.email,
            created_by=request.user,
            updated_by=request.user
        )
        
        log_model_action(request.user, 'create', connection)
        
        # 既存ユーザーがいる場合は権限を付与
        from .utils import grant_permissions_on_connection_request
        grant_permissions_on_connection_request(staff.email)
        
        messages.success(request, f'スタッフ「{staff.name}」への接続申請を送信しました。')
        
        return redirect('staff:staff_detail', pk=staff_id)
        
    except Staff.DoesNotExist:
        messages.error(request, 'スタッフが見つかりません。')
        return redirect('staff:staff_list')
    except Exception as e:
        messages.error(request, f'エラーが発生しました: {str(e)}')
        return redirect('staff:staff_list')


@login_required
def connect_index(request):
    """接続管理のトップページ"""
    # ログインユーザー宛の申請数を取得
    pending_count = ConnectStaff.objects.filter(email=request.user.email, status='pending').count()
    approved_count = ConnectStaff.objects.filter(email=request.user.email, status='approved').count()
    
    return render(request, 'connect/index.html', {
        'pending_count': pending_count,
        'approved_count': approved_count,
    })