from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse, HttpResponse, Http404
from .models import ClientContract, StaffContract, ClientContractPrint, StaffContractPrint
from .forms import ClientContractForm, StaffContractForm
from django.conf import settings
from django.utils import timezone
import os
from apps.system.logs.models import AppLog
from apps.common.utils import fill_pdf_from_template
from apps.client.models import Client, ClientUser
from apps.staff.models import Staff
from apps.master.models import ContractPattern, StaffAgreement
from apps.connect.models import ConnectStaff, ConnectStaffAgree, ConnectClient
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
from apps.common.pdf_utils import generate_contract_pdf


# 契約管理トップページ
@login_required
def contract_index(request):
    """契約管理トップページ"""
    # クライアント契約の統計
    client_contract_count = ClientContract.objects.count()
    current_client_contracts = ClientContract.objects.count()
    recent_client_contracts = ClientContract.objects.select_related('client').order_by('-created_at')[:5]
    
    # スタッフ契約の統計
    staff_contract_count = StaffContract.objects.count()
    current_staff_contracts = StaffContract.objects.count()
    recent_staff_contracts = StaffContract.objects.select_related('staff').order_by('-created_at')[:5]
    
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
    contract_pattern_filter = request.GET.get('contract_pattern', '')
    
    contracts = ClientContract.objects.select_related('client', 'contract_pattern').all()
    
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
        contracts = contracts.filter(contract_status=status_filter)

    # 契約パターンフィルタを適用
    if contract_pattern_filter:
        contracts = contracts.filter(contract_pattern_id=contract_pattern_filter)

    contracts = contracts.order_by('-start_date', 'client__name')

    # 契約状況のドロップダウンリストを取得
    contract_status_list = [{'value': v, 'name': n} for v, n in ClientContract.ContractStatus.choices]
    contract_pattern_list = ContractPattern.objects.filter(contract_type='client')
    
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
        'contract_status_list': contract_status_list,
        'contract_pattern_filter': contract_pattern_filter,
        'contract_pattern_list': contract_pattern_list,
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
        action__in=['create', 'update', 'delete', 'print']
    ).order_by('-timestamp')[:10]  # 最新10件
    
    # 発行履歴を取得
    print_history = ClientContractPrint.objects.filter(client_contract=contract).order_by('-printed_at')

    context = {
        'contract': contract,
        'print_history': print_history,
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
    
    if contract.contract_status not in [ClientContract.ContractStatus.DRAFT, ClientContract.ContractStatus.PENDING]:
        messages.error(request, 'この契約は編集できません。')
        return redirect('contract:client_contract_detail', pk=pk)

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
    
    if contract.contract_status not in [ClientContract.ContractStatus.DRAFT, ClientContract.ContractStatus.PENDING]:
        messages.error(request, 'この契約は削除できません。')
        return redirect('contract:client_contract_detail', pk=pk)

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
    contract_pattern_filter = request.GET.get('contract_pattern', '')
    
    contracts = StaffContract.objects.select_related('staff', 'contract_pattern').all()
    
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
        contracts = contracts.filter(contract_status=status_filter)

    # 契約パターンフィルタを適用
    if contract_pattern_filter:
        contracts = contracts.filter(contract_pattern_id=contract_pattern_filter)

    contracts = contracts.order_by('-start_date', 'staff__name_last', 'staff__name_first')

    # 契約状況のドロップダウンリストを取得
    contract_status_list = [{'value': v, 'name': n} for v, n in StaffContract.ContractStatus.choices]
    contract_pattern_list = ContractPattern.objects.filter(contract_type='staff')
    
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
        'contract_status_list': contract_status_list,
        'contract_pattern_filter': contract_pattern_filter,
        'contract_pattern_list': contract_pattern_list,
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
        action__in=['create', 'update', 'delete', 'print']
    ).order_by('-timestamp')[:10]  # 最新10件

    # 発行履歴を取得
    print_history = StaffContractPrint.objects.filter(staff_contract=contract).order_by('-printed_at')
    
    context = {
        'contract': contract,
        'print_history': print_history,
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

    # ファイル名
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    pdf_filename = f"client_contract_{pk}_{timestamp}.pdf"

    # レスポンスの準備
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{pdf_filename}"'

    # PDFドキュメントの作成
    buffer = io.BytesIO()

    # PDFのタイトルと前文
    title = "業務委託契約書"
    intro_text = f"{contract.client.name} 様との間で、以下の通り業務委託契約を締結します。"

    # 表示項目の定義
    items = [
        {"title": "契約名", "text": str(contract.contract_name)},
        {"title": "クライアント名", "text": str(contract.client.name)},
        {"title": "契約番号", "text": str(contract.contract_number)},
        {"title": "契約開始日", "text": str(contract.start_date)},
        {"title": "契約終了日", "text": str(contract.end_date or "N/A")},
        {"title": "契約金額", "text": f"{contract.contract_amount} 円" if contract.contract_amount else "N/A"},
        {"title": "支払サイト", "text": str(contract.payment_site.name if contract.payment_site else "N/A")},
        {"title": "契約内容", "text": str(contract.description)},
        {"title": "備考", "text": str(contract.notes)},
    ]

    # 契約パターンに紐づく契約文言を追加
    if contract.contract_pattern:
        terms = contract.contract_pattern.terms.all().order_by('display_order')
        if terms:
            # 「備考」の前に挿入するためのインデックスを取得
            notes_index = -1
            for i, item in enumerate(items):
                if item["title"] == "備考":
                    notes_index = i
                    break
            
            # 契約文言を挿入
            term_items = []
            for term in terms:
                term_items.append({"title": str(term.contract_clause), "text": str(term.contract_terms)})

            if notes_index != -1:
                items[notes_index:notes_index] = term_items
            else:
                # 備考が見つからない場合は末尾に追加
                items.extend(term_items)

    # ステータスが承認済未満（下書き、申請中）の場合は透かしを入れる
    watermark = None
    if contract.contract_status and int(contract.contract_status) < int(ClientContract.ContractStatus.APPROVED):
        watermark = 'DRAFT'

    # 共通関数を呼び出してPDFを生成
    generate_contract_pdf(buffer, title, intro_text, items, watermark_text=watermark)

    # レスポンスにPDFを書き込む
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)

    # 承認済の場合、ステータスを発行済に変更し、発行履歴を記録
    if contract.contract_status == ClientContract.ContractStatus.APPROVED:
        contract.contract_status = ClientContract.ContractStatus.ISSUED
        contract.save()

        # PDFを保存
        contract_dir = os.path.join(settings.MEDIA_ROOT, 'contracts', 'client', str(contract.pk))
        os.makedirs(contract_dir, exist_ok=True)
        file_path_on_disk = os.path.join(contract_dir, pdf_filename)
        with open(file_path_on_disk, 'wb') as f:
            f.write(pdf)

        # DBに保存するパス
        db_file_path = os.path.join('contracts', 'client', str(contract.pk), pdf_filename)

        ClientContractPrint.objects.create(
            client_contract=contract,
            printed_by=request.user,
            pdf_file_path=db_file_path,
        )

    # AppLogに記録
    AppLog.objects.create(
        user=request.user,
        action='print',
        model_name='ClientContract',
        object_id=str(contract.pk),
        object_repr=f'契約書PDF出力: {contract.contract_name}'
    )

    return response


