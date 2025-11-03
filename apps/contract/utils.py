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
        if contract.contract_pattern and contract.contract_pattern.contract_type_code == Constants.CLIENT_CONTRACT_TYPE.DISPATCH:
            return "労働者派遣個別契約書"
        else:
            return "業務委託個別契約書"
    elif isinstance(contract, StaffContract):
        return "雇用契約書兼労働条件通知書"
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
        if contract.contract_pattern and contract.contract_pattern.contract_type_code == Constants.CLIENT_CONTRACT_TYPE.DISPATCH:
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

        # 派遣契約の場合、追加情報を挿入
        if contract.contract_pattern and contract.contract_pattern.contract_type_code == Constants.CLIENT_CONTRACT_TYPE.DISPATCH and hasattr(contract, 'haken_info'):
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

            # 抵触日制限外詳細は業務内容の次に配置
            try:
                haken_exempt_info = haken_info.haken_exempt_info
                if haken_exempt_info and haken_exempt_info.period_exempt_detail:
                    haken_items.append({"title": "抵触日制限外詳細", "text": str(haken_exempt_info.period_exempt_detail)})
            except haken_info.__class__.haken_exempt_info.RelatedObjectDoesNotExist:
                pass  # haken_exempt_infoが存在しない場合は何もしない

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

            # itemsリストに挿入（備考の前に挿入）
            notes_index = -1
            for i, item in enumerate(items):
                if item["title"] == "備考":
                    notes_index = i
                    break

            if notes_index != -1:
                items[notes_index:notes_index] = haken_items
            else:
                items.extend(haken_items)

        items.append({"title": "備考", "text": str(contract.notes)})
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
            {"title": "契約番号", "text": str(contract.contract_number or "")},
            {"title": "契約名", "text": str(contract.contract_name)},
            {"title": "スタッフ名", "text": f"{contract.staff.name_last} {contract.staff.name_first}"},
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

        # 派遣契約の場合、契約パターン文言の後に追加項目を挿入
        if isinstance(contract, ClientContract) and contract.contract_pattern and contract.contract_pattern.contract_type_code == Constants.CLIENT_CONTRACT_TYPE.DISPATCH and hasattr(contract, 'haken_info'):
            haken_info = contract.haken_info
            additional_items = []

            # 紹介予定派遣(TTP)の場合、追加情報を挿入（契約パターン文言の次）
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
                        additional_items.append(ttp_section)
            except haken_info.__class__.ttp_info.RelatedObjectDoesNotExist:
                pass # ttp_infoが存在しない場合は何もしない

            # 協定対象派遣労働者に限定するか否かの別（紹介予定派遣に関する事項の次）
            limit_by_agreement_display = haken_info.get_limit_by_agreement_display() if haken_info.limit_by_agreement else "N/A"
            additional_items.append({"title": "協定対象派遣労働者に限定するか否かの別", "text": limit_by_agreement_display})

            # 無期雇用派遣労働者又は60歳以上の者に限定するか否かの別（その次）
            limit_indefinite_or_senior_display = haken_info.get_limit_indefinite_or_senior_display() if haken_info.limit_indefinite_or_senior else "N/A"
            additional_items.append({"title": "無期雇用派遣労働者又は60歳以上の者に限定するか否かの別", "text": limit_indefinite_or_senior_display})

            # 許可番号（その次）
            from apps.company.models import Company
            company = Company.objects.first()
            if company and company.haken_permit_number:
                additional_items.append({"title": "許可番号", "text": company.haken_permit_number})

            # 追加項目を備考の前に挿入
            if additional_items:
                notes_index = -1
                for i, item in enumerate(items):
                    if item["title"] == "備考":
                        notes_index = i
                        break

                if notes_index != -1:
                    items[notes_index:notes_index] = additional_items
                else:
                    items.extend(additional_items)

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


