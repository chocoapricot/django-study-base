from django.contrib.auth.signals import user_logged_in, user_logged_out
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