@login_required
@permission_required('contract.change_clientcontract', raise_exception=True)
def client_contract_approve(request, pk):
    """クライアント契約の承認ステータスを更新する"""
    contract = get_object_or_404(ClientContract, pk=pk)
    if request.method == 'POST':
        is_approved = request.POST.get('is_approved')
        if is_approved:
            contract.contract_status = ClientContract.ContractStatus.APPROVED
            contract.approved_at = timezone.now()
            messages.success(request, f'契約「{contract.contract_name}」を承認済にしました。')
        else:
            contract.contract_status = ClientContract.ContractStatus.DRAFT
            contract.approved_at = None
            contract.issued_at = None
            contract.confirmed_at = None
            messages.success(request, f'契約「{contract.contract_name}」を作成中に戻しました。')
        contract.save()
    return redirect('contract:client_contract_detail', pk=contract.pk)


@login_required
@permission_required('contract.change_clientcontract', raise_exception=True)
def client_contract_issue(request, pk):
    """クライアント契約を発行済にする"""
    contract = get_object_or_404(ClientContract, pk=pk)
    if request.method == 'POST' and 'is_issued' in request.POST:
        if contract.contract_status == ClientContract.ContractStatus.APPROVED:
            # client_contract_pdfを呼び出してPDF生成とステータス更新を行う
            # この関数はPDFレスポンスを返すが、ここではリダイレクトするため無視する
            client_contract_pdf(request, pk)
            # メッセージはclient_contract_pdf内では設定されないのでここで設定
            messages.success(request, f'契約「{contract.contract_name}」を発行済にし、PDFを履歴に保存しました。')
    return redirect('contract:client_contract_detail', pk=contract.pk)


