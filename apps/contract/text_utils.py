from .utils import get_contract_pdf_title, format_worktime_pattern
from apps.system.settings.models import Dropdowns
from apps.company.models import Company
import re

def generate_staff_contract_full_text(contract):
    """
    スタッフ契約（雇用契約書兼労働条件通知書）のテキスト全文を生成する
    PDF生成ロジック(utils.generate_contract_pdf_content)と一致させる
    """
    
    # 1. タイトル
    pdf_title = get_contract_pdf_title(contract)
    
    # 2. 基本情報項目の構築 (items)
    # utils.pyの394行目付近のロジック
    start_date_str = contract.start_date.strftime('%Y年%m月%d日')
    end_date_str = contract.end_date.strftime('%Y年%m月%d日') if contract.end_date else "無期限"
    contract_period = f"{start_date_str}　～　{end_date_str}"
    
    pay_unit_name = ""
    if contract.pay_unit:
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
    ]
    
    worktime_text = format_worktime_pattern(contract.worktime_pattern)
    if worktime_text:
        items.append({"title": "就業時間", "text": worktime_text})
    
    items.append({"title": "備考", "text": str(contract.notes or "")})

    # 3. 契約パターンの適用 (Preamble, Body Terms, Postamble)
    intro_text = ""
    postamble_text = ""
    
    if contract.contract_pattern:
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
            intro_text = "\n\n".join(preamble_text_parts)

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

    # 4. テキスト構築
    lines = []
    
    # ヘッダー
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"【{pdf_title}】")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    
    if intro_text:
        lines.append(intro_text)
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("契約内容")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    for item in items:
        lines.append(f"■ {item['title']}")
        lines.append(item['text'])
        lines.append("")

    if postamble_text:
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("")
        lines.append(postamble_text)
        
    return "\n".join(lines)


