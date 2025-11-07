from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Prefetch, Count
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.http import require_POST
import re
from datetime import datetime, date
from django.core.files.base import ContentFile
from datetime import date
from django.forms.models import model_to_dict
from .models import ClientContract, StaffContract, ClientContractPrint, StaffContractPrint, ClientContractHaken, ClientContractTtp, ClientContractHakenExempt, StaffContractTeishokubi, StaffContractTeishokubiDetail
from .forms import ClientContractForm, StaffContractForm, ClientContractHakenForm, ClientContractTtpForm, ClientContractHakenExemptForm, StaffContractTeishokubiDetailForm
from apps.common.constants import Constants
from django.conf import settings
from django.utils import timezone
import os
from apps.system.logs.models import AppLog
# # from apps.common.utils import fill_pdf_from_template
from apps.client.models import Client, ClientUser
from apps.staff.models import Staff
from apps.master.models import ContractPattern, StaffAgreement, DefaultValue
from apps.connect.models import ConnectStaff, ConnectStaffAgree, ConnectClient, MynumberRequest, ProfileRequest, BankRequest, ContactRequest, ConnectInternationalRequest, DisabilityRequest
from apps.staff.models import Staff
from apps.client.models import Client
from apps.company.models import Company, CompanyDepartment
from apps.system.settings.models import Dropdowns
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
from .utils import generate_contract_pdf_content, generate_quotation_pdf, generate_client_contract_number, generate_staff_contract_number, generate_teishokubi_notification_pdf, generate_haken_notification_pdf, generate_haken_motokanri_pdf
from .resources import ClientContractResource, StaffContractResource
from .models import ContractAssignment
from django.urls import reverse

@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_pdf(request, pk):
    """クライアント契約書のPDFを生成して返す"""
    contract = get_object_or_404(ClientContract, pk=pk)

    # 承認済みの場合は発行済みに更新
    if contract.contract_status == Constants.CONTRACT_STATUS.APPROVED:
        contract.contract_status = Constants.CONTRACT_STATUS.ISSUED
        contract.issued_at = timezone.now()
        contract.issued_by = request.user
        contract.save()
        messages.success(request, f'契約「{contract.contract_name}」の契約書を発行しました。')

    pdf_content, pdf_filename, document_title = generate_contract_pdf_content(contract)

    if pdf_content:
        new_print = ClientContractPrint(
            client_contract=contract,
            printed_by=request.user,
            print_type=ClientContractPrint.PrintType.CONTRACT,
            document_title=document_title,
            contract_number=contract.contract_number
        )
        new_print.pdf_file.save(pdf_filename, ContentFile(pdf_content), save=True)

        AppLog.objects.create(
            user=request.user,
            action='print',
            model_name='ClientContract',
            object_id=str(contract.pk),
            object_repr=f'契約書PDF出力: {contract.contract_name}'
        )

        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{pdf_filename}"'
        return response
    else:
        messages.error(request, "PDFの生成に失敗しました。")
        return redirect('contract:client_contract_detail', pk=pk)

