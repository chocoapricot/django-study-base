import threading

_thread_locals = threading.local()

def get_current_tenant_id():
    """現在のスレッドに保存されているテナントIDを取得する。"""
    return getattr(_thread_locals, 'tenant_id', None)

def set_current_tenant_id(tenant_id):
    """現在のスレッドにテナントIDを保存する。"""
    _thread_locals.tenant_id = tenant_id

def is_in_request():
    """リクエスト処理中かどうかを判定する。"""
    return getattr(_thread_locals, 'in_request', False)

class TenantMiddleware:
    """
    セッションからテナントIDを取得し、スレッドローカルに保存するミドルウェア。
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.in_request = True
        # セッションから current_tenant_id を取得
        tenant_id = request.session.get('current_tenant_id')
        set_current_tenant_id(tenant_id)

        try:
            response = self.get_response(request)
        finally:
            # リクエスト終了時にクリア（メモリリーク防止）
            set_current_tenant_id(None)
            _thread_locals.in_request = False

        return response
