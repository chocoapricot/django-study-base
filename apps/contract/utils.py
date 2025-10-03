import os
import io
import re
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from .models import ClientContract, StaffContract, ClientContractPrint, StaffContractPrint, ClientContractNumber, StaffContractNumber
from apps.common.pdf_utils import generate_contract_pdf
from apps.system.logs.models import AppLog

def generate_client_contract_number(contract: ClientContract) -> str:
    """
    クライアント契約番号を採番する。
    フォーマット: {クライアントコード}-{契約開始年月}-{4桁連番}
    """
    client_code = contract.client.client_code
    if not client_code:
        raise ValueError("クライアントコードを生成できません。クライアントに有効な法人番号が設定されているか確認してください。")

    year_month = contract.start_date.strftime('%Y%m')

    with transaction.atomic():
        # 行をロックして取得、なければ作成
        number_manager, created = ClientContractNumber.objects.select_for_update().get_or_create(
            client_code=client_code,
            year_month=year_month,
            defaults={
                'last_number': 0,
                'corporate_number': contract.client.corporate_number,
            }
        )

        # 番号をインクリメント
        new_number = number_manager.last_number + 1
        number_manager.last_number = new_number
        number_manager.save()

    # 契約番号をフォーマット
    return f"{client_code}-{year_month}-{new_number:04d}"