def generate_haken_motokanri_pdf(contract, user, issued_at, watermark_text=None):
    """派遣元管理台帳PDFを生成する"""
    from apps.company.models import Company
    from datetime import date
    
    pdf_title = "派遣元管理台帳"
    
    # 会社情報を取得
    company = Company.objects.first()
    client = contract.client
    haken_info = contract.haken_info
    
    # クライアント契約に紐づく割当を取得（割当ごとに出力）
    from apps.contract.models import ContractAssignment
    assignments = ContractAssignment.objects.filter(
        client_contract=contract
    ).select_related('staff_contract__staff', 'staff_contract__employment_type').all()
    
    # PDFコンテンツの準備
    intro_text = "労働者派遣法（労働者派遣事業の適正な運営の確保及び派遣労働者の保護等に関する法律）第37条「派遣元管理台帳」として作成が必要であり、派遣元事業主は、派遣元管理台帳を3年間保存しなければならない。労働者派遣法施行規則第35条の記載事項が必要。"
    items = []
    
    # 割当ごとに派遣元管理台帳の項目を作成
    for i, assignment in enumerate(assignments, 1):
        staff_contract = assignment.staff_contract
        staff = staff_contract.staff
        
        # スタッフが複数の場合、2人目以降は新しいタイトルから開始
        if i > 1:
            items.append({
                "title": "派遣元管理台帳",
                "is_new_page_title": True,
                "text": ""
            })
        
        # 0. 契約番号（最初に追加）
        contract_number = contract.contract_number if contract.contract_number else "-"
        items.append({
            "title": "契約番号",
            "text": contract_number
        })
        
        # 1. 派遣労働者氏名
        full_name = f"{staff.name_last} {staff.name_first}"
        items.append({
            "title": "派遣労働者氏名",
            "text": full_name
        })
        
        # 2. 60歳以上であるか否かの別（派遣先通知書のロジックを参考）
        age_classification = ""
        if staff.birth_date:
            # 割当開始日 = スタッフ契約とクライアント契約が重なる期間の開始日
            assignment_start_date = max(contract.start_date, staff_contract.start_date)
            birth_date = staff.birth_date
            age_years = assignment_start_date.year - birth_date.year
            if (assignment_start_date.month, assignment_start_date.day) < (birth_date.month, birth_date.day):
                age_years -= 1
            
            # 60歳以上かどうかの判定
            if age_years >= 60:
                age_classification = "60歳以上"
            else:
                age_classification = "60歳未満"
        else:
            age_classification = "生年月日未設定"
        
        items.append({
            "title": "60歳以上であるか否かの別",
            "text": age_classification
        })
        
        # 3. 協定対象派遣労働者かの別
        agreement_target_text = ""
        if company and company.dispatch_treatment_method == 'agreement':
            agreement_target_text = "協定対象派遣労働者"
        else:
            agreement_target_text = "協定対象派遣労働者ではない"
        items.append({
            "title": "協定対象派遣労働者かの別",
            "text": agreement_target_text
        })
        
        # 4. 無期雇用か有期雇用かの別
        employment_type_text = ""
        contract_period_text = ""
        if staff_contract.employment_type:
            if staff_contract.employment_type.is_fixed_term:
                employment_type_text = "有期雇用派遣労働者"
                # 有期派遣労働者の場合は労働契約期間も出力
                if staff_contract.start_date and staff_contract.end_date:
                    contract_period_text = f"{staff_contract.start_date.strftime('%Y年%m月%d日')} ～ {staff_contract.end_date.strftime('%Y年%m月%d日')}"
                elif staff_contract.start_date:
                    contract_period_text = f"{staff_contract.start_date.strftime('%Y年%m月%d日')} ～ （終了日未定）"
            else:
                employment_type_text = "無期雇用派遣労働者"
        else:
            employment_type_text = "未設定"
        
        items.append({
            "title": "無期雇用か有期雇用かの別",
            "text": employment_type_text
        })
        
        # 労働契約期間（有期雇用の場合のみ）
        if contract_period_text:
            items.append({
                "title": "労働契約期間",
                "text": contract_period_text
            })
        
        # 5. 派遣先の名称
        items.append({
            "title": "派遣先の名称",
            "text": client.name if client.name else "-"
        })
        
        # 6. 派遣先の事業所の名称
        workplace_name = ""
        if haken_info and haken_info.haken_office:
            workplace_name = haken_info.haken_office.name
        items.append({
            "title": "派遣先の事業所の名称",
            "text": workplace_name if workplace_name else "-"
        })
        
        # 7. 就業場所
        workplace_address = ""
        if haken_info and haken_info.work_location:
            workplace_address = haken_info.work_location
        items.append({
            "title": "就業場所",
            "text": workplace_address if workplace_address else "-"
        })
        
        # 8. 組織単位
        organization_unit = ""
        if haken_info and haken_info.haken_unit:
            organization_unit = haken_info.haken_unit.name
        items.append({
            "title": "組織単位",
            "text": organization_unit if organization_unit else "-"
        })
        
        # 9. 業務の種類
        business_type = ""
        if contract.business_content:
            business_type = contract.business_content
        elif staff_contract.business_content:
            business_type = staff_contract.business_content
        items.append({
            "title": "業務の種類",
            "text": business_type if business_type else "-"
        })
        
        # 10. 抵触日制限外詳細（もし登録があれば）
        if haken_info:
            try:
                haken_exempt_info = haken_info.haken_exempt_info
                if haken_exempt_info and haken_exempt_info.period_exempt_detail:
                    items.append({
                        "title": "抵触日制限外詳細",
                        "text": str(haken_exempt_info.period_exempt_detail)
                    })
            except haken_info.__class__.haken_exempt_info.RelatedObjectDoesNotExist:
                pass  # haken_exempt_infoが存在しない場合は何もしない
        
        # 11. 責任の程度
        responsibility_degree = ""
        if haken_info and haken_info.responsibility_degree:
            responsibility_degree = haken_info.responsibility_degree
        items.append({
            "title": "責任の程度",
            "text": responsibility_degree if responsibility_degree else "-"
        })
        
        # 12. 派遣期間（クライアント契約の期間）
        dispatch_period = ""
        if contract.start_date and contract.end_date:
            dispatch_period = f"{contract.start_date.strftime('%Y年%m月%d日')} ～ {contract.end_date.strftime('%Y年%m月%d日')}"
        elif contract.start_date:
            dispatch_period = f"{contract.start_date.strftime('%Y年%m月%d日')} ～ （終了日未定）"
        else:
            dispatch_period = "-"
        
        items.append({
            "title": "派遣期間",
            "text": dispatch_period
        })
        
        # Helper functions for formatting user info (個別契約書と同じ表記)
        def format_client_user_for_ledger(user, with_phone=False):
            if not user:
                return "-"
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

        def format_company_user_for_ledger(user, with_phone=False):
            if not user:
                return "-"
            from apps.company.models import CompanyDepartment
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
        
        # 13. 派遣元責任者（個別契約書と同じ表記：役職・氏名・電話番号）
        company_responsible = ""
        if haken_info and haken_info.responsible_person_company:
            # 製造派遣かどうかでタイトルを決定
            is_manufacturing_dispatch = contract.job_category and contract.job_category.is_manufacturing_dispatch
            company_responsible = format_company_user_for_ledger(haken_info.responsible_person_company, with_phone=True)
        
        company_responsible_title = "製造業務専門派遣元責任者" if (contract.job_category and contract.job_category.is_manufacturing_dispatch) else "派遣元責任者"
        items.append({
            "title": company_responsible_title,
            "text": company_responsible if company_responsible else "-"
        })
        
        # 14. 派遣先責任者（個別契約書と同じ表記：役職・氏名・電話番号）
        client_responsible = ""
        if haken_info and haken_info.responsible_person_client:
            client_responsible = format_client_user_for_ledger(haken_info.responsible_person_client, with_phone=True)
        
        client_responsible_title = "製造業務専門派遣先責任者" if (contract.job_category and contract.job_category.is_manufacturing_dispatch) else "派遣先責任者"
        items.append({
            "title": client_responsible_title,
            "text": client_responsible if client_responsible else "-"
        })
        
        # 15. 個別契約書記載事項（契約パターンの契約文言「本文」のみを出力）
        if contract.contract_pattern:
            # 契約パターンに紐づく契約文言の「本文」のみを取得
            contract_terms = contract.contract_pattern.terms.filter(display_position=2).order_by('display_order')
            
            if contract_terms.exists():
                # 3列表示のテーブル形式で出力
                contract_terms_items = []
                for term in contract_terms:
                    contract_terms_items.append({
                        'title': '個別契約書記載事項',
                        'clause': term.contract_clause,
                        'terms': term.contract_terms
                    })
                
                # 3列表示の特別な項目として追加
                items.append({
                    'title': '個別契約書記載事項',
                    'contract_terms_table': contract_terms_items
                })
        
        # 16. 派遣労働者からの苦情の処理状況（件名のみ）
        items.append({
            "title": "派遣労働者からの苦情の処理状況",
            "text": "-"
        })
        
        # 17. 各種保険の取得届提出の有無（派遣先通知書と同じロジック、労災保険除く）
        staff = staff_contract.staff
        insurance_status_lines = []
        payroll = getattr(staff, 'payroll', None)
        
        # 健康保険
        if payroll and payroll.health_insurance_join_date:
            insurance_status_lines.append("健康保険：有")
        else:
            reason = payroll.health_insurance_non_enrollment_reason if payroll else ""
            if reason:
                insurance_status_lines.append(f"健康保険：無　（未加入理由）{reason}")
            else:
                insurance_status_lines.append("健康保険：無")
        
        # 厚生年金
        if payroll and payroll.welfare_pension_join_date:
            insurance_status_lines.append("厚生年金：有")
        else:
            reason = payroll.pension_insurance_non_enrollment_reason if payroll else ""
            if reason:
                insurance_status_lines.append(f"厚生年金：無　（未加入理由）{reason}")
            else:
                insurance_status_lines.append("厚生年金：無")
        
        # 雇用保険
        if payroll and payroll.employment_insurance_join_date:
            insurance_status_lines.append("雇用保険：有")
        else:
            reason = payroll.employment_insurance_non_enrollment_reason if payroll else ""
            if reason:
                insurance_status_lines.append(f"雇用保険：無　（未加入理由）{reason}")
            else:
                insurance_status_lines.append("雇用保険：無")
        
        insurance_status_text = "\n".join(insurance_status_lines)
        items.append({
            "title": "各種保険の取得届提出の有無",
            "text": insurance_status_text
        })
        
        # 18. 教育訓練の内容（件名のみ）
        items.append({
            "title": "教育訓練の内容",
            "text": "-"
        })
        
        # 19. キャリア・コンサルティングの日時及び内容（件名のみ）
        items.append({
            "title": "キャリア・コンサルティングの日時及び内容",
            "text": "-"
        })
        
        # 20. 雇用安定措置の内容（派遣雇用安定措置登録から取得）
        employment_stability_measures = []
        
        # 割当に紐づく派遣雇用安定措置情報を取得
        try:
            haken_measures = assignment.haken_info
            
            # 派遣先への直接雇用の依頼
            if haken_measures.direct_employment_request:
                measure_text = "派遣先への直接雇用の依頼"
                if haken_measures.direct_employment_detail:
                    measure_text += f"\n{haken_measures.direct_employment_detail}"
                employment_stability_measures.append(measure_text)
            
            # 新たな派遣先の提供
            if haken_measures.new_dispatch_offer:
                measure_text = "新たな派遣先の提供"
                if haken_measures.new_dispatch_detail:
                    measure_text += f"\n{haken_measures.new_dispatch_detail}"
                employment_stability_measures.append(measure_text)
            
            # 派遣元での無期雇用化
            if haken_measures.indefinite_employment:
                measure_text = "派遣元での無期雇用化"
                if haken_measures.indefinite_employment_detail:
                    measure_text += f"\n{haken_measures.indefinite_employment_detail}"
                employment_stability_measures.append(measure_text)
            
            # その他の雇用安定措置
            if haken_measures.other_measures:
                measure_text = "その他の雇用安定措置"
                if haken_measures.other_measures_detail:
                    measure_text += f"\n{haken_measures.other_measures_detail}"
                employment_stability_measures.append(measure_text)
                
        except AttributeError:
            # haken_infoが存在しない場合
            pass
        
        # 雇用安定措置の内容を出力
        if employment_stability_measures:
            employment_stability_text = "\n\n".join(employment_stability_measures)
        else:
            # 派遣雇用安定措置登録から情報を取得できない場合は「実施なし」
            employment_stability_text = "実施なし"
        
        items.append({
            "title": "雇用安定措置の内容",
            "text": employment_stability_text
        })
        
        # 21. 紹介予定派遣に関する事項（個別契約書と同様の形式で出力）
        if haken_info:
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
                        items.append(ttp_section)
            except haken_info.__class__.ttp_info.RelatedObjectDoesNotExist:
                pass # ttp_infoが存在しない場合は何もしない
        
        # 割当間の区切り（最後の割当以外）
        if i < len(assignments):
            items.append({
                "title": "",
                "text": "",
                "is_separator": True
            })

    timestamp = issued_at.strftime('%Y%m%d%H%M%S')
    pdf_filename = f"haken_motokanri_{contract.pk}_{timestamp}.pdf"

    buffer = io.BytesIO()
    generate_table_based_contract_pdf(buffer, pdf_title, intro_text, items, watermark_text=watermark_text)
    pdf_content = buffer.getvalue()
    buffer.close()

    return pdf_content, pdf_filename, pdf_title


