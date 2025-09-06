from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from .models import ClientContract, StaffContract
from .forms import ClientContractForm, StaffContractForm
from apps.system.logs.models import AppLog
from apps.common.utils import fill_pdf_from_template
from apps.client.models import Client
from apps.staff.models import Staff
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io


# 契約管理トップページ
@login_required
def contract_index(request):
    """契約管理トップページ"""
    # クライアント契約の統計
    client_contract_count = ClientContract.objects.count()
    current_client_contracts = ClientContract.objects.filter(is_active=True).count()
    recent_client_contracts = ClientContract.objects.select_related('client').filter(
        is_active=True
    ).order_by('-created_at')[:5]
    
    # スタッフ契約の統計
    staff_contract_count = StaffContract.objects.count()
    current_staff_contracts = StaffContract.objects.filter(is_active=True).count()
    recent_staff_contracts = StaffContract.objects.select_related('staff').filter(
        is_active=True
    ).order_by('-created_at')[:5]
    
    context = {
        'client_contract_count': client_contract_count,
        'current_client_contracts': current_client_contracts,
        'recent_client_contracts': recent_client_contracts,
        'staff_contract_count': staff_contract_count,
        'current_staff_contracts': current_staff_contracts,
        'recent_staff_contracts': recent_staff_contracts,
    }
    return render(request, 'contract/contract_index.html', context)


# クライアント契約管理
@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_list(request):
    """クライアント契約一覧"""
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    client_filter = request.GET.get('client', '')  # クライアントフィルタを追加
    
    contracts = ClientContract.objects.select_related('client').all()
    
    # クライアントフィルタを適用
    if client_filter:
        contracts = contracts.filter(client_id=client_filter)
    
    # 検索条件を適用
    if search_query:
        contracts = contracts.filter(
            Q(contract_name__icontains=search_query) |
            Q(client__name__icontains=search_query) |
            Q(contract_number__icontains=search_query)
        )
    
    # ステータスフィルタを適用
    if status_filter:
        from django.utils import timezone
        today = timezone.now().date()
        
        if status_filter == 'current':
            contracts = contracts.filter(
                is_active=True,
                start_date__lte=today,
                end_date__gte=today
            )
        elif status_filter == 'expired':
            contracts = contracts.filter(end_date__lt=today)
        elif status_filter == 'future':
            contracts = contracts.filter(start_date__gt=today)
        elif status_filter == 'inactive':
            contracts = contracts.filter(is_active=False)
    
    contracts = contracts.order_by('-start_date', 'client__name')
    
    # ページネーション
    paginator = Paginator(contracts, 20)
    page = request.GET.get('page')
    contracts_page = paginator.get_page(page)
    
    # フィルタ対象のクライアント情報を取得（パンくずリスト用）
    filtered_client = None
    if client_filter:
        from apps.client.models import Client
        try:
            filtered_client = Client.objects.get(pk=client_filter)
        except Client.DoesNotExist:
            pass
    
    context = {
        'contracts': contracts_page,
        'search_query': search_query,
        'status_filter': status_filter,
        'client_filter': client_filter,
        'filtered_client': filtered_client,
    }
    return render(request, 'contract/client_contract_list.html', context)


@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_detail(request, pk):
    """クライアント契約詳細"""
    contract = get_object_or_404(ClientContract, pk=pk)
    
    # クライアントフィルタ情報を取得
    client_filter = request.GET.get('client', '')
    from_client_detail = bool(client_filter)
    
    # 遷移元を判定（リファラーから）
    referer = request.META.get('HTTP_REFERER', '')
    from_client_detail_direct = False
    if client_filter and referer:
        # クライアント詳細画面から直接遷移した場合
        if f'/client/client/detail/{client_filter}/' in referer:
            from_client_detail_direct = True
    
    # AppLogから履歴を取得
    change_logs = AppLog.objects.filter(
        model_name='ClientContract',
        object_id=str(contract.pk),
        action__in=['create', 'update', 'delete']
    ).order_by('-timestamp')[:10]  # 最新10件
    
    context = {
        'contract': contract,
        'change_logs': change_logs,
        'client_filter': client_filter,
        'from_client_detail': from_client_detail,
        'from_client_detail_direct': from_client_detail_direct,
    }
    return render(request, 'contract/client_contract_detail.html', context)