def generate_assignment_employment_conditions_full_text(assignment):
    """
    就業条件明示書のテキスト全文を生成する
    PDF生成ロジック(utils.generate_employment_conditions_pdf)と一致させる
    Args:
        assignment: ContractAssignmentインスタンス
    """
    from .utils import (
        format_worktime_pattern, 
        format_client_user_info, 
        format_company_user_info
    )
    
    client_contract = assignment.client_contract
    staff_contract = assignment.staff_contract
    staff = staff_contract.staff
    
    # 会社名を取得
    try:
        company = Company.objects.first()
        company_name = company.name if company else "会社名"
    except Exception:
        company_name = "会社名"
        
    # 前文
    preamble_text = f"""{company_name}（以下「乙」という）は、{staff.name_last} {staff.name_first}（以下「甲」という）に対し、労働者派遣法に基づき、労働者を派遣する。労働者派遣法第34条に基づき就業条件明示書を交付する。就業条件等に変更がある場合は、事前に通知する。"""
    
    items = []
    
    # 基本情報
    items.append({"title": "契約番号", "text": client_contract.contract_number or "-"})
    items.append({"title": "契約名", "text": client_contract.contract_name})
    items.append({"title": "派遣労働者氏名", "text": f"{staff.name_last} {staff.name_first}"})
    items.append({"title": "派遣先", "text": client_contract.client.name})
    
    # 派遣期間
    start_date = assignment.assignment_start_date or client_contract.start_date
    end_date = assignment.assignment_end_date or client_contract.end_date
    start_str = start_date.strftime('%Y年%m月%d日') if start_date else ""
    end_str = end_date.strftime('%Y年%m月%d日') if end_date else "期間の定めなし"
    items.append({"title": "派遣期間", "text": f"{start_str} ～ {end_str}"})
    
    # 契約金額
    pay_unit_name = ""
    if staff_contract.pay_unit:
        try:
            dropdown = Dropdowns.objects.get(category='pay_unit', value=staff_contract.pay_unit)
            pay_unit_name = dropdown.name
        except Dropdowns.DoesNotExist:
            pass

    contract_amount_text = "N/A"
    if staff_contract.contract_amount is not None:
        contract_amount_text = f"{staff_contract.contract_amount:,}円"
        if pay_unit_name:
            contract_amount_text = f"{pay_unit_name} {contract_amount_text}"
            
    items.append({"title": "契約金額", "text": contract_amount_text})
    
    # 派遣先事業所の名称及び所在地
    if hasattr(client_contract, 'haken_info') and client_contract.haken_info and client_contract.haken_info.haken_office:
        office = client_contract.haken_info.haken_office
        client_name = office.client.name
        office_name = office.name
        
        teishokubi_text = ""
        if office.haken_jigyosho_teishokubi:
            teishokubi_text = f"（抵触日：{office.haken_jigyosho_teishokubi.strftime('%Y年%m月%d日')}）"
        
        postal = f"〒{office.postal_code}" if office.postal_code else ""
        address = office.address or ""
        phone = f"電話番号：{office.phone_number}" if office.phone_number else ""

        line1 = f"{client_name}　{office_name}{teishokubi_text}"
        line2 = f"{postal} {address} {phone}".strip()
        haken_office_text = f"{line1}\n{line2}" if line2 else line1
        items.append({"title": "派遣先事業所の名称及び所在地", "text": haken_office_text})
    else:
        items.append({"title": "派遣先事業所の名称及び所在地", "text": "-"})

    # 就業場所
    if staff_contract.work_location:
         items.append({"title": "就業場所", "text": staff_contract.work_location})
         
    # 組織単位
    if hasattr(client_contract, 'haken_info') and client_contract.haken_info and client_contract.haken_info.haken_unit:
        unit = client_contract.haken_info.haken_unit
        unit_name = unit.name
        
        details = []
        if unit.haken_unit_manager_title:
            details.append(f"組織の長の職名：{unit.haken_unit_manager_title}")
            
        # 個人抵触日
        try:
            from apps.contract.models import StaffContractTeishokubi
            staff_teishokubi = StaffContractTeishokubi.objects.filter(
                staff_email=staff.email,
                organization_name=unit_name
            ).first()
            if staff_teishokubi and staff_teishokubi.conflict_date:
                conflict_date_str = staff_teishokubi.conflict_date.strftime('%Y年%m月%d日')
                details.append(f"抵触日：{conflict_date_str}")
        except Exception:
            pass
            
        if details:
            detail_text = "、".join(details)
            haken_unit_text = f"{unit_name}　（{detail_text}）"
        else:
            haken_unit_text = unit_name
        items.append({"title": "組織単位", "text": haken_unit_text})
    else:
        items.append({"title": "組織単位", "text": "-"})

    # 業務内容
    business_content = ""
    if staff_contract.business_content:
        business_content = staff_contract.business_content
    elif client_contract.business_content:
        business_content = client_contract.business_content
    if business_content:
        items.append({"title": "業務内容", "text": business_content})

    # 責任の程度
    if hasattr(client_contract, 'haken_info') and client_contract.haken_info and client_contract.haken_info.responsibility_degree:
        items.append({"title": "責任の程度", "text": client_contract.haken_info.responsibility_degree})

    # 就業時間
    worktime_text = format_worktime_pattern(staff_contract.worktime_pattern)
    if worktime_text:
        items.append({"title": "就業時間", "text": worktime_text})

    # 派遣先指揮命令者
    if hasattr(client_contract, 'haken_info') and client_contract.haken_info and client_contract.haken_info.commander:
        items.append({"title": "派遣先指揮命令者", "text": format_client_user_info(client_contract.haken_info.commander, default_text="-")})

    # 派遣元責任者
    if hasattr(client_contract, 'haken_info') and client_contract.haken_info and client_contract.haken_info.responsible_person_company:
        company_responsible = format_company_user_info(client_contract.haken_info.responsible_person_company, with_phone=True, default_text="-")
        is_manu = client_contract.job_category and client_contract.job_category.is_manufacturing_dispatch
        title = "製造業務専門派遣元責任者" if is_manu else "派遣元責任者"
        items.append({"title": title, "text": company_responsible})

    # 派遣先責任者
    if hasattr(client_contract, 'haken_info') and client_contract.haken_info and client_contract.haken_info.responsible_person_client:
        client_responsible = format_client_user_info(client_contract.haken_info.responsible_person_client, with_phone=True, default_text="-")
        is_manu = client_contract.job_category and client_contract.job_category.is_manufacturing_dispatch
        title = "製造業務専門派遣先責任者" if is_manu else "派遣先責任者"
        items.append({"title": title, "text": client_responsible})

    # 派遣元苦情申出先
    if hasattr(client_contract, 'haken_info') and client_contract.haken_info and client_contract.haken_info.complaint_officer_company:
        officer = format_company_user_info(client_contract.haken_info.complaint_officer_company, with_phone=True, default_text="-")
        items.append({"title": "派遣元苦情申出先", "text": officer})

    # 派遣先苦情申出先
    if hasattr(client_contract, 'haken_info') and client_contract.haken_info and client_contract.haken_info.complaint_officer_client:
        officer = format_client_user_info(client_contract.haken_info.complaint_officer_client, with_phone=True, default_text="-")
        items.append({"title": "派遣先苦情申出先", "text": officer})


    # 契約パターンの文言
    if staff_contract.contract_pattern:
        contract_terms = staff_contract.contract_pattern.terms.filter(display_position=2).order_by('display_order')
        for term in contract_terms:
            term_text = term.contract_terms
            term_text = term_text.replace('{{staff_name}}', f"{staff.name_last} {staff.name_first}")
            term_text = term_text.replace('{{company_name}}', company_name)
            
            if staff_contract.start_date:
                term_text = term_text.replace('{{start_date}}', staff_contract.start_date.strftime('%Y年%m月%d日'))
            if staff_contract.end_date:
                term_text = term_text.replace('{{end_date}}', staff_contract.end_date.strftime('%Y年%m月%d日'))
            else:
                term_text = term_text.replace('{{end_date}}', '期間の定めなし')
                
            if staff_contract.contract_amount:
                term_text = term_text.replace('{{contract_amount}}', f"{staff_contract.contract_amount:,.0f}円")
            
            if staff_contract.business_content:
                term_text = term_text.replace('{{business_content}}', staff_contract.business_content)
                
            items.append({"title": term.contract_clause, "text": term_text})

    # テキスト構築
    lines = []
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("【就業条件明示書】")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("")
    
    if preamble_text:
        lines.append(preamble_text)
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("契約内容")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    for item in items:
        lines.append(f"■ {item['title']}")
        lines.append(item['text'])
        lines.append("")
    
    return "\n".join(lines)