@login_required
@permission_required('contract.change_clientcontract', raise_exception=True)
def client_contract_confirm(request, pk):
    """クライアント契約を確認済にする"""
    contract = get_object_or_404(ClientContract, pk=pk)
    if request.method == 'POST' and 'is_confirmed' in request.POST:
        if contract.contract_status == ClientContract.ContractStatus.ISSUED:
            contract.contract_status = ClientContract.ContractStatus.CONTRACTED
            contract.confirmed_at = timezone.now()
            contract.save()
            messages.success(request, f'契約「{contract.contract_name}」を確認済にしました。')
    return redirect('contract:client_contract_detail', pk=contract.pk)


@login_required
@permission_required('contract.change_staffcontract', raise_exception=True)
def staff_contract_approve(request, pk):
    """スタッフ契約の承認ステータスを更新する"""
    contract = get_object_or_404(StaffContract, pk=pk)
    if request.method == 'POST':
        is_approved = request.POST.get('is_approved')
        if is_approved:
            contract.contract_status = StaffContract.ContractStatus.APPROVED
            contract.approved_at = timezone.now()
            messages.success(request, f'契約「{contract.contract_name}」を承認済にしました。')
        else:
            contract.contract_status = StaffContract.ContractStatus.DRAFT
            contract.approved_at = None
            contract.issued_at = None
            contract.confirmed_at = None
            messages.success(request, f'契約「{contract.contract_name}」を作成中に戻しました。')
        contract.save()
    return redirect('contract:staff_contract_detail', pk=contract.pk)


@login_required
@permission_required('contract.change_staffcontract', raise_exception=True)
def staff_contract_issue(request, pk):
    """スタッフ契約を発行済にする"""
    contract = get_object_or_404(StaffContract, pk=pk)
    if request.method == 'POST' and 'is_issued' in request.POST:
        if contract.contract_status == StaffContract.ContractStatus.APPROVED:
            # staff_contract_pdfを呼び出してPDF生成とステータス更新を行う
            # この関数はPDFレスポンスを返すが、ここではリダイレクトするため無視する
            staff_contract_pdf(request, pk)
            # メッセージはstaff_contract_pdf内では設定されないのでここで設定
            messages.success(request, f'契約「{contract.contract_name}」を発行済にし、PDFを履歴に保存しました。')
    return redirect('contract:staff_contract_detail', pk=contract.pk)


@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def download_client_contract_pdf(request, pk):
    """Downloads a previously generated client contract PDF."""
    print_history = get_object_or_404(ClientContractPrint, pk=pk)

    file_path = os.path.join(settings.MEDIA_ROOT, print_history.pdf_file_path)

    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="application/pdf")
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            return response
    raise Http404

@login_required
@permission_required('contract.view_staffcontract', raise_exception=True)
def download_staff_contract_pdf(request, pk):
    """Downloads a previously generated staff contract PDF."""
    print_history = get_object_or_404(StaffContractPrint, pk=pk)

    file_path = os.path.join(settings.MEDIA_ROOT, print_history.pdf_file_path)

    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="application/pdf")
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            return response
    raise Http404


