from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver

from apps.profile.models import StaffProfile
from .models import ConnectStaff, ProfileRequest, ConnectStaffAgree


@receiver(post_save, sender=StaffProfile)
def create_or_update_profile_request(sender, instance, **kwargs):
    """
    StaffProfileが保存されたときに、関連するConnectStaffに対して
    ProfileRequestを作成または更新します。
    """
    try:
        user_email = instance.user.email
    except AttributeError:
        # userが紐付いていない場合は何もしない
        return

    # 承認済みの接続を取得
    connections = ConnectStaff.objects.filter(email=user_email, status='approved')

    for conn in connections:
        # 既存のリクエストを削除
        ProfileRequest.objects.filter(connect_staff=conn, staff_profile=instance).delete()
        # 新しいリクエストを作成
        ProfileRequest.objects.create(
            connect_staff=conn,
            staff_profile=instance,
            status='pending'
        )


@receiver(pre_save, sender=ConnectStaff)
def delete_agreement_on_unapprove(sender, instance, **kwargs):
    """
    ConnectStaffの承認が解除されたら、関連するConnectStaffAgreeを削除する。
    """
    if instance.pk:
        try:
            original = sender.objects.get(pk=instance.pk)
            if original.status == 'approved' and instance.status != 'approved':
                ConnectStaffAgree.objects.filter(
                    email=instance.email,
                    corporate_number=instance.corporate_number
                ).delete()
        except sender.DoesNotExist:
            pass  # 新規作成時は何もしない


@receiver(post_delete, sender=ConnectStaff)
def delete_agreement_on_disconnect(sender, instance, **kwargs):
    """
    ConnectStaffが削除されたら、関連するConnectStaffAgreeを削除する。
    """
    ConnectStaffAgree.objects.filter(
        email=instance.email,
        corporate_number=instance.corporate_number
    ).delete()
