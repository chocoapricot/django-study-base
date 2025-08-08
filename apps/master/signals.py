from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django_currentuser.middleware import get_current_user
from apps.system.logs.utils import log_model_action
from .models import Qualification, Skill


@receiver(post_save, sender=Qualification)
def log_qualification_save(sender, instance, created, **kwargs):
    """資格マスタの作成・更新ログ"""
    user = get_current_user()
    action = 'create' if created else 'update'
    log_model_action(user, action, instance, getattr(instance, 'version', None))


@receiver(post_delete, sender=Qualification)
def log_qualification_delete(sender, instance, **kwargs):
    """資格マスタの削除ログ"""
    user = get_current_user()
    log_model_action(user, 'delete', instance)


@receiver(post_save, sender=Skill)
def log_skill_save(sender, instance, created, **kwargs):
    """技能マスタの作成・更新ログ"""
    user = get_current_user()
    action = 'create' if created else 'update'
    log_model_action(user, action, instance, getattr(instance, 'version', None))


@receiver(post_delete, sender=Skill)
def log_skill_delete(sender, instance, **kwargs):
    """技能マスタの削除ログ"""
    user = get_current_user()
    log_model_action(user, 'delete', instance)