@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_export(request):
    """クライアント契約データのエクスポート（CSV/Excel）"""
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    client_filter = request.GET.get('client', '')
    contract_type_filter = request.GET.get('contract_type', '')
    date_filter = request.GET.get('date_filter', '')
    format_type = request.GET.get('format', 'csv')

    contracts = ClientContract.objects.select_related('client', 'haken_info__ttp_info').all()

    if client_filter:
        contracts = contracts.filter(client_id=client_filter)
    if search_query:
        contracts = contracts.filter(
            Q(contract_name__icontains=search_query) |
            Q(client__name__icontains=search_query) |
            Q(contract_number__icontains=search_query)
        )
    if status_filter:
        contracts = contracts.filter(contract_status=status_filter)
    if contract_type_filter:
        contracts = contracts.filter(client_contract_type_code=contract_type_filter)
    
    # 日付フィルタを適用
    if date_filter:
        today = date.today()
        if date_filter == 'today':
            # 本日が契約期間に含まれているもの
            contracts = contracts.filter(
                start_date__lte=today
            ).filter(
                Q(end_date__gte=today) | Q(end_date__isnull=True)
            )
        elif date_filter == 'future':
            # 本日以降に契約終了があるもの（無期限契約も含む）
            contracts = contracts.filter(
                Q(end_date__gte=today) | Q(end_date__isnull=True)
            )

    contracts = contracts.order_by('-start_date', 'client__name')

    resource = ClientContractResource()
    dataset = resource.export(contracts)

    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    if format_type == 'excel':
        response = HttpResponse(
            dataset.xlsx,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="client_contracts_{timestamp}.xlsx"'
    else:
        csv_data = '\ufeff' + dataset.csv
        response = HttpResponse(csv_data, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="client_contracts_{timestamp}.csv"'

    return response

@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_dispatch_ledger_pdf(request, pk):
    """クライアント契約の派遣元管理台帳PDFを生成して返す"""
    contract = get_object_or_404(ClientContract, pk=pk)

    if contract.client_contract_type_code != Constants.CLIENT_CONTRACT_TYPE.DISPATCH:
        messages.error(request, 'この契約の派遣元管理台帳は発行できません。')
        return redirect('contract:client_contract_detail', pk=pk)

    issued_at = timezone.now()
    pdf_content, pdf_filename, document_title = generate_haken_motokanri_pdf(
        contract, request.user, issued_at
    )

    if pdf_content:
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{pdf_filename}"'
        return response
    else:
        messages.error(request, "派遣元管理台帳のPDFの生成に失敗しました。")
        return redirect('contract:client_contract_detail', pk=pk)

@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_draft_pdf(request, pk):
    """クライアント契約書のドラフトPDFを生成して返す"""
    contract = get_object_or_404(ClientContract, pk=pk)
    pdf_content, pdf_filename, document_title = generate_contract_pdf_content(contract)

    if pdf_content:
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{pdf_filename}"'
        return response
    else:
        messages.error(request, "PDFの生成に失敗しました。")
        return redirect('contract:client_contract_detail', pk=pk)

@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_draft_quotation(request, pk):
    """クライアント契約の見積書のドラフトPDFを生成して返す"""
    contract = get_object_or_404(ClientContract, pk=pk)

    issued_at = timezone.now()
    pdf_content, pdf_filename, document_title = generate_quotation_pdf(
        contract, request.user, issued_at, watermark_text="DRAFT"
    )

    if pdf_content:
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{pdf_filename}"'
        return response
    else:
        messages.error(request, "見積書のPDFの生成に失敗しました。")
        return redirect('contract:client_contract_detail', pk=pk)

@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_draft_haken_notification(request, pk):
    """クライアント契約の派遣先通知書のドラフトPDFを生成して返す"""
    contract = get_object_or_404(ClientContract, pk=pk)

    if contract.client_contract_type_code != Constants.CLIENT_CONTRACT_TYPE.DISPATCH:
        messages.error(request, 'この契約の派遣先通知書は発行できません。')
        return redirect('contract:client_contract_detail', pk=pk)

    issued_at = timezone.now()
    pdf_content, pdf_filename, document_title = generate_haken_notification_pdf(
        contract, request.user, issued_at, watermark_text="DRAFT"
    )

    if pdf_content:
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{pdf_filename}"'
        return response
    else:
        messages.error(request, "派遣通知書のPDFの生成に失敗しました。")
        return redirect('contract:client_contract_detail', pk=pk)

@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_contract_draft_dispatch_ledger(request, pk):
    """クライアント契約の派遣先管理台帳のドラフトPDFを生成して返す"""
    contract = get_object_or_404(ClientContract, pk=pk)

    if contract.client_contract_type_code != Constants.CLIENT_CONTRACT_TYPE.DISPATCH:
        messages.error(request, 'この契約の派遣先管理台帳は発行できません。')
        return redirect('contract:client_contract_detail', pk=pk)

    issued_at = timezone.now()
    pdf_content, pdf_filename, document_title = generate_haken_sakikanri_pdf(
        contract, request.user, issued_at, watermark_text="DRAFT"
    )

    if pdf_content:
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{pdf_filename}"'
        return response
    else:
        messages.error(request, "派遣先管理台帳のPDFの生成に失敗しました。")
        return redirect('contract:client_contract_detail', pk=pk)

@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def view_client_contract_pdf(request, pk):
    """
    クライアント契約印刷履歴のPDFをブラウザで表示する
    """
    print_history = get_object_or_404(ClientContractPrint, pk=pk)
    
    if not print_history.pdf_file:
        raise Http404("PDFファイルが見つかりません")
    
    try:
        response = HttpResponse(print_history.pdf_file.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{print_history.pdf_file.name}"'
        return response
    except Exception as e:
        raise Http404(f"PDFファイルの読み込みに失敗しました: {str(e)}")

@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def download_client_contract_pdf(request, pk):
    """Downloads a previously generated client contract PDF."""
    print_history = get_object_or_404(ClientContractPrint, pk=pk)

    if not print_history.pdf_file:
        raise Http404("PDFファイルが見つかりません")
    
    try:
        response = HttpResponse(print_history.pdf_file.read(), content_type='application/pdf')
        filename = os.path.basename(print_history.pdf_file.name)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        raise Http404(f"PDFファイルの読み込みに失敗しました: {str(e)}")
        
@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def assignment_employment_conditions_pdf(request, assignment_pk):
    """
    就業条件明示書PDF出力
    POSTリクエスト: 状況カードのスイッチから呼び出し（発行履歴に保存してリダイレクト）
    GETリクエスト: 印刷メニューから呼び出し（PDFを直接表示）
    """
    from .models import ContractAssignmentHakenPrint
    from django.core.files.base import ContentFile
    
    assignment = get_object_or_404(
        ContractAssignment.objects.select_related(
            'client_contract__client',
            'staff_contract__staff',
            'client_contract__haken_info__haken_office',
            'client_contract__haken_info__commander',
            'client_contract__haken_info__complaint_officer_client'
        ),
        pk=assignment_pk
    )
    
    # 派遣契約かどうかチェック
    if assignment.client_contract.client_contract_type_code != Constants.CLIENT_CONTRACT_TYPE.DISPATCH:
        messages.error(request, 'この契約は派遣契約ではないため、就業条件明示書を発行できません。')
        return redirect('contract:contract_assignment_detail', assignment_pk=assignment_pk)
    
    # スタッフ契約の状態チェック（作成中または申請の場合のみ）
    if assignment.staff_contract.contract_status not in [Constants.CONTRACT_STATUS.DRAFT, Constants.CONTRACT_STATUS.PENDING]:
        messages.error(request, 'スタッフ契約が作成中または申請状態の場合のみ就業条件明示書を発行できます。')
        return redirect('contract:contract_assignment_detail', assignment_pk=assignment_pk)
    
    try:
        # PDF生成
        from .utils import generate_employment_conditions_pdf
        pdf_content = generate_employment_conditions_pdf(
            assignment=assignment,
            user=request.user,
            issued_at=timezone.now(),
            watermark_text="DRAFT"
        )
        
        # ファイル名を生成
        filename = f"employment_conditions_draft_{assignment.pk}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        
        # ログ記録（ドラフト版でも操作ログは残す）
        AppLog.objects.create(
            user=request.user,
            model_name='ContractAssignment',
            object_id=str(assignment.pk),
            action='print',
            object_repr=f'就業条件明示書（ドラフト）を出力しました'
        )
        
        # POSTリクエストの場合はメッセージを表示してリダイレクト
        if request.method == 'POST':
            messages.success(request, '就業条件明示書（ドラフト）を出力しました。')
            return redirect('contract:contract_assignment_detail', assignment_pk=assignment_pk)
        
        # GETリクエストの場合はPDFを直接表示
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response
        
    except Exception as e:
        messages.error(request, f'就業条件明示書の生成中にエラーが発生しました: {str(e)}')
        return redirect('contract:contract_assignment_detail', assignment_pk=assignment_pk)

@login_required
@permission_required('contract.change_clientcontract', raise_exception=True)
def issue_quotation(request, pk):
    """クライアント契約の見積書を発行する"""
    contract = get_object_or_404(ClientContract, pk=pk)

    if int(contract.contract_status) < int(Constants.CONTRACT_STATUS.APPROVED):
        messages.error(request, 'この契約の見積書は発行できません。')
        return redirect('contract:client_contract_detail', pk=pk)

    # NOTE: allow re-issuing quotations even if a previous quotation exists.
    # This lets users unapprove -> reapprove -> reissue a fresh quotation while
    # preserving past quotation history.

    issued_at = timezone.now()
    pdf_content, pdf_filename, document_title = generate_quotation_pdf(contract, request.user, issued_at)

    if pdf_content:
        # 履歴として新しい ClientContractPrint を作成
        new_print = ClientContractPrint(
            client_contract=contract,
            printed_by=request.user,
            printed_at=issued_at,
            print_type=ClientContractPrint.PrintType.QUOTATION,
            document_title=document_title,
            contract_number=contract.contract_number
        )
        new_print.pdf_file.save(pdf_filename, ContentFile(pdf_content), save=True)

        # 契約側の見積発行日時/発行者を更新（UI 判定はこれを参照する）
        contract.quotation_issued_at = issued_at
        contract.quotation_issued_by = request.user
        contract.save()

        AppLog.objects.create(
            user=request.user,
            action='quotation_issue',
            model_name='ClientContract',
            object_id=str(contract.pk),
            object_repr=f'見積書PDF出力: {contract.contract_name}'
        )
        messages.success(request, f'契約「{contract.contract_name}」の見積書を発行しました。')
    else:
        messages.error(request, "見積書のPDFの生成に失敗しました。")

    return redirect('contract:client_contract_detail', pk=pk)

@login_required
@permission_required('contract.change_clientcontract', raise_exception=True)
def issue_dispatch_ledger(request, pk):
    """クライアント契約の派遣先管理台帳を発行する"""
    contract = get_object_or_404(ClientContract, pk=pk)
    
    # 派遣契約でない場合はエラー
    if contract.client_contract_type_code != Constants.CLIENT_CONTRACT_TYPE.DISPATCH:
        messages.error(request, '派遣契約以外では派遣先管理台帳を発行できません。')
        return redirect('contract:client_contract_detail', pk=pk)
    
    # 承認済み以降でない場合はエラー
    if not contract.is_approved_or_later:
        messages.error(request, '承認済み以降の契約でのみ派遣先管理台帳を発行できます。')
        return redirect('contract:client_contract_detail', pk=pk)

    issued_at = timezone.now()
    pdf_content, pdf_filename, document_title = generate_haken_sakikanri_pdf(contract, request.user, issued_at)

    if pdf_content:
        new_print = ClientContractPrint.objects.create(
            client_contract=contract,
            printed_by=request.user,
            printed_at=issued_at,
            print_type=ClientContractPrint.PrintType.DISPATCH_LEDGER,
            document_title=document_title,
            contract_number=contract.contract_number
        )
        new_print.pdf_file.save(pdf_filename, ContentFile(pdf_content))

        # 契約側の派遣先管理台帳発行日時/発行者を更新（UI 判定はこれを参照する）
        contract.dispatch_ledger_issued_at = issued_at
        contract.dispatch_ledger_issued_by = request.user
        contract.save()

        AppLog.objects.create(
            user=request.user,
            action='dispatch_ledger_issue',
            model_name='ClientContract',
            object_id=str(contract.pk),
            object_repr=f'派遣先管理台帳PDF出力: {contract.contract_name}'
        )
        messages.success(request, f'契約「{contract.contract_name}」の派遣先管理台帳を発行しました。')
    else:
        messages.error(request, "派遣先管理台帳のPDFの生成に失敗しました。")

    return redirect('contract:client_contract_detail', pk=pk)

@login_required
@permission_required('contract.change_clientcontract', raise_exception=True)
def issue_teishokubi_notification(request, pk):
    """クライアント契約の抵触日通知書を発行する"""
    contract = get_object_or_404(ClientContract, pk=pk)

    if int(contract.contract_status) < int(Constants.CONTRACT_STATUS.APPROVED) or contract.client_contract_type_code != Constants.CLIENT_CONTRACT_TYPE.DISPATCH:
        messages.error(request, 'この契約の抵触日通知書は共有できません。')
        return redirect('contract:client_contract_detail', pk=pk)

    # 派遣情報および派遣先事業所の抵触日の存在チェック
    haken_info = getattr(contract, 'haken_info', None)
    if not haken_info or not haken_info.haken_office or not haken_info.haken_office.haken_jigyosho_teishokubi:
        messages.error(request, '派遣事業所の抵触日が設定されていません。')
        return redirect('contract:client_contract_detail', pk=pk)

    issued_at = timezone.now()
    pdf_content, pdf_filename, document_title = generate_teishokubi_notification_pdf(contract, request.user, issued_at)

    if pdf_content:
        new_print = ClientContractPrint(
            client_contract=contract,
            printed_by=request.user,
            printed_at=issued_at,
            print_type=ClientContractPrint.PrintType.TEISHOKUBI_NOTIFICATION,
            document_title=document_title,
            contract_number=contract.contract_number
        )
        new_print.pdf_file.save(pdf_filename, ContentFile(pdf_content), save=True)

        # 抵触日通知書の共有日時/共有者を契約に記録
        contract.teishokubi_notification_issued_at = issued_at
        contract.teishokubi_notification_issued_by = request.user
        contract.save()

        AppLog.objects.create(
            user=request.user,
            action='teishokubi_notification_issue',
            model_name='ClientContract',
            object_id=str(contract.pk),
            object_repr=f'抵触日通知書PDF出力: {contract.contract_name}'
        )
        messages.success(request, f'契約「{contract.contract_name}」の抵触日通知書を共有しました。')
    else:
        messages.error(request, "抵触日通知書のPDFの生成に失敗しました。")

    return redirect('contract:client_contract_detail', pk=pk)

@login_required
@permission_required('contract.view_clientcontract', raise_exception=True)
def client_teishokubi_notification_pdf(request, pk):
    """クライアント契約の抵触日通知書のPDFを生成して返す"""
    contract = get_object_or_404(ClientContract, pk=pk)

    if contract.client_contract_type_code != Constants.CLIENT_CONTRACT_TYPE.DISPATCH:
        messages.error(request, 'この契約の抵触日通知書は発行できません。')
        return redirect('contract:client_contract_detail', pk=pk)

    # 派遣情報および派遣先事業所の抵触日の存在チェック
    haken_info = getattr(contract, 'haken_info', None)
    if not haken_info or not haken_info.haken_office or not haken_info.haken_office.haken_jigyosho_teishokubi:
        messages.error(request, '派遣事業所の抵触日が設定されていません。')
        return redirect('contract:client_contract_detail', pk=pk)

    issued_at = timezone.now()
    pdf_content, pdf_filename, document_title = generate_teishokubi_notification_pdf(
        contract, request.user, issued_at
    )

    if pdf_content:
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{pdf_filename}"'
        return response
    else:
        messages.error(request, "抵触日通知書のPDFの生成に失敗しました。")
        return redirect('contract:client_contract_detail', pk=pk)