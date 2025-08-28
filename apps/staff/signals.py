from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django_currentuser.middleware import get_current_user
from apps.system.logs.utils import log_model_action
from .models import StaffQualification, StaffSkill, StaffFile


@receiver(post_save, sender=StaffQualification)
def log_staff_qualification_save(sender, instance, created, **kwargs):
    """スタッフ資格の作成・更新ログ"""
    user = get_current_user()
    action = 'create' if created else 'update'
    log_model_action(user, action, instance, getattr(instance, 'version', None))


@receiver(post_delete, sender=StaffQualification)
def log_staff_qualification_delete(sender, instance, **kwargs):
    """スタッフ資格の削除ログ"""
    user = get_current_user()
    log_model_action(user, 'delete', instance)


@receiver(post_save, sender=StaffSkill)
def log_staff_skill_save(sender, instance, created, **kwargs):
    """スタッフ技能の作成・更新ログ"""
    user = get_current_user()
    action = 'create' if created else 'update'
    log_model_action(user, action, instance, getattr(instance, 'version', None))


@receiver(post_delete, sender=StaffSkill)
def log_staff_skill_delete(sender, instance, **kwargs):
    """スタッフ技能の削除ログ"""
    user = get_current_user()
    log_model_action(user, 'delete', instance)


@receiver(post_save, sender=StaffFile)
def log_staff_file_save(sender, instance, created, **kwargs):
    """スタッフファイルの作成・更新ログ"""
    user = get_current_user()
    action = 'create' if created else 'update'
    log_model_action(user, action, instance, getattr(instance, 'version', None))


@receiver(post_delete, sender=StaffFile)
def log_staff_file_delete(sender, instance, **kwargs):
    """スタッフファイルの削除ログ"""
    user = get_current_user()
    log_model_action(user, 'delete', instance)