@login_required
@permission_required('contract.add_clientcontract', raise_exception=True)
def client_contract_create(request):
    """クライアント契約作成"""
    # URLパラメータからクライアントIDを取得
    selected_client_id = request.GET.get('selected_client_id')
    
    if request.method == 'POST':
        form = ClientContractForm(request.POST)
        if form.is_valid():
            contract = form.save(commit=False)
            contract.created_by = request.user
            contract.updated_by = request.user
            contract.save()
            messages.success(request, f'クライアント契約「{contract.contract_name}」を作成しました。')
            return redirect('contract:client_contract_detail', pk=contract.pk)
    else:
        # 初期値を設定
        initial_data = {}
        if selected_client_id:
            initial_data['client'] = selected_client_id
        form = ClientContractForm(initial=initial_data)
    
    context = {
        'form': form,
        'title': 'クライアント契約作成',
    }
    return render(request, 'contract/client_contract_form.html', context)


@login_required
@permission_required('contract.change_clientcontract', raise_exception=True)
def client_contract_update(request, pk):
    """クライアント契約更新"""
    contract = get_object_or_404(ClientContract, pk=pk)
    
    if request.method == 'POST':
        form = ClientContractForm(request.POST, instance=contract)
        if form.is_valid():
            contract = form.save(commit=False)
            contract.updated_by = request.user
            contract.save()
            messages.success(request, f'クライアント契約「{contract.contract_name}」を更新しました。')
            return redirect('contract:client_contract_detail', pk=contract.pk)
    else:
        form = ClientContractForm(instance=contract)
    
    context = {
        'form': form,
        'contract': contract,
        'title': 'クライアント契約編集',
    }
    return render(request, 'contract/client_contract_form.html', context)


@login_required
@permission_required('contract.delete_clientcontract', raise_exception=True)
def client_contract_delete(request, pk):
    """クライアント契約削除"""
    contract = get_object_or_404(ClientContract, pk=pk)
    
    if request.method == 'POST':
        contract_name = contract.contract_name
        contract.delete()
        messages.success(request, f'クライアント契約「{contract_name}」を削除しました。')
        return redirect('contract:client_contract_list')
    
    context = {
        'contract': contract,
    }
    return render(request, 'contract/client_contract_delete.html', context)


# スタッフ契約管理
@login_required
@permission_required('contract.view_staffcontract', raise_exception=True)
def staff_contract_list(request):
    """スタッフ契約一覧"""
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    staff_filter = request.GET.get('staff', '')  # スタッフフィルタを追加
    
    contracts = StaffContract.objects.select_related('staff').all()
    
    # スタッフフィルタを適用
    if staff_filter:
        contracts = contracts.filter(staff_id=staff_filter)
    
    # 検索条件を適用
    if search_query:
        contracts = contracts.filter(
            Q(contract_name__icontains=search_query) |
            Q(staff__name_last__icontains=search_query) |
            Q(staff__name_first__icontains=search_query) |
            Q(contract_number__icontains=search_query)
        )
    
    # ステータスフィルタを適用
    if status_filter:
        from django.utils import timezone
        today = timezone.now().date()
        
        if status_filter == 'current':
            contracts = contracts.filter(
                is_active=True,
                start_date__lte=today,
                end_date__gte=today
            )
        elif status_filter == 'expired':
            contracts = contracts.filter(end_date__lt=today)
        elif status_filter == 'future':
            contracts = contracts.filter(start_date__gt=today)
        elif status_filter == 'inactive':
            contracts = contracts.filter(is_active=False)
    
    contracts = contracts.order_by('-start_date', 'staff__name_last', 'staff__name_first')
    
    # ページネーション
    paginator = Paginator(contracts, 20)
    page = request.GET.get('page')
    contracts_page = paginator.get_page(page)
    
    # フィルタ対象のスタッフ情報を取得（パンくずリスト用）
    filtered_staff = None
    if staff_filter:
        from apps.staff.models import Staff
        try:
            filtered_staff = Staff.objects.get(pk=staff_filter)
        except Staff.DoesNotExist:
            pass
    
    context = {
        'contracts': contracts_page,
        'search_query': search_query,
        'status_filter': status_filter,
        'staff_filter': staff_filter,
        'filtered_staff': filtered_staff,
    }
    return render(request, 'contract/staff_contract_list.html', context)