def generate_haken_sakikanri_pdf(contract, user, issued_at, watermark_text=None):
    """派遣先管理台帳PDFを生成する"""
    from apps.company.models import Company
    from datetime import date
    
    pdf_title = "派遣先管理台帳"
    
    # 会社情報を取得
    company = Company.objects.first()
    client = contract.client
    haken_info = contract.haken_info
    
    # クライアント契約に紐づく割当を取得（割当ごとに出力）
    from apps.contract.models import ContractAssignment
    assignments = ContractAssignment.objects.filter(
        client_contract=contract
    ).select_related('staff_contract__staff', 'staff_contract__employment_type').all()
    
    # PDFコンテンツの準備
    intro_text = "労働者派遣法（労働者派遣事業の適正な運営の確保及び派遣労働者の保護等に関する法律）第42条「派遣先管理台帳」として作成が必要であり、派遣先事業主は、派遣先管理台帳を3年間保存しなければならない。労働者派遣法施行規則第36条の記載事項が必要。"
    items = []
    
    # 割当ごとに派遣先管理台帳の項目を作成
    for i, assignment in enumerate(assignments, 1):
        staff_contract = assignment.staff_contract
        staff = staff_contract.staff
        
        # スタッフが複数の場合、2人目以降は新しいタイトルから開始
        if i > 1:
            items.append({
                "title": "派遣先管理台帳",
                "is_new_page_title": True,
                "text": ""
            })
        
        # 派遣先管理台帳の項目（派遣元管理台帳とは異なる項目）
        # 1. 契約番号
        items.append({
            "title": "契約番号",
            "text": contract.contract_number if contract.contract_number else "-"
        })
        
        # 2. 派遣労働者氏名
        full_name = f"{staff.name_last} {staff.name_first}"
        items.append({
            "title": "派遣労働者氏名",
            "text": full_name
        })
        
        # 3. 60歳以上であるか否かの別
        age_classification = ""
        if staff.birth_date:
            # 割当開始日 = スタッフ契約とクライアント契約が重なる期間の開始日
            assignment_start_date = max(contract.start_date, staff_contract.start_date)
            birth_date = staff.birth_date
            age_years = assignment_start_date.year - birth_date.year
            if (assignment_start_date.month, assignment_start_date.day) < (birth_date.month, birth_date.day):
                age_years -= 1
            
            # 60歳以上かどうかの判定
            if age_years >= 60:
                age_classification = "60歳以上"
            else:
                age_classification = "60歳未満"
        else:
            age_classification = "生年月日未設定"
        
        items.append({
            "title": "60歳以上であるか否かの別",
            "text": age_classification
        })
        
        # 4. 無期雇用か有期雇用かの別
        employment_type_text = ""
        if staff_contract.employment_type:
            if staff_contract.employment_type.is_fixed_term:
                employment_type_text = "有期雇用派遣労働者"
            else:
                employment_type_text = "無期雇用派遣労働者"
        else:
            employment_type_text = "未設定"
        
        items.append({
            "title": "無期雇用か有期雇用かの別",
            "text": employment_type_text
        })
        
        # 5. 労働契約期間（有期雇用の場合のみ）
        contract_period_text = ""
        if staff_contract.employment_type and staff_contract.employment_type.is_fixed_term:
            if staff_contract.start_date and staff_contract.end_date:
                contract_period_text = f"{staff_contract.start_date.strftime('%Y年%m月%d日')} ～ {staff_contract.end_date.strftime('%Y年%m月%d日')}"
            elif staff_contract.start_date:
                contract_period_text = f"{staff_contract.start_date.strftime('%Y年%m月%d日')} ～ （終了日未定）"
            else:
                contract_period_text = "-"
            
            items.append({
                "title": "労働契約期間",
                "text": contract_period_text
            })
        
        # 6. 派遣元事業主の名称
        items.append({
            "title": "派遣元事業主の名称",
            "text": company.name if company and company.name else "-"
        })
        
        # 7. 派遣元の事業所の名称（スタッフの所属部署）
        # 契約開始日時点での有効な部署を取得
        contract_start_date = contract.start_date
        staff_department_name = staff.get_department_name(contract_start_date)
        
        items.append({
            "title": "派遣元の事業所の名称",
            "text": staff_department_name if staff_department_name else "-"
        })
        
        # 8. 派遣元事業主の事業所の所在地
        office_address = ""
        if staff.department_code:
            from apps.company.models import CompanyDepartment
            try:
                # 契約開始日時点で有効な部署を取得
                department = CompanyDepartment.objects.filter(
                    department_code=staff.department_code
                ).filter(
                    models.Q(valid_from__isnull=True) | models.Q(valid_from__lte=contract_start_date)
                ).filter(
                    models.Q(valid_to__isnull=True) | models.Q(valid_to__gte=contract_start_date)
                ).first()
                
                if department and department.address:
                    # スタッフの所属部署に住所がある場合
                    office_info_parts = [department.address]
                    if department.phone_number:
                        office_info_parts.append(f"電話番号：{department.phone_number}")
                    office_address = "\n".join(office_info_parts)
                elif company and company.address:
                    # 部署に住所がない場合は会社の住所を使用
                    office_info_parts = [company.address]
                    if company.phone_number:
                        office_info_parts.append(f"電話番号：{company.phone_number}")
                    office_address = "\n".join(office_info_parts)
                else:
                    office_address = "-"
            except Exception:
                # エラーの場合は会社の住所を使用
                if company and company.address:
                    office_info_parts = [company.address]
                    if company.phone_number:
                        office_info_parts.append(f"電話番号：{company.phone_number}")
                    office_address = "\n".join(office_info_parts)
                else:
                    office_address = "-"
        elif company and company.address:
            # 部署コードがない場合は会社の住所を使用
            office_info_parts = [company.address]
            if company.phone_number:
                office_info_parts.append(f"電話番号：{company.phone_number}")
            office_address = "\n".join(office_info_parts)
        else:
            office_address = "-"
        
        items.append({
            "title": "派遣元事業主の事業所の所在地",
            "text": office_address
        })
        
        # 9. 派遣期間
        dispatch_period = ""
        if contract.start_date and contract.end_date:
            dispatch_period = f"{contract.start_date.strftime('%Y年%m月%d日')} ～ {contract.end_date.strftime('%Y年%m月%d日')}"
        elif contract.start_date:
            dispatch_period = f"{contract.start_date.strftime('%Y年%m月%d日')} ～ （終了日未定）"
        else:
            dispatch_period = "-"
        
        items.append({
            "title": "派遣期間",
            "text": dispatch_period
        })
        
        # 10. 就業場所
        workplace_address = ""
        if haken_info and haken_info.work_location:
            workplace_address = haken_info.work_location
        items.append({
            "title": "就業場所",
            "text": workplace_address if workplace_address else "-"
        })
        
        # 11. 組織単位
        organization_unit = ""
        if haken_info and haken_info.haken_unit:
            organization_unit = haken_info.haken_unit.name
        items.append({
            "title": "組織単位",
            "text": organization_unit if organization_unit else "-"
        })
        
        # 12. 業務の種類
        business_type = ""
        if contract.business_content:
            business_type = contract.business_content
        elif staff_contract.business_content:
            business_type = staff_contract.business_content
        items.append({
            "title": "業務の種類",
            "text": business_type if business_type else "-"
        })
        
        # 13. 抵触日制限外詳細（登録がある場合のみ）
        if haken_info:
            try:
                haken_exempt_info = haken_info.haken_exempt_info
                if haken_exempt_info and haken_exempt_info.period_exempt_detail:
                    items.append({
                        "title": "抵触日制限外詳細",
                        "text": str(haken_exempt_info.period_exempt_detail)
                    })
            except haken_info.__class__.haken_exempt_info.RelatedObjectDoesNotExist:
                pass  # haken_exempt_infoが存在しない場合は何もしない
        
        # 14. 派遣先責任者
        client_responsible = ""
        if haken_info and haken_info.responsible_person_client:
            def format_client_user_for_ledger(user, with_phone=False):
                if not user:
                    return "-"
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
            
            client_responsible = format_client_user_for_ledger(haken_info.responsible_person_client, with_phone=True)
        
        client_responsible_title = "製造業務専門派遣先責任者" if (contract.job_category and contract.job_category.is_manufacturing_dispatch) else "派遣先責任者"
        items.append({
            "title": client_responsible_title,
            "text": client_responsible if client_responsible else "-"
        })
        
        # 15. 就業状況
        items.append({
            "title": "就業状況",
            "text": "別添のとおり"
        })
        
        # 16. 派遣元責任者（派遣元管理台帳と同じ）
        def format_company_user_for_ledger(user, with_phone=False):
            if not user:
                return "-"
            from apps.company.models import CompanyDepartment
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
        
        company_responsible = ""
        if haken_info and haken_info.responsible_person_company:
            company_responsible = format_company_user_for_ledger(haken_info.responsible_person_company, with_phone=True)
        
        company_responsible_title = "製造業務専門派遣元責任者" if (contract.job_category and contract.job_category.is_manufacturing_dispatch) else "派遣元責任者"
        items.append({
            "title": company_responsible_title,
            "text": company_responsible if company_responsible else "-"
        })
        
        # 17. 派遣労働者からの苦情の処理状況
        items.append({
            "title": "派遣労働者からの苦情の処理状況",
            "text": "別添のとおり"
        })
        
        # 18. 各種保険の取得届提出の有無（派遣元管理台帳と同じ）
        insurance_status_lines = []
        payroll = getattr(staff, 'payroll', None)
        
        # 健康保険
        if payroll and payroll.health_insurance_join_date:
            insurance_status_lines.append("健康保険：有")
        else:
            reason = payroll.health_insurance_non_enrollment_reason if payroll else ""
            if reason:
                insurance_status_lines.append(f"健康保険：無　（未加入理由）{reason}")
            else:
                insurance_status_lines.append("健康保険：無")
        
        # 厚生年金
        if payroll and payroll.welfare_pension_join_date:
            insurance_status_lines.append("厚生年金：有")
        else:
            reason = payroll.pension_insurance_non_enrollment_reason if payroll else ""
            if reason:
                insurance_status_lines.append(f"厚生年金：無　（未加入理由）{reason}")
            else:
                insurance_status_lines.append("厚生年金：無")
        
        # 雇用保険
        if payroll and payroll.employment_insurance_join_date:
            insurance_status_lines.append("雇用保険：有")
        else:
            reason = payroll.employment_insurance_non_enrollment_reason if payroll else ""
            if reason:
                insurance_status_lines.append(f"雇用保険：無　（未加入理由）{reason}")
            else:
                insurance_status_lines.append("雇用保険：無")
        
        insurance_status_text = "\n".join(insurance_status_lines)
        items.append({
            "title": "各種保険の取得届提出の有無",
            "text": insurance_status_text
        })
        
        # 19. 教育訓練の内容
        items.append({
            "title": "教育訓練の内容",
            "text": "別添のとおり"
        })
        
        # 20. 紹介予定派遣に関する事項（TTPの場合のみ）
        if haken_info:
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
                        items.append(ttp_section)
            except haken_info.__class__.ttp_info.RelatedObjectDoesNotExist:
                pass # ttp_infoが存在しない場合は何もしない
        
        # 割当間の区切り（最後の割当以外）
        if i < len(assignments):
            items.append({
                "title": "",
                "text": "",
                "is_separator": True
            })

    timestamp = issued_at.strftime('%Y%m%d%H%M%S')
    pdf_filename = f"haken_sakikanri_{contract.pk}_{timestamp}.pdf"

    buffer = io.BytesIO()
    generate_table_based_contract_pdf(buffer, pdf_title, intro_text, items, watermark_text=watermark_text)
    pdf_content = buffer.getvalue()
    buffer.close()

    return pdf_content, pdf_filename, pdf_title


