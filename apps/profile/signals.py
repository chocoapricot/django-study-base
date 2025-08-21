from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.profile.models import ProfileMynumber
from apps.connect.models import ConnectStaff, MynumberRequest


@receiver(post_save, sender=ProfileMynumber)
def create_or_update_mynumber_request(sender, instance, **kwargs):
    """
    ProfileMynumberが作成または更新されたときに、関連するすべての有効な
    ConnectStaffに対してMynumberRequestを作成または更新します。
    既存のレコードは一度すべて削除されます。
    """
    user = instance.user

    # ユーザーに関連する承認済みのConnectStaffを取得
    approved_connections = ConnectStaff.objects.filter(
        email=user.email,
        status='approved'
    )

    # このユーザーの既存のMynumberRequestをすべて削除
    MynumberRequest.objects.filter(
        profile_mynumber__user=user
    ).delete()

    # 承認済みの接続ごとに新しいMynumberRequestを作成
    for connection in approved_connections:
        MynumberRequest.objects.create(
            connect_staff=connection,
            profile_mynumber=instance,
            status='pending'
        )
