from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django_currentuser.middleware import get_current_authenticated_user

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    from apps.system.logs.models import AppLog
    AppLog.objects.create(
        user=user,
        action='login',
        model_name='User',
        object_id=str(user.pk),
        object_repr=f'{user} がログイン',
        version=None
    )

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    from apps.system.logs.models import AppLog
    AppLog.objects.create(
        user=user,
        action='logout',
        model_name='User',
        object_id=str(user.pk),
        object_repr=f'{user} がログアウト',
        version=None
    )
