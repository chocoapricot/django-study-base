from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django_currentuser.middleware import get_current_user
from apps.system.logs.utils import log_model_action
from .models import StaffQualification, StaffSkill, StaffFile, StaffBank, StaffMynumber, StaffContact, StaffInternational, StaffDisability


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


@receiver(post_save, sender=StaffBank)
def log_staff_bank_save(sender, instance, created, **kwargs):
    user = get_current_user()
    action = 'create' if created else 'update'
    log_model_action(user, action, instance, getattr(instance, 'version', None))

@receiver(post_delete, sender=StaffBank)
def log_staff_bank_delete(sender, instance, **kwargs):
    user = get_current_user()
    log_model_action(user, 'delete', instance)


@receiver(post_save, sender=StaffMynumber)
def log_staff_mynumber_save(sender, instance, created, **kwargs):
    user = get_current_user()
    action = 'create' if created else 'update'
    log_model_action(user, action, instance, getattr(instance, 'version', None))

@receiver(post_delete, sender=StaffMynumber)
def log_staff_mynumber_delete(sender, instance, **kwargs):
    user = get_current_user()
    log_model_action(user, 'delete', instance)


@receiver(post_save, sender=StaffContact)
def log_staff_contact_save(sender, instance, created, **kwargs):
    user = get_current_user()
    action = 'create' if created else 'update'
    log_model_action(user, action, instance, getattr(instance, 'version', None))

@receiver(post_delete, sender=StaffContact)
def log_staff_contact_delete(sender, instance, **kwargs):
    user = get_current_user()
    log_model_action(user, 'delete', instance)


@receiver(post_save, sender=StaffInternational)
def log_staff_international_save(sender, instance, created, **kwargs):
    user = get_current_user()
    action = 'create' if created else 'update'
    log_model_action(user, action, instance, getattr(instance, 'version', None))

@receiver(post_delete, sender=StaffInternational)
def log_staff_international_delete(sender, instance, **kwargs):
    user = get_current_user()
    log_model_action(user, 'delete', instance)


@receiver(post_save, sender=StaffDisability)
def log_staff_disability_save(sender, instance, created, **kwargs):
    user = get_current_user()
    action = 'create' if created else 'update'
    log_model_action(user, action, instance, getattr(instance, 'version', None))

@receiver(post_delete, sender=StaffDisability)
def log_staff_disability_delete(sender, instance, **kwargs):
    user = get_current_user()
    log_model_action(user, 'delete', instance)