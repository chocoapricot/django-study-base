from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from apps.connect.utils import check_and_grant_permissions_for_email, check_and_grant_client_permissions_for_email

User = get_user_model()


@receiver(post_save, sender=User)
def check_connection_requests_on_user_creation(sender, instance, created, **kwargs):
    """ユーザー作成時に接続申請をチェックして権限を付与"""
    if created and instance.email:
        # スタッフ接続申請をチェック
        check_and_grant_permissions_for_email(instance.email)
        
        # クライアント接続申請をチェック
        check_and_grant_client_permissions_for_email(instance.email)