@login_required
def staff_contract_confirm_list(request):
    """スタッフ契約確認一覧"""
    user = request.user

    if request.method == 'POST':
        contract_id = request.POST.get('contract_id')
        action = request.POST.get('action')
        contract = get_object_or_404(StaffContract, pk=contract_id)

        if action == 'confirm':
            # スタッフ同意文言を取得
            staff_agreement = StaffAgreement.objects.filter(
                Q(corporation_number=contract.corporate_number) | Q(corporation_number__isnull=True) | Q(corporation_number=''),
                is_active=True
            ).order_by('-corporation_number', '-created_at').first()

            if staff_agreement:
                ConnectStaffAgree.objects.update_or_create(
                    email=user.email,
                    corporate_number=contract.corporate_number,
                    staff_agreement=staff_agreement,
                    defaults={'is_agreed': True}
                )
                contract.contract_status = StaffContract.ContractStatus.CONFIRMED
                contract.confirmed_at = timezone.now()
                contract.save()
                messages.success(request, f'契約「{contract.contract_name}」を確認しました。')
            else:
                messages.error(request, '確認可能な同意文言が見つかりませんでした。')

        elif action == 'unconfirm':
            contract.contract_status = StaffContract.ContractStatus.ISSUED
            contract.confirmed_at = None
            contract.save()
            messages.success(request, f'契約「{contract.contract_name}」を未確認に戻しました。')

        return redirect('contract:staff_contract_confirm_list')

    try:
        staff = Staff.objects.get(email=user.email)
    except Staff.DoesNotExist:
        staff = None

    if not staff:
        context = {
            'contracts_with_status': [],
            'title': 'スタッフ契約確認',
        }
        return render(request, 'contract/staff_contract_confirm_list.html', context)

    # 接続許可されている法人番号を取得
    approved_corporate_numbers = ConnectStaff.objects.filter(
        email=user.email,
        status='approved'
    ).values_list('corporate_number', flat=True)

    # 契約を取得
    contracts = StaffContract.objects.filter(
        staff=staff,
        corporate_number__in=approved_corporate_numbers,
        contract_status__in=[StaffContract.ContractStatus.ISSUED, StaffContract.ContractStatus.CONFIRMED]
    ).select_related('staff').order_by('-start_date')

    # 同意状況とPDFの情報を追加
    contracts_with_status = []
    for contract in contracts:
        # 同意文言の取得
        staff_agreement = StaffAgreement.objects.filter(
            Q(corporation_number=contract.corporate_number) | Q(corporation_number__isnull=True) | Q(corporation_number=''),
            is_active=True
        ).order_by('-corporation_number', '-created_at').first()

        is_agreed = False
        if staff_agreement:
            is_agreed = ConnectStaffAgree.objects.filter(
                email=user.email,
                corporate_number=contract.corporate_number,
                staff_agreement=staff_agreement,
                is_agreed=True
            ).exists()

        # 最新のPDFを取得
        latest_pdf = StaffContractPrint.objects.filter(staff_contract=contract).order_by('-printed_at').first()

        contracts_with_status.append({
            'contract': contract,
            'is_agreed': is_agreed,
            'latest_pdf': latest_pdf,
        })

    context = {
        'contracts_with_status': contracts_with_status,
        'title': 'スタッフ契約確認',
    }
    return render(request, 'contract/staff_contract_confirm_list.html', context)


@login_required
def client_contract_confirm_list(request):
    """クライアント契約確認一覧"""
    user = request.user

    if request.method == 'POST':
        contract_id = request.POST.get('contract_id')
        action = request.POST.get('action')
        contract = get_object_or_404(ClientContract, pk=contract_id)

        if action == 'confirm':
            contract.contract_status = ClientContract.ContractStatus.CONFIRMED
            contract.confirmed_at = timezone.now()
            contract.save()
            messages.success(request, f'契約「{contract.contract_name}」を確認しました。')

        elif action == 'unconfirm':
            contract.contract_status = ClientContract.ContractStatus.ISSUED
            contract.confirmed_at = None
            contract.save()
            messages.success(request, f'契約「{contract.contract_name}」を未確認に戻しました。')

        return redirect('contract:client_contract_confirm_list')

    try:
        client_user = ClientUser.objects.get(email=user.email)
        client = client_user.client
    except ClientUser.DoesNotExist:
        client = None

    if not client:
        context = {
            'contracts_with_status': [],
            'title': 'クライアント契約確認',
        }
        return render(request, 'contract/client_contract_confirm_list.html', context)

    # 接続許可されている法人番号を取得
    approved_corporate_numbers = ConnectClient.objects.filter(
        email=user.email,
        status='approved'
    ).values_list('corporate_number', flat=True)

    # 契約を取得
    contracts = ClientContract.objects.filter(
        client=client,
        corporate_number__in=approved_corporate_numbers,
        contract_status__in=[ClientContract.ContractStatus.ISSUED, ClientContract.ContractStatus.CONFIRMED]
    ).select_related('client').order_by('-start_date')

    # PDFの情報を追加
    contracts_with_status = []
    for contract in contracts:
        # 最新のPDFを取得
        latest_pdf = ClientContractPrint.objects.filter(client_contract=contract).order_by('-printed_at').first()

        contracts_with_status.append({
            'contract': contract,
            'latest_pdf': latest_pdf,
        })

    context = {
        'contracts_with_status': contracts_with_status,
        'title': 'クライアント契約確認',
    }
    return render(request, 'contract/client_contract_confirm_list.html', context)