@login_required
@permission_required('contract.view_staffcontract', raise_exception=True)
def staff_contract_detail(request, pk):
    """スタッフ契約詳細"""
    contract = get_object_or_404(StaffContract, pk=pk)
    
    # スタッフフィルタ情報を取得
    staff_filter = request.GET.get('staff', '')
    from_staff_detail = bool(staff_filter)
    
    # 遷移元を判定（リファラーから）
    referer = request.META.get('HTTP_REFERER', '')
    from_staff_detail_direct = False
    if staff_filter and referer:
        # スタッフ詳細画面から直接遷移した場合
        if f'/staff/staff/detail/{staff_filter}/' in referer:
            from_staff_detail_direct = True
    
    # AppLogから履歴を取得
    change_logs = AppLog.objects.filter(
        model_name='StaffContract',
        object_id=str(contract.pk),
        action__in=['create', 'update', 'delete']
    ).order_by('-timestamp')[:10]  # 最新10件
    
    context = {
        'contract': contract,
        'change_logs': change_logs,
        'staff_filter': staff_filter,
        'from_staff_detail': from_staff_detail,
        'from_staff_detail_direct': from_staff_detail_direct,
    }
    return render(request, 'contract/staff_contract_detail.html', context)


@login_required
@permission_required('contract.add_staffcontract', raise_exception=True)
def staff_contract_create(request):
    """スタッフ契約作成"""
    if request.method == 'POST':
        form = StaffContractForm(request.POST)
        if form.is_valid():
            contract = form.save(commit=False)
            contract.created_by = request.user
            contract.updated_by = request.user
            contract.save()
            messages.success(request, f'スタッフ契約「{contract.contract_name}」を作成しました。')
            return redirect('contract:staff_contract_detail', pk=contract.pk)
    else:
        form = StaffContractForm()
    
    context = {
        'form': form,
        'title': 'スタッフ契約作成',
    }
    return render(request, 'contract/staff_contract_form.html', context)


@login_required
@permission_required('contract.change_staffcontract', raise_exception=True)
def staff_contract_update(request, pk):
    """スタッフ契約更新"""
    contract = get_object_or_404(StaffContract, pk=pk)
    
    if request.method == 'POST':
        form = StaffContractForm(request.POST, instance=contract)
        if form.is_valid():
            contract = form.save(commit=False)
            contract.updated_by = request.user
            contract.save()
            messages.success(request, f'スタッフ契約「{contract.contract_name}」を更新しました。')
            return redirect('contract:staff_contract_detail', pk=contract.pk)
    else:
        form = StaffContractForm(instance=contract)
    
    context = {
        'form': form,
        'contract': contract,
        'title': 'スタッフ契約編集',
    }
    return render(request, 'contract/staff_contract_form.html', context)


@login_required
@permission_required('contract.delete_staffcontract', raise_exception=True)
def staff_contract_delete(request, pk):
    """スタッフ契約削除"""
    contract = get_object_or_404(StaffContract, pk=pk)
    
    if request.method == 'POST':
        contract_name = contract.contract_name
        contract.delete()
        messages.success(request, f'スタッフ契約「{contract_name}」を削除しました。')
        return redirect('contract:staff_contract_list')
    
    context = {
        'contract': contract,
    }
    return render(request, 'contract/staff_contract_delete.html', context)


# 選択用ビュー
@login_required
def client_select(request):
    """クライアント選択画面"""
    search_query = request.GET.get('q', '')
    return_url = request.GET.get('return_url', '')
    
    # 基本契約締結日が入っているクライアントのみを対象とする
    clients = Client.objects.filter(basic_contract_date__isnull=False)
    
    if search_query:
        clients = clients.filter(
            Q(name__icontains=search_query) |
            Q(corporate_number__icontains=search_query) |
            Q(address__icontains=search_query)
        )
    
    clients = clients.order_by('name')
    
    # ページネーション
    paginator = Paginator(clients, 20)
    page = request.GET.get('page')
    clients_page = paginator.get_page(page)
    
    context = {
        'clients': clients_page,
        'search_query': search_query,
        'return_url': return_url,
    }
    return render(request, 'contract/client_select.html', context)


