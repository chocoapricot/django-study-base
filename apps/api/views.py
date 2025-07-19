def get_company_info(request):
    corporate_number = request.GET.get("corporate_number")
    if corporate_number:
        company_info = fetch_company_info(corporate_number)
        if company_info:
            return JsonResponse({"success": True, "data": company_info})
    return JsonResponse({"success": False, "error": "企業情報の取得に失敗しました。"})
def get_zipcode_info(request):
    zipcode = request.GET.get("zipcode")
    # logger.error(zipcode)
    if zipcode:
        zipcode_info = fetch_zipcode(zipcode)
        # logger.error(zipcode_info)
        if zipcode_info:
            return JsonResponse({"success": True, "data": zipcode_info})
    return JsonResponse({"success": False, "error": "郵便番号の取得に失敗しました。"})

import logging
from django.http import JsonResponse
from apps.api.helpers import fetch_company_info, fetch_zipcode  # API呼び出し関数をインポート
from django.contrib.auth.decorators import login_required

# ロガーの作成
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
    # logger.error(zipcode)
    if zipcode:
        zipcode_info = fetch_zipcode(zipcode)
        # logger.error(zipcode_info)
        if zipcode_info:
            return JsonResponse({"success": True, "data": zipcode_info})
    return JsonResponse({"success": False, "error": "郵便番号の取得に失敗しました。"})
