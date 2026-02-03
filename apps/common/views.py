# apps/common/views.py
import json
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt # Ajax POSTなのでCSRFトークンを免除（本番環境ではより安全な方法を検討）
@require_POST
def set_sidebar_state(request):
    """
    サイドバーの開閉状態をセッションに保存するビュー
    """
    try:
        data = json.loads(request.body)
        is_collapsed = data.get('is_collapsed')

        if is_collapsed is None or not isinstance(is_collapsed, bool):
            return HttpResponseBadRequest('Invalid data: "is_collapsed" must be a boolean.')

        request.session['is_sidebar_collapsed'] = is_collapsed
        return JsonResponse({'status': 'ok'})
    except json.JSONDecodeError:
        return HttpResponseBadRequest('Invalid JSON')