def generate_haken_notification_pdf(contract, user, issued_at, watermark_text=None):
    """派遣先通知書PDFを生成する"""
    from apps.company.models import Company
    from datetime import date
    
    pdf_title = "派遣先通知書"

    # --- データ取得 ---
    company = Company.objects.first()
    client = contract.client
    haken_info = contract.haken_info
    responsible_person = haken_info.responsible_person_client if haken_info else None

    # クライアント契約に紐づくスタッフ契約を取得
    all_staff_contracts = contract.staff_contracts.select_related('staff', 'employment_type').all()
    
    # 同じスタッフが複数いる場合は、最も早い開始日の契約のみを残す
    staff_contract_dict = {}
    for staff_contract in all_staff_contracts:
        staff_id = staff_contract.staff.id
        if staff_id not in staff_contract_dict:
            staff_contract_dict[staff_id] = staff_contract
        else:
            # より早い開始日の契約を保持
            if staff_contract.start_date < staff_contract_dict[staff_id].start_date:
                staff_contract_dict[staff_id] = staff_contract
    
    # 重複を除去したスタッフ契約リスト
    staff_contracts = list(staff_contract_dict.values())

    # --- PDFコンテンツの準備 ---
    # 宛先 (左上) - 派遣先
    client_name_text = f"{client.name} 御中"
    to_address_lines = ["（派遣先）", client_name_text]

    # 送付元 (右上) - 派遣元
    company_name_text = f"{company.name}" if company else ""
    company_address = f"{company.address}" if company and company.address else ""
    
    from_address_lines = ["（派遣元）", company_name_text]
    if company_address:
        from_address_lines.append(company_address)

    # 前文
    intro_text = f"労働者派遣契約に基づき下記の者を派遣いたします。"

    # テーブル項目（契約情報と派遣労働者情報）
    items = []

    # 契約情報を追加
    contract_info_items = []
    
    # 契約番号
    contract_info_items.append({
        "title": "契約番号",
        "text": contract.contract_number if contract.contract_number else "-"
    })
    
    # クライアント名
    contract_info_items.append({
        "title": "派遣先名",
        "text": client.name if client.name else "-"
    })
    
    # 派遣期間
    dispatch_period = ""
    if contract.start_date and contract.end_date:
        dispatch_period = f"{contract.start_date.strftime('%Y年%m月%d日')} ～ {contract.end_date.strftime('%Y年%m月%d日')}"
    elif contract.start_date:
        dispatch_period = f"{contract.start_date.strftime('%Y年%m月%d日')} ～ （終了日未定）"
    else:
        dispatch_period = "-"
    
    contract_info_items.append({
        "title": "派遣期間",
        "text": dispatch_period
    })
    
    # 契約情報をrowspan形式で追加
    items.append({
        "title": "契約情報",
        "rowspan_items": contract_info_items
    })

    # 派遣労働者情報を追加（2段階タイトル構造）
    for i, staff_contract in enumerate(staff_contracts, 1):
        staff = staff_contract.staff
        
        # 年齢計算（割当開始日時点）
        age = ""
        if staff.birth_date:
            # 割当開始日 = スタッフ契約とクライアント契約が重なる期間の開始日
            assignment_start_date = max(contract.start_date, staff_contract.start_date)
            birth_date = staff.birth_date
            age_years = assignment_start_date.year - birth_date.year
            if (assignment_start_date.month, assignment_start_date.day) < (birth_date.month, birth_date.day):
                age_years -= 1
            
            # 年齢区分による表記
            if age_years < 18:
                age = f"□　60歳以上\n■　60歳未満\n　-　■　45歳以上60歳未満\n　-　■　18歳未満（{age_years}歳）"
            elif 18 <= age_years < 45:
                age = "□　60歳以上\n■　60歳未満\n　-　□　45歳以上60歳未満\n　-　□　18歳未満（　歳）"
            elif 45 <= age_years < 60:
                age = "□　60歳以上\n■　60歳未満\n　-　■　45歳以上60歳未満\n　-　□　18歳未満（　歳）"
            else:  # 60歳以上
                age = "■　60歳以上\n□　60歳未満\n　-　□　45歳以上60歳未満\n　-　□　18歳未満（　歳）"

        # 性別
        gender = ""
        if staff.sex:
            from apps.system.settings.models import Dropdowns
            try:
                gender_dropdown = Dropdowns.objects.get(category='sex', value=str(staff.sex))
                gender = gender_dropdown.name
            except Dropdowns.DoesNotExist:
                gender = str(staff.sex)

        # 雇用形態
        employment_type = ""
        if staff_contract.employment_type:
            if staff_contract.employment_type.is_fixed_term:
                employment_type = "有期"
            else:
                employment_type = "無期"

        # 派遣労働者情報をrowspan形式で追加（3列表示）
        worker_title = f"派遣労働者{i}"
        
        # サブ項目を作成
        rowspan_items = []
        
        # 氏名
        full_name = f"{staff.name_last} {staff.name_first}"
        rowspan_items.append({
            "title": "氏名",
            "text": full_name
        })
        
        # 性別
        rowspan_items.append({
            "title": "性別",
            "text": gender if gender else "-"
        })
        
        # 年齢
        rowspan_items.append({
            "title": "年齢",
            "text": age if age else "-"
        })
        
        # 雇用形態
        rowspan_items.append({
            "title": "雇用形態",
            "text": employment_type if employment_type else "-"
        })
        
        # 協定対象（会社情報の派遣待遇決定方式に基づいて動的に設定）
        agreement_target_text = ""
        if company and company.dispatch_treatment_method == 'agreement':
            agreement_target_text = "■　協定対象　（労使協定方式）\n□　協定対象でない　（均等・均衡方式）"
        else:
            agreement_target_text = "□　協定対象　（労使協定方式）\n■　協定対象でない　（均等・均衡方式）"
        
        rowspan_items.append({
            "title": "協定対象",
            "text": agreement_target_text
        })
        
        # 保険加入状況
        insurance_status_lines = []
        
        # スタッフの給与情報を取得
        payroll = getattr(staff, 'payroll', None)
        
        # 健康保険
        if payroll and payroll.health_insurance_join_date:
            insurance_status_lines.append("健康保険：有")
        else:
            reason = payroll.health_insurance_non_enrollment_reason if payroll else ""
            if reason:
                insurance_status_lines.append(f"健康保険：無　（未加入理由）{reason}")
            else:
                insurance_status_lines.append("健康保険：無")
        
        # 厚生年金
        if payroll and payroll.welfare_pension_join_date:
            insurance_status_lines.append("厚生年金：有")
        else:
            reason = payroll.pension_insurance_non_enrollment_reason if payroll else ""
            if reason:
                insurance_status_lines.append(f"厚生年金：無　（未加入理由）{reason}")
            else:
                insurance_status_lines.append("厚生年金：無")
        
        # 雇用保険
        if payroll and payroll.employment_insurance_join_date:
            insurance_status_lines.append("雇用保険：有")
        else:
            reason = payroll.employment_insurance_non_enrollment_reason if payroll else ""
            if reason:
                insurance_status_lines.append(f"雇用保険：無　（未加入理由）{reason}")
            else:
                insurance_status_lines.append("雇用保険：無")
        
        insurance_status_text = "\n".join(insurance_status_lines)
        rowspan_items.append({
            "title": "保険加入状況",
            "text": insurance_status_text
        })

        # rowspan形式でアイテムを追加
        items.append({
            "title": worker_title,
            "rowspan_items": rowspan_items
        })

    timestamp = issued_at.strftime('%Y%m%d%H%M%S')
    pdf_filename = f"haken_notification_{contract.pk}_{timestamp}.pdf"

    buffer = io.BytesIO()
    generate_table_based_contract_pdf(
        buffer, 
        pdf_title, 
        intro_text, 
        items, 
        watermark_text=watermark_text,
        to_address_lines=to_address_lines,
        from_address_lines=from_address_lines
    )
    pdf_content = buffer.getvalue()
    buffer.close()

    return pdf_content, pdf_filename, pdf_title


