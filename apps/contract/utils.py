import os
import io
from django.conf import settings
from django.utils import timezone
from .models import ClientContract, StaffContract, ClientContractPrint, StaffContractPrint
from apps.common.pdf_utils import generate_contract_pdf
from apps.system.logs.models import AppLog

def generate_and_save_contract_pdf(contract, user):
    """契約書PDFを生成し、保存する共通関数"""
    if isinstance(contract, ClientContract):
        contract_type = 'client'
        PrintModel = ClientContractPrint
        pdf_title = "業務委託契約書"
        intro_text = f"{contract.client.name} 様との間で、以下の通り業務委託契約を締結します。"
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
        model_name = 'ClientContract'
    elif isinstance(contract, StaffContract):
        contract_type = 'staff'
        PrintModel = StaffContractPrint
        pdf_title = "雇用契約書"
        intro_text = f"{contract.staff.name_last} {contract.staff.name_first} 様との間で、以下の通り雇用契約を締結します。"
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
    
    buffer = io.BytesIO()
    generate_contract_pdf(buffer, pdf_title, intro_text, items)
    pdf_content = buffer.getvalue()
    buffer.close()

    contract_dir = os.path.join(settings.MEDIA_ROOT, 'contracts', contract_type, str(contract.pk))
    os.makedirs(contract_dir, exist_ok=True)
    file_path_on_disk = os.path.join(contract_dir, pdf_filename)
    with open(file_path_on_disk, 'wb') as f:
        f.write(pdf_content)
    
    db_file_path = os.path.join('contracts', contract_type, str(contract.pk), pdf_filename)
    
    print_instance = PrintModel.objects.create(
        **{f'{contract_type}_contract': contract, 'printed_by': user, 'pdf_file_path': db_file_path}
    )

    AppLog.objects.create(
        user=user,
        action='print',
        model_name=model_name,
        object_id=str(contract.pk),
        object_repr=f'契約書PDF出力: {contract.contract_name}'
    )

    return pdf_content, pdf_filename
