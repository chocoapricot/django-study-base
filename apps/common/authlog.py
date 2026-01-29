from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django_currentuser.middleware import get_current_authenticated_user


def get_client_ip(request):
    """クライアントのIPアドレスを取得"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    from apps.system.logs.models import AppLog
    
    ip_address = get_client_ip(request)
    
    AppLog.objects.create(
        user=user,
        action='login',
        model_name='User',
        object_id=str(user.pk),
        object_repr=f'{user} がログイン (IP: {ip_address})',
        version=None
    )

    # ログイン時にテナント情報をセッションに初期化
    from apps.company.views import get_current_company
    try:
        # get_current_company は内部で request.session['current_tenant_id'] を設定する
        get_current_company(request)
    except Exception:
        # 会社情報が見つからない場合などは無視する
        pass


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    from apps.system.logs.models import AppLog
    
    ip_address = get_client_ip(request)
    
    AppLog.objects.create(
        user=user,
        action='logout',
        model_name='User',
        object_id=str(user.pk),
        object_repr=f'{user} がログアウト (IP: {ip_address})',
        version=None
    )

@receiver(user_login_failed)
def log_user_login_failed(sender, request, credentials, **kwargs):
    from apps.system.logs.models import AppLog
    from django.contrib.auth import get_user_model

    ip_address = get_client_ip(request)
    # allauth can use 'email' or 'username' in credentials
    username = credentials.get('username') or credentials.get('email')

    User = get_user_model()
    user = None
    if username:
        # Try to find user by username or email. This is best-effort.
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            try:
                user = User.objects.get(email=username)
            except User.DoesNotExist:
                user = None

    AppLog.objects.create(
        user=user,  # This can be None if the user is not found
        action='login_failed',
        model_name='User',
        object_id=str(user.pk) if user else '0',
        object_repr=f"'{username}' のログインに失敗 (IP: {ip_address})",
        version=None
    )