from .models import AccessLog

class AccessLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # /admin/ へのアクセスはログに記録しない
        if request.path.startswith('/admin/'):
            return self.get_response(request)

        response = self.get_response(request)

        # ログを作成
        AccessLog.objects.create(
            user=request.user if request.user.is_authenticated else None,
            url=request.path,
        )

        return response
