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

def is_tenant_id_set():
    """セッションにテナントIDが明示的に設定されている（Noneを含む）かどうかを判定する。"""
    return getattr(_thread_locals, 'tenant_id_set', False)

class TenantMiddleware:
    """
    セッションからテナントIDを取得し、スレッドローカルに保存するミドルウェア。
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # リクエスト処理中フラグをセット
        _thread_locals.in_request = True

        try:
            # 1. セッションから current_tenant_id を取得
            tenant_id_set = 'current_tenant_id' in request.session
            tenant_id = request.session.get('current_tenant_id')

            # 2. セッションにない場合でログイン済みの場合は、ユーザー情報から補完を試みる
            # request.user が存在することを確認（Middlewareの順序やテスト対策）
            if not tenant_id and hasattr(request, 'user') and request.user.is_authenticated:
                from apps.company.views import get_current_company
                # 補完処理中はフィルタリングを一時的に無効化する
                _thread_locals.determining_tenant = True
                try:
                    # get_current_company は内部で request.session['current_tenant_id'] を設定する
                    get_current_company(request)
                    tenant_id = request.session.get('current_tenant_id')
                    if tenant_id:
                        tenant_id_set = True
                except Exception:
                    # 補完に失敗してもここでは例外を投げず、フィルタリングに任せる
                    pass
                finally:
                    _thread_locals.determining_tenant = False

            # スレッドローカルを確実に更新
            _thread_locals.tenant_id_set = tenant_id_set
            set_current_tenant_id(tenant_id)

            response = self.get_response(request)
            return response

        finally:
            # リクエスト終了時にクリア（メモリリーク防止、およびテスト環境での汚染防止）
            set_current_tenant_id(None)
            _thread_locals.tenant_id_set = False
            _thread_locals.in_request = False
