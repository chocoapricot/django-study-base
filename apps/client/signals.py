from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django_currentuser.middleware import get_current_user
from apps.system.logs.utils import log_model_action
from .models import ClientFile


@receiver(post_save, sender=ClientFile)
def log_client_file_save(sender, instance, created, **kwargs):
    """クライアントファイルの作成・更新ログ"""
    user = get_current_user()
    action = 'create' if created else 'update'
    log_model_action(user, action, instance, getattr(instance, 'version', None))


@receiver(post_delete, sender=ClientFile)
def log_client_file_delete(sender, instance, **kwargs):
    """クライアントファイルの削除ログ"""
    user = get_current_user()
    log_model_action(user, 'delete', instance)