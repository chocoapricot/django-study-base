import os
import io
from django.conf import settings
from django.utils import timezone
from .models import ClientContract, StaffContract, ClientContractPrint, StaffContractPrint
from apps.common.pdf_utils import generate_contract_pdf
from apps.system.logs.models import AppLog

def get_contract_pdf_title(contract):
    """
    契約書の種類に応じてPDFのタイトルを決定する。
    """
    if isinstance(contract, ClientContract):
        if contract.contract_pattern and contract.contract_pattern.contract_type_code == '20':
            return "労働者派遣個別契約書"
        else:
            return "業務委託契約書"
    elif isinstance(contract, StaffContract):
        return "雇用契約書"
    return "契約書"

def generate_and_save_contract_pdf(contract, user):
    """契約書PDFを生成し、保存する共通関数"""
    pdf_title = get_contract_pdf_title(contract)

    if isinstance(contract, ClientContract):
        contract_type = 'client'
        intro_text = f"{contract.client.name} 様との間で、以下の通り業務委託契約を締結します。"
        start_date_str = contract.start_date.strftime('%Y年%m月%d日')
        end_date_str = contract.end_date.strftime('%Y年%m月%d日') if contract.end_date else "無期限"
        contract_period = f"{start_date_str}　～　{end_date_str}"
        items = [
            {"title": "契約名", "text": str(contract.contract_name)},
            {"title": "クライアント名", "text": str(contract.client.name)},
            {"title": "契約番号", "text": str(contract.contract_number)},
            {"title": "契約期間", "text": contract_period},
            {"title": "契約金額", "text": f"{contract.contract_amount:,} 円" if contract.contract_amount else "N/A"},
            {"title": "支払サイト", "text": str(contract.payment_site.name if contract.payment_site else "N/A")},
            {"title": "契約内容", "text": str(contract.description)},
            {"title": "備考", "text": str(contract.notes)},
        ]
        model_name = 'ClientContract'
    elif isinstance(contract, StaffContract):
        contract_type = 'staff'
        intro_text = f"{contract.staff.name_last} {contract.staff.name_first} 様との間で、以下の通り雇用契約を締結します。"
        start_date_str = contract.start_date.strftime('%Y年%m月%d日')
        end_date_str = contract.end_date.strftime('%Y年%m月%d日') if contract.end_date else "無期限"
        contract_period = f"{start_date_str}　～　{end_date_str}"
        items = [
            {"title": "契約名", "text": str(contract.contract_name)},
            {"title": "スタッフ名", "text": f"{contract.staff.name_last} {contract.staff.name_first}"},
            {"title": "契約番号", "text": str(contract.contract_number or "")},
            {"title": "契約期間", "text": contract_period},
            {"title": "契約金額", "text": f"{contract.contract_amount:,} 円" if contract.contract_amount else "N/A"},
            {"title": "契約内容", "text": str(contract.description or "")},
            {"title": "備考", "text": str(contract.notes or "")},
        ]
        model_name = 'StaffContract'
    else:
        return None, None

    if contract.contract_pattern:
        terms = contract.contract_pattern.terms.all().order_by('display_order')
        if terms:
            notes_index = -1
            for i, item in enumerate(items):
                if item["title"] == "備考":
                    notes_index = i
                    break
            term_items = []
            for term in terms:
                term_items.append({"title": str(term.contract_clause), "text": str(term.contract_terms)})
            if notes_index != -1:
                items[notes_index:notes_index] = term_items
            else:
                items.extend(term_items)

    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    pdf_filename = f"{contract_type}_contract_{contract.pk}_{timestamp}.pdf"
    
    # 透かしのテキストを決定
    watermark_text = None
    if contract.contract_status in [contract.ContractStatus.DRAFT, contract.ContractStatus.PENDING]:
        watermark_text = "DRAFT"

    buffer = io.BytesIO()
    generate_contract_pdf(buffer, pdf_title, intro_text, items, watermark_text=watermark_text)
    pdf_content = buffer.getvalue()
    buffer.close()

    contract_dir = os.path.join(settings.MEDIA_ROOT, 'contracts', contract_type, str(contract.pk))
    os.makedirs(contract_dir, exist_ok=True)
    file_path_on_disk = os.path.join(contract_dir, pdf_filename)
    with open(file_path_on_disk, 'wb') as f:
        f.write(pdf_content)
    
    db_file_path = os.path.join('contracts', contract_type, str(contract.pk), pdf_filename)
    
    if contract_type == 'client':
        ClientContractPrint.objects.create(
            client_contract=contract,
            printed_by=user,
            pdf_file_path=db_file_path
        )
    else:
        StaffContractPrint.objects.create(
            staff_contract=contract,
            printed_by=user,
            pdf_file_path=db_file_path
        )

    AppLog.objects.create(
        user=user,
        action='print',
        model_name=model_name,
        object_id=str(contract.pk),
        object_repr=f'契約書PDF出力: {contract.contract_name}'
    )

    return pdf_content, pdf_filename