def generate_teishokubi_notification_pdf(source_obj, user, issued_at, watermark_text=None):
    """抵触日通知書PDFを生成する"""
    from apps.client.models import ClientDepartment
    pdf_title = "抵触日通知書"
    buffer = io.BytesIO()

    # --- データ取得 ---
    company = Company.objects.first()

    # 通知日の取得
    notice_date = None
    
    if isinstance(source_obj, ClientContract):
        contract = source_obj
        client = contract.client
        haken_info = contract.haken_info
        responsible_person = haken_info.responsible_person_client
        haken_office = haken_info.haken_office
        clash_date = haken_office.haken_jigyosho_teishokubi if haken_office else None
        # 通知日を取得（クライアント組織に設定されている場合）
        notice_date = haken_office.haken_jigyosho_teishokubi_notice_date if haken_office else None
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
        # 通知日を取得（クライアント組織に設定されている場合）
        notice_date = department.haken_jigyosho_teishokubi_notice_date
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
    # 通知日を日本語形式でフォーマット
    notice_date_str = None
    if notice_date:
        notice_date_str = notice_date.strftime('%Y年%m月%d日')
    
    generate_article_based_contract_pdf(
        buffer,
        meta_title=pdf_title,
        to_address_lines=to_address_lines,
        from_address_lines=from_address_lines,
        main_title_text=main_title,
        summary_lines=summary_lines,
        body_title_text=body_title,
        body_items=body_items,
        watermark_text=watermark_text,
        notice_date=notice_date_str
    )

    pdf_content = buffer.getvalue()
    buffer.close()

    timestamp = issued_at.strftime('%Y%m%d%H%M%S')
    pdf_filename = f"client_teishokubi_notification_{source_obj.pk}_{timestamp}.pdf"

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


# 後方互換性のためのエイリアス
# 旧メソッド名から新メソッド名へのエイリアス
generate_dispatch_ledger_pdf = generate_haken_motokanri_pdf
generate_dispatch_destination_ledger_pdf = generate_haken_sakikanri_pdf