from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.staff.models_other import StaffFlag
from apps.client.models import ClientFlag
from apps.contract.models import ContractClientFlag, ContractStaffFlag, ContractAssignmentFlag
from django.urls import reverse

@login_required
def flag_list(request):
    """
    全てのエンティティのフラッグをまとめて表示するビュー
    """
    staff_flags = StaffFlag.objects.select_related('staff', 'flag_status', 'company_user', 'company_department')
    client_flags = ClientFlag.objects.select_related('client', 'flag_status', 'company_user', 'company_department')
    contract_client_flags = ContractClientFlag.objects.select_related('client_contract', 'client_contract__client', 'flag_status', 'company_user', 'company_department')
    contract_staff_flags = ContractStaffFlag.objects.select_related('staff_contract', 'staff_contract__staff', 'flag_status', 'company_user', 'company_department')
    contract_assignment_flags = ContractAssignmentFlag.objects.select_related('contract_assignment', 'contract_assignment__client_contract', 'contract_assignment__staff_contract', 'flag_status', 'company_user', 'company_department')

    results = []

    for f in staff_flags:
        results.append({
            'type': 'スタッフ',
            'entity_name': f"{f.staff.name_last} {f.staff.name_first}",
            'entity_url': reverse('staff:staff_detail', args=[f.staff.pk]),
            'flag': f,
            'updated_at': f.updated_at,
            'update_url': reverse('staff:staff_flag_update', args=[f.pk])
        })

    for f in client_flags:
        results.append({
            'type': 'クライアント',
            'entity_name': f.client.name,
            'entity_url': reverse('client:client_detail', args=[f.client.pk]),
            'flag': f,
            'updated_at': f.updated_at,
            'update_url': reverse('client:client_flag_update', args=[f.pk])
        })

    for f in contract_client_flags:
        results.append({
            'type': 'クライアント契約',
            'entity_name': str(f.client_contract),
            'entity_url': reverse('contract:client_contract_detail', args=[f.client_contract.pk]),
            'flag': f,
            'updated_at': f.updated_at,
            'update_url': reverse('contract:client_contract_flag_update', args=[f.pk])
        })

    for f in contract_staff_flags:
        results.append({
            'type': 'スタッフ契約',
            'entity_name': str(f.staff_contract),
            'entity_url': reverse('contract:staff_contract_detail', args=[f.staff_contract.pk]),
            'flag': f,
            'updated_at': f.updated_at,
            'update_url': reverse('contract:staff_contract_flag_update', args=[f.pk])
        })

    for f in contract_assignment_flags:
        results.append({
            'type': '契約アサイン',
            'entity_name': str(f.contract_assignment),
            'entity_url': reverse('contract:contract_assignment_detail', args=[f.contract_assignment.pk]),
            'flag': f,
            'updated_at': f.updated_at,
            'update_url': reverse('contract:contract_assignment_flag_update', args=[f.pk])
        })

    results.sort(key=lambda x: x['updated_at'], reverse=True)

    context = {
        'flags': results,
    }

    return render(request, 'system/flags/flag_list.html', context)