def generate_staff_contract_number(contract: StaffContract) -> str:
    """
    スタッフ契約番号を採番する。
    フォーマット: {社員番号}-{契約開始年月}-{2桁連番}
    """
    employee_no = contract.staff.employee_no
    if not employee_no:
        raise ValueError("社員番号が設定されていません。スタッフ情報を確認してください。")

    year_month = contract.start_date.strftime('%Y%m')

    with transaction.atomic():
        # 行をロックして取得、なければ作成
        number_manager, created = StaffContractNumber.objects.select_for_update().get_or_create(
            employee_no=employee_no,
            year_month=year_month,
            defaults={
                'last_number': 0,
                'corporate_number': contract.corporate_number,
            }
        )

        # 番号をインクリメント
        new_number = number_manager.last_number + 1
        number_manager.last_number = new_number
        number_manager.save()

    # 契約番号をフォーマット
    return f"{employee_no}-{year_month}-{new_number:02d}"


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
        intro_text = ""
        start_date_str = contract.start_date.strftime('%Y年%m月%d日')
        end_date_str = contract.end_date.strftime('%Y年%m月%d日') if contract.end_date else "無期限"
        contract_period = f"{start_date_str}　～　{end_date_str}"

        # 派遣契約の場合、契約期間の名称を「派遣期間」とする
        contract_period_title = "契約期間"
        if contract.contract_pattern and contract.contract_pattern.contract_type_code == '20':
            contract_period_title = "派遣期間"

        items = [
            {"title": "契約番号", "text": str(contract.contract_number)},
            {"title": "クライアント名", "text": str(contract.client.name)},
            {"title": "契約名", "text": str(contract.contract_name)},
            {"title": contract_period_title, "text": contract_period},
            {"title": "契約金額", "text": f"{contract.contract_amount:,} 円" if contract.contract_amount else "N/A"},
            {"title": "支払条件", "text": str(contract.payment_site.name if contract.payment_site else "N/A")},
            {"title": "契約内容", "text": str(contract.description)},
            {"title": "備考", "text": str(contract.notes)},
        ]

        # 派遣契約の場合、追加情報を挿入
        if contract.contract_pattern and contract.contract_pattern.contract_type_code == '20' and hasattr(contract, 'haken_info'):
            from apps.company.models import Company, CompanyDepartment
            haken_info = contract.haken_info
            haken_items = []

            # Helper to format user info
            def format_client_user(user, with_phone=False):
                if not user:
                    return "N/A"
                parts = []
                if user.department:
                    parts.append(user.department.name)
                if user.position:
                    parts.append(user.position)
                parts.append(user.name)

                base_info = '　'.join(filter(None, parts))

                if with_phone and user.phone_number:
                    return f"{base_info} 電話番号：{user.phone_number}"
                return base_info

            def format_company_user(user, with_phone=False):
                if not user:
                    return "N/A"
                parts = []
                department = CompanyDepartment.objects.filter(department_code=user.department_code).first() if user.department_code else None
                if department:
                    parts.append(department.name)
                if user.position:
                    parts.append(user.position)
                parts.append(user.name)

                base_info = '　'.join(filter(None, parts))

                if with_phone and user.phone_number:
                    return f"{base_info} 電話番号：{user.phone_number}"
                return base_info

            haken_items.append({"title": "業務内容", "text": str(haken_info.business_content or "")})
            haken_items.append({"title": "責任の程度", "text": str(haken_info.responsibility_degree or "")})

            # 派遣先事業所
            if haken_info.haken_office:
                office = haken_info.haken_office
                client_name = office.client.name
                office_name = office.name
                postal = f"〒{office.postal_code}" if office.postal_code else ""
                address = office.address or ""
                phone = f"電話番号：{office.phone_number}" if office.phone_number else ""

                line1 = f"{client_name}　{office_name}"
                line2 = f"{postal} {address} {phone}".strip()

                haken_office_text = f"{line1}\n{line2}" if line2 else line1
                haken_items.append({"title": "派遣先事業所の名称及び所在地", "text": haken_office_text})
            else:
                haken_items.append({"title": "派遣先事業所の名称及び所在地", "text": ""})

            haken_items.append({"title": "就業場所", "text": str(haken_info.work_location or "")})

            # 組織単位
            if haken_info.haken_unit:
                unit = haken_info.haken_unit
                unit_name = unit.name
                manager_title = f"（{unit.haken_unit_manager_title}）" if unit.haken_unit_manager_title else ""
                haken_unit_text = f"{unit_name}　{manager_title}".strip()
                haken_items.append({"title": "組織単位", "text": haken_unit_text})
            else:
                haken_items.append({"title": "組織単位", "text": ""})

            # 派遣先
            haken_items.append({"title": "派遣先指揮命令者", "text": format_client_user(haken_info.commander)})
            haken_items.append({"title": "派遣先苦情申出先", "text": format_client_user(haken_info.complaint_officer_client, with_phone=True)})
            haken_items.append({"title": "派遣先責任者", "text": format_client_user(haken_info.responsible_person_client, with_phone=True)})

            # 派遣元
            haken_items.append({"title": "派遣元苦情申出先", "text": format_company_user(haken_info.complaint_officer_company, with_phone=True)})
            haken_items.append({"title": "派遣元責任者", "text": format_company_user(haken_info.responsible_person_company, with_phone=True)})

            # 限定の別
            limit_by_agreement_display = haken_info.get_limit_by_agreement_display() if haken_info.limit_by_agreement else "N/A"
            limit_indefinite_or_senior_display = haken_info.get_limit_indefinite_or_senior_display() if haken_info.limit_indefinite_or_senior else "N/A"
            haken_items.append({"title": "協定対象派遣労働者に限定するか否かの別", "text": limit_by_agreement_display})
            haken_items.append({"title": "無期雇用派遣労働者又は60歳以上の者に限定するか否かの別", "text": limit_indefinite_or_senior_display})

            # 許可番号
            company = Company.objects.first()
            if company and company.haken_permit_number:
                haken_items.append({"title": "許可番号", "text": company.haken_permit_number})

            # itemsリストに挿入
            notes_index = -1
            for i, item in enumerate(items):
                if item["title"] == "備考":
                    notes_index = i
                    break

            if notes_index != -1:
                items[notes_index:notes_index] = haken_items
            else:
                items.extend(haken_items)
    elif isinstance(contract, StaffContract):
        contract_type = 'staff'
        intro_text = ""
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

    postamble_text = ""
    if contract.contract_pattern:
        from apps.company.models import Company

        # プレースホルダーの準備
        replacements = {}
        if isinstance(contract, ClientContract):
            company = Company.objects.first()
            replacements = {
                "{{company_name}}": company.name if company else "",
                "{{client_name}}": contract.client.name,
            }
        elif isinstance(contract, StaffContract):
            company = Company.objects.first()
            replacements = {
                "{{company_name}}": company.name if company else "",
                "{{staff_name}}": f"{contract.staff.name_last} {contract.staff.name_first}",
            }

        def replace_placeholders(text):
            text = str(text) if text is not None else ""
            for key, value in replacements.items():
                placeholder = key.strip('{}').strip()
                pattern = re.compile(r'{{\s*' + re.escape(placeholder) + r'\s*}}')
                text = pattern.sub(value, text)
            return text

        terms = contract.contract_pattern.terms.all().order_by('display_position', 'display_order')

        preamble_terms = [term for term in terms if term.display_position == 1]
        body_terms = [term for term in terms if term.display_position == 2]
        postamble_terms = [term for term in terms if term.display_position == 3]

        if preamble_terms:
            preamble_text_parts = [replace_placeholders(term.contract_terms) for term in preamble_terms]
            intro_text = "\n\n".join(preamble_text_parts) + "\n\n" + intro_text

        if body_terms:
            notes_index = -1
            for i, item in enumerate(items):
                if item["title"] == "備考":
                    notes_index = i
                    break

            term_items = [{"title": str(term.contract_clause), "text": replace_placeholders(term.contract_terms)} for term in body_terms]

            if notes_index != -1:
                items[notes_index:notes_index] = term_items
            else:
                items.extend(term_items)

        if postamble_terms:
            postamble_text_parts = [replace_placeholders(term.contract_terms) for term in postamble_terms]
            postamble_text = "\n\n".join(postamble_text_parts)

    timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
    pdf_filename = f"{contract_type}_contract_{contract.pk}_{timestamp}.pdf"
    
    watermark_text = None
    if contract.contract_status in [contract.ContractStatus.DRAFT, contract.ContractStatus.PENDING]:
        watermark_text = "DRAFT"

    buffer = io.BytesIO()
    generate_contract_pdf(buffer, pdf_title, intro_text, items, watermark_text=watermark_text, postamble_text=postamble_text)
    pdf_content = buffer.getvalue()
    buffer.close()

    return pdf_content, pdf_filename, pdf_title