@login_required
@permission_required('contract.view_staffcontract', raise_exception=True)
def staff_contract_pdf(request, pk):
    """スタッフ契約書のPDFを生成して返す"""
    contract = get_object_or_404(StaffContract, pk=pk)

    # ファイル名
    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    pdf_filename = f"staff_contract_{pk}_{timestamp}.pdf"

    # レスポンスの準備
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{pdf_filename}"'

    # PDFドキュメントの作成
    buffer = io.BytesIO()

    # PDFのタイトルと前文
    title = "雇用契約書"
    intro_text = f"{contract.staff.name_last} {contract.staff.name_first} 様との間で、以下の通り雇用契約を締結します。"

    # 表示項目の定義
    items = [
        {"title": "契約名", "text": str(contract.contract_name)},
        {"title": "スタッフ名", "text": f"{contract.staff.name_last} {contract.staff.name_first}"},
        {"title": "契約番号", "text": str(contract.contract_number or "")},
        {"title": "契約開始日", "text": str(contract.start_date)},
        {"title": "契約終了日", "text": str(contract.end_date or "N/A")},
        {"title": "契約金額", "text": f"{contract.contract_amount} 円" if contract.contract_amount else "N/A"},
        {"title": "契約内容", "text": str(contract.description or "")},
        {"title": "備考", "text": str(contract.notes or "")},
    ]

    # 契約パターンに紐づく契約文言を追加
    if contract.contract_pattern:
        terms = contract.contract_pattern.terms.all().order_by('display_order')
        if terms:
            # 「備考」の前に挿入するためのインデックスを取得
            notes_index = -1
            for i, item in enumerate(items):
                if item["title"] == "備考":
                    notes_index = i
                    break
            
            # 契約文言を挿入
            term_items = []
            for term in terms:
                term_items.append({"title": str(term.contract_clause), "text": str(term.contract_terms)})

            if notes_index != -1:
                items[notes_index:notes_index] = term_items
            else:
                # 備考が見つからない場合は末尾に追加
                items.extend(term_items)

    # ステータスが承認済未満（下書き、申請中）の場合は透かしを入れる
    watermark = None
    if contract.contract_status and int(contract.contract_status) < int(StaffContract.ContractStatus.APPROVED):
        watermark = 'DRAFT'

    # 共通関数を呼び出してPDFを生成
    generate_contract_pdf(buffer, title, intro_text, items, watermark_text=watermark)

    # レスポンスにPDFを書き込む
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)

    # 承認済の場合、ステータスを発行済に変更し、発行履歴を記録
    if contract.contract_status == StaffContract.ContractStatus.APPROVED:
        contract.contract_status = StaffContract.ContractStatus.ISSUED
        contract.issued_at = timezone.now()
        contract.save()

        # PDFを保存
        contract_dir = os.path.join(settings.MEDIA_ROOT, 'contracts', 'staff', str(contract.pk))
        os.makedirs(contract_dir, exist_ok=True)
        file_path_on_disk = os.path.join(contract_dir, pdf_filename)
        with open(file_path_on_disk, 'wb') as f:
            f.write(pdf)

        # DBに保存するパス
        db_file_path = os.path.join('contracts', 'staff', str(contract.pk), pdf_filename)

        StaffContractPrint.objects.create(
            staff_contract=contract,
            printed_by=request.user,
            pdf_file_path=db_file_path,
        )

    # AppLogに記録
    AppLog.objects.create(
        user=request.user,
        action='print',
        model_name='StaffContract',
        object_id=str(contract.pk),
        object_repr=f'契約書PDF出力: {contract.contract_name}'
    )

    return response