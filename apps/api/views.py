import logging
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from apps.api.helpers import fetch_company_info, fetch_zipcode
from apps.master.models import Bank, BankBranch

logger = logging.getLogger('api')

@login_required
def get_company_info(request):
    corporate_number = request.GET.get("corporate_number")
    if corporate_number:
        company_info = fetch_company_info(corporate_number)
        if company_info:
            return JsonResponse({"success": True, "data": company_info})
    return JsonResponse({"success": False, "error": "企業情報の取得に失敗しました。"})

@login_required
def get_zipcode_info(request):
    zipcode = request.GET.get("zipcode")
    if zipcode:
        zipcode_info = fetch_zipcode(zipcode)
        if zipcode_info:
            return JsonResponse({"success": True, "data": zipcode_info})
    return JsonResponse({"success": False, "error": "郵便番号の取得に失敗しました。"})

@login_required
def search_banks(request):
    """銀行を検索する"""
    query = request.GET.get('q', '')
    if not query:
        return JsonResponse([], safe=False)

    banks = Bank.objects.filter(
        Q(name__icontains=query) | Q(bank_code__icontains=query)
    ).values('name', 'bank_code')

    return JsonResponse(list(banks), safe=False)

@login_required
def search_bank_branches(request):
    """銀行の支店を検索する"""
    bank_code = request.GET.get('bank_code', '')
    query = request.GET.get('q', '')

    if not bank_code or not query:
        return JsonResponse([], safe=False)

    branches = BankBranch.objects.filter(
        bank__bank_code=bank_code
    ).filter(
        Q(name__icontains=query) | Q(branch_code__icontains=query)
    ).values('name', 'branch_code')

    return JsonResponse(list(branches), safe=False)


from django.db.models.functions import Concat
from django.db.models import Value

@login_required
def get_client_users(request, client_id):
    """指定されたクライアントIDに紐づく担当者リストを返す"""
    from apps.client.models import ClientUser
    try:
        users = ClientUser.objects.filter(client_id=client_id).select_related('department')
        user_list = [{'id': user.id, 'name': str(user)} for user in users]
        return JsonResponse(user_list, safe=False)
    except Exception as e:
        logger.error(f"Error fetching client users for client_id {client_id}: {e}")
        return JsonResponse([], safe=False)

@login_required
def get_client_haken_offices(request, client_id):
    """指定されたクライアントIDに紐づく派遣先事業所リストを返す"""
    from apps.client.models import ClientDepartment
    try:
        departments = ClientDepartment.objects.filter(
            client_id=client_id,
            is_haken_office=True
        ).order_by('display_order')
        department_list = [{'id': dept.id, 'name': dept.name} for dept in departments]
        return JsonResponse(department_list, safe=False)
    except Exception as e:
        logger.error(f"Error fetching client haken offices for client_id {client_id}: {e}")
        return JsonResponse([], safe=False)

@login_required
def get_client_haken_units(request, client_id):
    """指定されたクライアントIDに紐づく派遣組織単位リストを返す"""
    from apps.client.models import ClientDepartment
    try:
        departments = ClientDepartment.objects.filter(
            client_id=client_id,
            is_haken_unit=True
        ).order_by('display_order')
        department_list = [{'id': dept.id, 'name': dept.name} for dept in departments]
        return JsonResponse(department_list, safe=False)
    except Exception as e:
        logger.error(f"Error fetching client haken units for client_id {client_id}: {e}")
        return JsonResponse([], safe=False)


@login_required
def get_client_department_detail(request, department_id):
    """指定された部署IDの詳細を返す"""
    from apps.client.models import ClientDepartment
    try:
        department = ClientDepartment.objects.get(pk=department_id)
        data = {
            'id': department.id,
            'name': department.name,
            'address': department.address or '',
            'postal_code': department.postal_code or '',
        }
        return JsonResponse({'success': True, 'data': data})
    except ClientDepartment.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Department not found'}, status=404)
    except Exception as e:
        logger.error(f"Error fetching client department detail for department_id {department_id}: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