@login_required
def staff_select(request):
    """スタッフ選択画面"""
    search_query = request.GET.get('q', '')
    return_url = request.GET.get('return_url', '')
    
    # 社員番号と入社日が入っているスタッフのみを対象とする
    staff_list = Staff.objects.filter(
        employee_no__isnull=False,
        hire_date__isnull=False
    ).exclude(employee_no='')
    
    if search_query:
        staff_list = staff_list.filter(
            Q(name_last__icontains=search_query) |
            Q(name_first__icontains=search_query) |
            Q(employee_no__icontains=search_query)
        )
    
    staff_list = staff_list.order_by('name_last', 'name_first')
    
    # ページネーション
    paginator = Paginator(staff_list, 20)
    page = request.GET.get('page')
    staff_page = paginator.get_page(page)
    
    context = {
        'staff_list': staff_page,
        'search_query': search_query,
        'return_url': return_url,
    }
    return render(request, 'contract/staff_select.html', context)


# 変更履歴ビュー
@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_change_history_list(request, pk):
    """クライアント契約変更履歴一覧"""
    from apps.system.logs.models import AppLog
    from django.core.paginator import Paginator
    
    contract = get_object_or_404(ClientContract, pk=pk)
    
    # 該当契約の変更履歴を取得
    logs = AppLog.objects.filter(
        model_name='ClientContract',
        object_id=str(pk),
        action__in=['create', 'update', 'delete']
    ).order_by('-timestamp')
    
    # ページネーション
    paginator = Paginator(logs, 20)
    page = request.GET.get('page')
    logs_page = paginator.get_page(page)
    
    return render(request, 'contract/contract_change_history_list.html', {
        'logs': logs_page,
        'title': f'クライアント契約変更履歴 - {contract.contract_name}',
        'list_url': 'contract:client_contract_detail',
        'list_url_pk': pk,
        'model_name': 'ClientContract'
    })


@login_required
@permission_required('contract.view_staffcontract', raise_exception=True)
def staff_contract_change_history_list(request, pk):
    """スタッフ契約変更履歴一覧"""
    from apps.system.logs.models import AppLog
    from django.core.paginator import Paginator
    
    contract = get_object_or_404(StaffContract, pk=pk)
    
    # 該当契約の変更履歴を取得
    logs = AppLog.objects.filter(
        model_name='StaffContract',
        object_id=str(pk),
        action__in=['create', 'update', 'delete']
    ).order_by('-timestamp')
    
    # ページネーション
    paginator = Paginator(logs, 20)
    page = request.GET.get('page')
    logs_page = paginator.get_page(page)
    
    return render(request, 'contract/contract_change_history_list.html', {
        'logs': logs_page,
        'title': f'スタッフ契約変更履歴 - {contract.contract_name}',
        'list_url': 'contract:staff_contract_detail',
        'list_url_pk': pk,
        'model_name': 'StaffContract'
    })


@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_pdf(request, pk):
    """クライアント契約書のPDFを生成して返す"""
    contract = get_object_or_404(ClientContract, pk=pk)
    client = contract.client

    # フォームに埋め込むデータを準備
    form_data = {
        'Text7': client.name if client.name else '',
        'Text6': client.name_furigana if client.name_furigana else '',
        'Text10': client.address if client.address else '',
    }

    # PDFフォームにデータを埋め込む（メモリ上にPDFを作成）
    output_pdf = fill_pdf_from_template('templates/pdfs/2025bun_01_input.pdf', form_data)

    # メモリ上のPDFをレスポンスとして返す
    response = HttpResponse(output_pdf.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="client_contract_{pk}.pdf"'
    return response


@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contracts_pdf(request):
    """クライアント契約一覧のPDFを生成して返す"""
    # フォントの登録
    font_path = 'statics/fonts/ipag.ttf'
    pdfmetrics.registerFont(TTFont('IPAG', font_path))

    # レスポンスの準備
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="client_contracts.pdf"'

    # PDFドキュメントの作成
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setFont('IPAG', 10)

    # 契約データの取得
    contracts = ClientContract.objects.select_related('client').all().order_by('client__name', '-start_date')

    # PDFに内容を書き込む
    p.drawString(50, 750, "クライアント契約一覧")
    y = 720
    for contract in contracts:
        if y < 50:
            p.showPage()
            p.setFont('IPAG', 10)
            y = 750

        text = f"契約名: {contract.contract_name}, クライアント: {contract.client.name}, 契約期間: {contract.start_date} ~ {contract.end_date or 'N/A'}, ステータス: {contract.status}"
        p.drawString(50, y, text)
        y -= 20

    p.showPage()
    p.save()

    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)

    return response