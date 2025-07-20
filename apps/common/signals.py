from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from .models import AppLog
import threading

# スレッドローカルで差分を一時保存
_thread_locals = threading.local()
from django_currentuser.middleware import get_current_authenticated_user

def log_action(instance, action, diff_text=None):
    user = get_current_authenticated_user()
    AppLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action=action,
        model_name=instance.__class__.__name__,
        object_id=str(getattr(instance, 'pk', '')),
        object_repr=diff_text if diff_text else str(instance)
    )

@receiver(pre_save)
def log_pre_save(sender, instance, **kwargs):
    # AppLog自身やmigrate時は除外
    if sender.__name__ == 'AppLog' or sender._meta.app_label == 'sessions':
        return
    if not instance.pk:
        # 新規作成は差分不要
        return
    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        old = None
    diff_list = []
    if old:
        exclude_fields = ['created_at', 'created_by', 'updated_at', 'updated_by', 'id', 'name', 'age']
        for field in instance._meta.fields:
            fname = field.name
            if fname in exclude_fields:
                continue
            old_val = getattr(old, fname, None)
            new_val = getattr(instance, fname, None)
            if old_val != new_val:
                label = getattr(field, 'verbose_name', fname)
                diff_list.append(f"{label}: '{old_val}'→'{new_val}'")
    diff_text = ", ".join(diff_list) if diff_list else None
    if not hasattr(_thread_locals, 'applog_diffs'):
        _thread_locals.applog_diffs = {}
    _thread_locals.applog_diffs[(sender.__name__, instance.pk)] = diff_text


@receiver(post_save)
def log_save(sender, instance, created, **kwargs):
    # AppLog自身やmigrate時は除外
    if sender.__name__ == 'AppLog' or sender._meta.app_label == 'sessions':
        return
    if created:
        log_action(instance, 'create')
    else:
        diff_text = None
        if hasattr(_thread_locals, 'applog_diffs'):
            diff_text = _thread_locals.applog_diffs.pop((sender.__name__, instance.pk), None)
        log_action(instance, 'update', diff_text=diff_text or str(instance))

@receiver(post_delete)
def log_delete(sender, instance, **kwargs):
    if sender.__name__ == 'AppLog' or sender._meta.app_label == 'sessions':
        return
    log_action(instance, 'delete')
