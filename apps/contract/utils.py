import os
import io
import re
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from .models import ClientContract, StaffContract, ClientContractPrint, StaffContractPrint, ClientContractNumber, StaffContractNumber
from apps.common.pdf_utils import generate_table_based_contract_pdf, generate_article_based_contract_pdf
from apps.system.logs.models import AppLog
from apps.company.models import Company
from apps.common.constants import Constants

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

        bill_unit_name = ""
        if contract.bill_unit:
            from apps.system.settings.models import Dropdowns
            try:
                dropdown = Dropdowns.objects.get(category='bill_unit', value=contract.bill_unit)
                bill_unit_name = dropdown.name
            except Dropdowns.DoesNotExist:
                pass

        contract_amount_text = "N/A"
        if contract.contract_amount is not None:
            contract_amount_text = f"{bill_unit_name} "
            contract_amount_text += f"¥{contract.contract_amount:,}"
        else:
            contract_amount_text = "N/A"

        items = [
            {"title": "契約番号", "text": str(contract.contract_number)},
            {"title": "クライアント名", "text": str(contract.client.name)},
            {"title": "契約名", "text": str(contract.contract_name)},
            {"title": contract_period_title, "text": contract_period},
            {"title": "契約金額", "text": contract_amount_text},
            {"title": "支払条件", "text": str(contract.payment_site.name if contract.payment_site else "N/A")},
        ]
        # 業務内容を備考の前に追加
        if contract.business_content:
            items.append({"title": "業務内容", "text": str(contract.business_content)})

        items.append({"title": "備考", "text": str(contract.notes)})

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

            # 業務内容を haken_items にも追加（派遣契約PDFのレイアウトを維持するため）
            if contract.business_content:
                 # 派遣の場合は、基本情報の業務内容を削除して、派遣情報セクションに含める
                items = [item for item in items if item.get("title") != "業務内容"]
                haken_items.append({"title": "業務内容", "text": str(contract.business_content or "")})

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

            # 派遣先責任者と派遣元責任者のタイトルを決定
            is_manufacturing_dispatch = contract.job_category and contract.job_category.is_manufacturing_dispatch
            client_responsible_person_title = "製造業務専門派遣先責任者" if is_manufacturing_dispatch else "派遣先責任者"
            company_responsible_person_title = "製造業務専門派遣元責任者" if is_manufacturing_dispatch else "派遣元責任者"

            # 派遣先
            haken_items.append({"title": "派遣先指揮命令者", "text": format_client_user(haken_info.commander)})
            haken_items.append({"title": "派遣先苦情申出先", "text": format_client_user(haken_info.complaint_officer_client, with_phone=True)})
            haken_items.append({"title": client_responsible_person_title, "text": format_client_user(haken_info.responsible_person_client, with_phone=True)})

            # 派遣元
            haken_items.append({"title": "派遣元苦情申出先", "text": format_company_user(haken_info.complaint_officer_company, with_phone=True)})
            haken_items.append({"title": company_responsible_person_title, "text": format_company_user(haken_info.responsible_person_company, with_phone=True)})

            # 限定の別
            limit_by_agreement_display = haken_info.get_limit_by_agreement_display() if haken_info.limit_by_agreement else "N/A"
            limit_indefinite_or_senior_display = haken_info.get_limit_indefinite_or_senior_display() if haken_info.limit_indefinite_or_senior else "N/A"
            haken_items.append({"title": "協定対象派遣労働者に限定するか否かの別", "text": limit_by_agreement_display})
            haken_items.append({"title": "無期雇用派遣労働者又は60歳以上の者に限定するか否かの別", "text": limit_indefinite_or_senior_display})

            # 許可番号
            company = Company.objects.first()
            if company and company.haken_permit_number:
                haken_items.append({"title": "許可番号", "text": company.haken_permit_number})

            # 紹介予定派遣(TTP)の場合、追加情報を挿入
            try:
                ttp_info = haken_info.ttp_info
                if ttp_info:
                    ttp_sub_items = []
                    # ClientContractTtpのフィールドをループして項目を作成
                    ttp_fields = [
                        'employer_name','contract_period', 'probation_period', 'business_content',
                        'work_location', 'working_hours', 'break_time', 'overtime',
                        'holidays', 'vacations', 'wages', 'insurances',
                         'other'
                    ]
                    for field_name in ttp_fields:
                        field = ttp_info._meta.get_field(field_name)
                        value = getattr(ttp_info, field_name)
                        if value:  # 値が設定されている項目のみ追加
                            ttp_sub_items.append({
                                'title': field.verbose_name,
                                'text': str(value)
                            })

                    if ttp_sub_items:
                        ttp_section = {
                            'title': '紹介予定派遣に\n関する事項',
                            'rowspan_items': ttp_sub_items
                        }
                        haken_items.append(ttp_section)
            except haken_info.__class__.ttp_info.RelatedObjectDoesNotExist:
                pass # ttp_infoが存在しない場合は何もしない

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

        pay_unit_name = ""
        if contract.pay_unit:
            from apps.system.settings.models import Dropdowns
            try:
                dropdown = Dropdowns.objects.get(category='pay_unit', value=contract.pay_unit)
                pay_unit_name = dropdown.name
            except Dropdowns.DoesNotExist:
                pass

        contract_amount_text = "N/A"
        if contract.contract_amount is not None:
            contract_amount_text = f"{contract.contract_amount:,}円"
            if pay_unit_name:
                contract_amount_text = f"{pay_unit_name} {contract_amount_text}"

        items = [
            {"title": "契約名", "text": str(contract.contract_name)},
            {"title": "スタッフ名", "text": f"{contract.staff.name_last} {contract.staff.name_first}"},
            {"title": "契約番号", "text": str(contract.contract_number or "")},
            {"title": "契約期間", "text": contract_period},
            {"title": "契約金額", "text": contract_amount_text},
            {"title": "就業場所", "text": str(contract.work_location or "")},
            {"title": "業務内容", "text": str(contract.business_content or "")},
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
            intro_text = "\n\n".join(preamble_text_parts) + intro_text

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
    if contract.contract_status in [Constants.CONTRACT_STATUS.DRAFT, Constants.CONTRACT_STATUS.PENDING]:
        watermark_text = "DRAFT"

    buffer = io.BytesIO()
    generate_table_based_contract_pdf(buffer, pdf_title, intro_text, items, watermark_text=watermark_text, postamble_text=postamble_text)
    pdf_content = buffer.getvalue()
    buffer.close()

    return pdf_content, pdf_filename, pdf_title


def generate_dispatch_ledger_pdf(contract, user, issued_at, watermark_text=None):
    """派遣元管理台帳PDFを生成する"""
    pdf_title = "派遣元管理台帳"

    intro_text = f"{contract.client.name} 御中"

    # 内容はタイトルのみとの指定のため、itemsは空リストにする
    items = []

    timestamp = issued_at.strftime('%Y%m%d%H%M%S')
    pdf_filename = f"dispatch_ledger_{contract.pk}_{timestamp}.pdf"

    buffer = io.BytesIO()
    generate_table_based_contract_pdf(buffer, pdf_title, intro_text, items, watermark_text=watermark_text)
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
    generate_table_based_contract_pdf(buffer, pdf_title, intro_text, items, watermark_text=watermark_text)
    pdf_content = buffer.getvalue()
    buffer.close()

    return pdf_content, pdf_filename, pdf_title


def generate_clash_day_notification_pdf(source_obj, user, issued_at, watermark_text=None):
    """抵触日通知書PDFを生成する"""
    from apps.client.models import ClientDepartment
    pdf_title = "抵触日通知書"
    buffer = io.BytesIO()

    # --- データ取得 ---
    company = Company.objects.first()

    if isinstance(source_obj, ClientContract):
        contract = source_obj
        client = contract.client
        haken_info = contract.haken_info
        responsible_person = haken_info.responsible_person_client
        haken_office = haken_info.haken_office
        clash_date = haken_office.haken_jigyosho_teishokubi if haken_office else None
        # 送付元 (右) - 契約書から
        client_name_text = f"{client.name}"
        person_text = ""
        if responsible_person:
            position = responsible_person.position or ""
            name = responsible_person.name or ""
            person_text = f"役職 {position}\n氏名 {name}"

        from_address_lines = ["（派遣先）", client_name_text]
        if person_text:
            from_address_lines.append(person_text)

    elif isinstance(source_obj, ClientDepartment):
        department = source_obj
        client = department.client
        haken_office = department
        clash_date = department.haken_jigyosho_teishokubi
        # 送付元 (右) - 組織情報から
        from_address_lines = [
            "（派遣先）",
            f"{client.name}",
            f"{department.name}"
        ]
    else:
        # 不明なオブジェクトタイプの場合はエラー
        return None, None, None

    # --- PDFコンテンツの準備 ---
    # 宛先 (左)
    company_name_text = f"{company.name} 御中" if company else ""
    to_address_lines = [
        "（派遣元）",
        company_name_text,
    ]

    # メインタイトル
    main_title = "派遣可能期間の制限（事業所単位の期間制限）に抵触する日の通知"

    # 概要
    summary_lines = [
        "労働者派遣法第２６条第４項に基づき、派遣可能期間の制限（事業所単位の期間制限）に抵触することとなる最初の日（以下、「抵触日」という。）を、下記のとおり通知します。"
    ]

    # 本文
    body_title = "記"
    body_items = []

    # 1. 事業所
    office_name = haken_office.name if haken_office else "（事業所情報なし）"
    office_address = ""
    if haken_office:
        postal = f"〒{haken_office.postal_code}" if haken_office.postal_code else ""
        address = haken_office.address or ""
        office_address = f"{postal} {address}".strip()
    item1_text = f"１．労働者派遣の役務の提供を受ける事業所\n{office_name}\n{office_address}"
    body_items.append(item1_text)

    # 2. 抵触日
    clash_date_str = clash_date.strftime('%Y年%m月%d日') if clash_date else "（抵触日の設定なし）"
    item2_text = f"２．上記事業所の抵触日\n{clash_date_str}"
    body_items.append(item2_text)

    # 3. その他
    item3_text = "３．その他\n事業所単位の派遣可能期間を延長した場合は、速やかに、労働者派遣法第４０条の２第７項に基づき、延長後の抵触日を通知します。"
    body_items.append(item3_text)

    # --- PDF生成 ---
    generate_article_based_contract_pdf(
        buffer,
        meta_title=pdf_title,
        to_address_lines=to_address_lines,
        from_address_lines=from_address_lines,
        main_title_text=main_title,
        summary_lines=summary_lines,
        body_title_text=body_title,
        body_items=body_items,
        watermark_text=watermark_text
    )

    pdf_content = buffer.getvalue()
    buffer.close()

    timestamp = issued_at.strftime('%Y%m%d%H%M%S')
    pdf_filename = f"clash_day_notification_{source_obj.pk}_{timestamp}.pdf"

    return pdf_content, pdf_filename, pdf_title


def generate_quotation_pdf(contract, user, issued_at, watermark_text=None):
    """見積書PDFを生成する"""
    pdf_title = "御見積書"

    intro_text = f"{contract.client.name} 様"
    
    start_date_str = contract.start_date.strftime('%Y年%m月%d日')
    end_date_str = contract.end_date.strftime('%Y年%m月%d日') if contract.end_date else "無期限"
    contract_period = f"{start_date_str}　～　{end_date_str}"
    
    bill_unit_name = ""
    if contract.bill_unit:
        from apps.system.settings.models import Dropdowns
        try:
            dropdown = Dropdowns.objects.get(category='bill_unit', value=contract.bill_unit)
            bill_unit_name = dropdown.name
        except Dropdowns.DoesNotExist:
            pass

    contract_amount_text = "別途ご相談"
    if contract.contract_amount is not None:
        contract_amount_text = f"¥{contract.contract_amount:,}"
        if bill_unit_name:
            contract_amount_text += f" / {bill_unit_name}"

    items = [
        {"title": "件名", "text": str(contract.contract_name)},
        {"title": "契約期間", "text": contract_period},
        {"title": "お見積金額", "text": contract_amount_text},
        {"title": "支払条件", "text": str(contract.payment_site.name if contract.payment_site else "別途ご相談")},
        {"title": "発行日", "text": issued_at.strftime('%Y年%m月%d日')},
        {"title": "発行者", "text": user.get_full_name_japanese()},
    ]

    timestamp = issued_at.strftime('%Y%m%d%H%M%S')
    pdf_filename = f"quotation_{contract.pk}_{timestamp}.pdf"

    buffer = io.BytesIO()
    generate_table_based_contract_pdf(buffer, pdf_title, intro_text, items, watermark_text=watermark_text)
    pdf_content = buffer.getvalue()
    buffer.close()

    return pdf_content, pdf_filename, pdf_title