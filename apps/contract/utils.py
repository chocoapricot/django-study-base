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
            return "業務委託個別契約書"
    elif isinstance(contract, StaffContract):
        return "雇用契約書"
    return "契約書"

def generate_contract_pdf_content(contract):
    """契約書PDFのコンテンツを生成して返す"""
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
            {"title": "支払条件", "text": str(contract.payment_site.name if contract.payment_site else "N/A")},
            {"title": "契約内容", "text": str(contract.description)},
            {"title": "備考", "text": str(contract.notes)},
        ]
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
    
    watermark_text = None
    if contract.contract_status in [contract.ContractStatus.DRAFT, contract.ContractStatus.PENDING]:
        watermark_text = "DRAFT"

    buffer = io.BytesIO()
    generate_contract_pdf(buffer, pdf_title, intro_text, items, watermark_text=watermark_text)
    pdf_content = buffer.getvalue()
    buffer.close()

    return pdf_content, pdf_filename, pdf_title


def generate_quotation_pdf(contract, user, issued_at, watermark_text=None):
    """見積書PDFを生成する"""
    pdf_title = "御見積書"

    intro_text = f"{contract.client.name} 様"
    
    start_date_str = contract.start_date.strftime('%Y年%m月%d日')
    end_date_str = contract.end_date.strftime('%Y年%m月%d日') if contract.end_date else "無期限"
    contract_period = f"{start_date_str}　～　{end_date_str}"
    
    items = [
        {"title": "件名", "text": str(contract.contract_name)},
        {"title": "契約期間", "text": contract_period},
        {"title": "お見積金額", "text": f"{contract.contract_amount:,} 円" if contract.contract_amount else "別途ご相談"},
        {"title": "支払条件", "text": str(contract.payment_site.name if contract.payment_site else "別途ご相談")},
        {"title": "発行日", "text": issued_at.strftime('%Y年%m月%d日')},
        {"title": "発行者", "text": user.get_full_name_japanese()},
    ]

    timestamp = issued_at.strftime('%Y%m%d%H%M%S')
    pdf_filename = f"quotation_{contract.pk}_{timestamp}.pdf"

    buffer = io.BytesIO()
    generate_contract_pdf(buffer, pdf_title, intro_text, items, watermark_text=watermark_text)
    pdf_content = buffer.getvalue()
    buffer.close()

    return pdf_content, pdf_filename, pdf_title
