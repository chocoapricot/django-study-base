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