def generate_dispatch_notification_pdf(contract, user, issued_at, watermark_text=None):
    """派遣通知書PDFを生成する"""
    pdf_title = "派遣通知書"

    intro_text = f"{contract.client.name} 様"

    items = [
        {"title": "件名", "text": str(contract.contract_name)},
        {"title": "発行日", "text": issued_at.strftime('%Y年%m月%d日')},
        {"title": "発行者", "text": user.get_full_name_japanese()},
    ]

    timestamp = issued_at.strftime('%Y%m%d%H%M%S')
    pdf_filename = f"dispatch_notification_{contract.pk}_{timestamp}.pdf"

    buffer = io.BytesIO()
    generate_contract_pdf(buffer, pdf_title, intro_text, items, watermark_text=watermark_text)
    pdf_content = buffer.getvalue()
    buffer.close()

    return pdf_content, pdf_filename, pdf_title


def generate_clash_day_notification_pdf(contract, user, issued_at, watermark_text=None):
    """抵触日通知書PDFを生成する"""
    pdf_title = "抵触日通知書"

    intro_text = f"{contract.client.name} 様"

    items = [
        {"title": "件名", "text": str(contract.contract_name)},
        {"title": "発行日", "text": issued_at.strftime('%Y年%m月%d日')},
        {"title": "発行者", "text": user.get_full_name_japanese()},
    ]

    timestamp = issued_at.strftime('%Y%m%d%H%M%S')
    pdf_filename = f"clash_day_notification_{contract.pk}_{timestamp}.pdf"

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
