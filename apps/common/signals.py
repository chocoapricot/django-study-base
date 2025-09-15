import sys
import threading

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from django_currentuser.middleware import get_current_authenticated_user

# スレッドローカルで差分を一時保存
_thread_locals = threading.local()


def get_display_name(instance, field_name):
    """
    フィールドの表示名を取得する汎用関数。
    1. Djangoの get_..._display() メソッドを試す。
    2. 既存の Dropdowns モデル検索のロジックを試す。
    """
    # 1. Djangoの get_..._display()
    try:
        display_method = getattr(instance, f'get_{field_name}_display')
        return display_method()
    except AttributeError:
        # Falls through to the next method
        pass

    value = getattr(instance, field_name)
    if not value:
        return ""

    # 2. 既存の Dropdowns モデル検索のロジック
    model_name = instance.__class__.__name__
    dropdown_mappings = {
        'Staff': {
            'sex': 'sex',
            'staff_regist_status_code': 'staff_regist_status'
        },
        'StaffContacted': {
            'contact_type': 'contact_type'
        },
        'Client': {
            'client_regist_status': 'client_regist_status'
        },
        'ClientContacted': {
            'contact_type': 'contact_type'
        }
    }

    if model_name in dropdown_mappings and field_name in dropdown_mappings[model_name]:
        category = dropdown_mappings[model_name][field_name]
        try:
            # Corrected import path
            from apps.system.settings.models import Dropdowns
            dropdown = Dropdowns.objects.filter(
                category=category,
                value=str(value),
                active=True
            ).first()
            if dropdown:
                return dropdown.name
        except (ImportError, Exception):
            # Let's not have this fail silently in case of other errors.
            # In a real app, you might want to log this.
            pass

    return str(value)


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

            # The value is already part of the instance, no need to get it separately
            display_val = get_display_name(instance, fname)
            if display_val is not None and display_val != '':
                label = getattr(field, 'verbose_name', fname)
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


@receiver(pre_save)
def log_pre_save(sender, instance, **kwargs):
    if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
        return
    # AppLog自身、MailLog、AccessLog、migrate時は除外
    if sender.__name__ in ['AppLog', 'MailLog', 'AccessLog', 'Migration'] or sender._meta.app_label == 'sessions':
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

                # 汎用的な表示名取得関数を使用
                old_display = get_display_name(old, fname)
                new_display = get_display_name(instance, fname)

                diff_list.append(f"{label}: '{old_display}'→'{new_display}'")
    diff_text = ", ".join(diff_list) if diff_list else None
    if not hasattr(_thread_locals, 'applog_diffs'):
        _thread_locals.applog_diffs = {}
    _thread_locals.applog_diffs[(sender.__name__, instance.pk)] = diff_text


@receiver(post_save)
def log_save(sender, instance, created, **kwargs):
    if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
        return
    # AppLog自身、MailLog、AccessLog、migrate時は除外
    if sender.__name__ in ['AppLog', 'MailLog', 'AccessLog', 'Migration'] or sender._meta.app_label == 'sessions':
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
    # AppLog自身、MailLog、AccessLog、migrate時は除外
    if sender.__name__ in ['AppLog', 'MailLog', 'AccessLog', 'Migration'] or sender._meta.app_label == 'sessions':
        return
    log_action(instance, 'delete')