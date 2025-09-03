from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import StaffAgreement
from apps.connect.models import ConnectStaffAgree


@receiver(pre_save, sender=StaffAgreement)
def reset_agreement_on_text_change(sender, instance, **kwargs):
    """
    StaffAgreementの文言が変更されたら、関連するConnectStaffAgreeを未同意にする。
    """
    if instance.pk:
        try:
            original = sender.objects.get(pk=instance.pk)
            if original.agreement_text != instance.agreement_text:
                ConnectStaffAgree.objects.filter(staff_agreement=instance).update(is_agreed=False)
        except sender.DoesNotExist:
            pass  # 新規作成時は何もしない
