import sys
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
import threading

# スレッドローカルで差分を一時保存
_thread_locals = threading.local()
from django_currentuser.middleware import get_current_authenticated_user

def log_action(instance, action, diff_text=None):
    user = get_current_authenticated_user()
    
    # 新規作成時にdropdownsフィールドの表示名を含める
    if action == 'create' and not diff_text:
        create_info_list = []
        exclude_fields = ['created_at', 'created_by', 'updated_at', 'updated_by', 'id', 'name', 'age']
        
        for field in instance._meta.fields:
            fname = field.name
            if fname in exclude_fields:
                continue
            val = getattr(instance, fname, None)
            if val is not None and val != '':
                label = getattr(field, 'verbose_name', fname)
                display_val = get_dropdown_display_name(fname, val, instance.__class__.__name__)
                create_info_list.append(f"'{display_val}'")
        
        diff_text = ", ".join(create_info_list) if create_info_list else str(instance)
    
    from apps.system.logs.models import AppLog
    AppLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action=action,
        model_name=instance.__class__.__name__,
        object_id=str(getattr(instance, 'pk', '')),
        object_repr=diff_text if diff_text else str(instance),
        version=getattr(instance, 'version', None)
    )

def get_dropdown_display_name(field_name, value, model_name):
    """dropdownsフィールドの値を表示名に変換する"""
    if value is None:
        return None
    
    # dropdownsを参照するフィールドのマッピング
    dropdown_mappings = {
        'Staff': {
            'sex': 'sex',
            'regist_form_code': 'regist_form'
        },
        'StaffContacted': {
            'contact_type': 'contact_type'
        },
        'Client': {
            'regist_form_client': 'regist_form_client'
        },
        'ClientContacted': {
            'contact_type': 'contact_type'
        }
    }
    
    if model_name in dropdown_mappings and field_name in dropdown_mappings[model_name]:
        category = dropdown_mappings[model_name][field_name]
        try:
            from apps.system.dropdowns.models import Dropdowns
            dropdown = Dropdowns.objects.filter(
                category=category, 
                value=str(value), 
                active=True
            ).first()
            if dropdown:
                return dropdown.name
        except:
            pass
    
    return value

@receiver(pre_save)
def log_pre_save(sender, instance, **kwargs):
    if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
        return
    # AppLog自身、MailLog、migrate時は除外
    if sender.__name__ in ['AppLog', 'MailLog', 'Migration'] or sender._meta.app_label == 'sessions':
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
                
                # dropdownsフィールドの場合は表示名に変換
                old_display = get_dropdown_display_name(fname, old_val, sender.__name__)
                new_display = get_dropdown_display_name(fname, new_val, sender.__name__)
                
                diff_list.append(f"{label}: '{old_display}'→'{new_display}'")
    diff_text = ", ".join(diff_list) if diff_list else None
    if not hasattr(_thread_locals, 'applog_diffs'):
        _thread_locals.applog_diffs = {}
    _thread_locals.applog_diffs[(sender.__name__, instance.pk)] = diff_text


@receiver(post_save)
def log_save(sender, instance, created, **kwargs):
    if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
        return
    # AppLog自身、MailLog、migrate時は除外
    if sender.__name__ in ['AppLog', 'MailLog', 'Migration'] or sender._meta.app_label == 'sessions':
        return
    if created:
        log_action(instance, 'create')
    else:
        diff_text = None
        if hasattr(_thread_locals, 'applog_diffs'):
            diff_text = _thread_locals.applog_diffs.pop((sender.__name__, instance.pk), None)
        # 実際に変更があった場合のみログを記録
        if diff_text:
            log_action(instance, 'update', diff_text=diff_text)

@receiver(post_delete)
def log_delete(sender, instance, **kwargs):
    if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
        return
    # AppLog自身、MailLog、migrate時は除外
    if sender.__name__ in ['AppLog', 'MailLog', 'Migration'] or sender._meta.app_label == 'sessions':
        return
    log_action(instance, 'delete')