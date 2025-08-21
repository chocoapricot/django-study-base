from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.profile.models import StaffProfile
from .models import ConnectStaff, ProfileRequest


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
