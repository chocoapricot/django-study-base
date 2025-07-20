from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from .models import AppLog
from django_currentuser.middleware import get_current_authenticated_user

def log_action(instance, action):
    user = get_current_authenticated_user()
    AppLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action=action,
        model_name=instance.__class__.__name__,
        object_id=str(getattr(instance, 'pk', '')),
        object_repr=str(instance)
    )

@receiver(post_save)
def log_save(sender, instance, created, **kwargs):
    # AppLog自身やmigrate時は除外
    if sender.__name__ == 'AppLog' or sender._meta.app_label == 'sessions':
        return
    if created:
        log_action(instance, 'create')
    else:
        log_action(instance, 'update')

@receiver(post_delete)
def log_delete(sender, instance, **kwargs):
    if sender.__name__ == 'AppLog' or sender._meta.app_label == 'sessions':
        return
    log_action(instance, 'delete')
