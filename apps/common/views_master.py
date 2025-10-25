from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator


@login_required
def master_select(request):
    """マスター選択画面（汎用）"""
    search_query = request.GET.get('q', '')
    master_type = request.GET.get('type', '')
    
    # マスタータイプに応じてデータを取得（有効なもののみ）
    if master_type == 'business_content':
        from apps.master.models import PhraseTemplate
        from apps.common.constants import Constants
        items = PhraseTemplate.objects.filter(
            is_active=True, 
            title__key=Constants.PHRASE_TEMPLATE_TITLE.CONTRACT_BUSINESS_CONTENT,
            title__is_active=True
        )
        modal_title = '業務内容を選択'
    elif master_type == 'responsibility_degree':
        from apps.master.models import PhraseTemplate
        from apps.common.constants import Constants
        items = PhraseTemplate.objects.filter(
            is_active=True, 
            title__key=Constants.PHRASE_TEMPLATE_TITLE.HAKEN_RESPONSIBILITY_DEGREE,
            title__is_active=True
        )
        modal_title = '責任の程度を選択'
    elif master_type == 'haken_teishokubi_exempt':
        from apps.master.models import PhraseTemplate
        from apps.common.constants import Constants
        items = PhraseTemplate.objects.filter(
            is_active=True, 
            title__key=Constants.PHRASE_TEMPLATE_TITLE.HAKEN_TEISHOKUBI_EXEMPT,
            title__is_active=True
        )
        modal_title = '派遣抵触日制限外を選択'
    elif master_type == 'health_insurance_non_enrollment':
        from apps.master.models import PhraseTemplate
        from apps.common.constants import Constants
        items = PhraseTemplate.objects.filter(
            is_active=True, 
            title__key=Constants.PHRASE_TEMPLATE_TITLE.STAFF_NO_HEALTH_INSURANCE,
            title__is_active=True
        )
        modal_title = '健康保険非加入理由を選択'
    elif master_type == 'pension_insurance_non_enrollment':
        from apps.master.models import PhraseTemplate
        from apps.common.constants import Constants
        items = PhraseTemplate.objects.filter(
            is_active=True, 
            title__key=Constants.PHRASE_TEMPLATE_TITLE.STAFF_NO_PENSION_INSURANCE,
            title__is_active=True
        )
        modal_title = '厚生年金非加入理由を選択'
    elif master_type == 'employment_insurance_non_enrollment':
        from apps.master.models import PhraseTemplate
        from apps.common.constants import Constants
        items = PhraseTemplate.objects.filter(
            is_active=True, 
            title__key=Constants.PHRASE_TEMPLATE_TITLE.STAFF_NO_EMPLOYMENT_INSURANCE,
            title__is_active=True
        )
        modal_title = '雇用保険非加入理由を選択'
    else:
        items = []
        modal_title = 'マスター選択'
    
    if search_query:
        items = items.filter(content__icontains=search_query)
    
    # 表示順で並び替え（モデルのMeta.orderingを使用）
    items = items.order_by('display_order')
    
    # ページネーション
    paginator = Paginator(items, 20)
    page = request.GET.get('page')
    items_page = paginator.get_page(page)
    
    context = {
        'page_obj': items_page,
        'search_query': search_query,
        'master_type': master_type,
        'modal_title': modal_title,
    }

    return render(request, 'common/_master_select_modal.html', context)