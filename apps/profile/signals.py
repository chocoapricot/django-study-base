from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.profile.models import ProfileMynumber, StaffProfileInternational, StaffProfileBank, StaffProfileDisability
from apps.connect.models import ConnectStaff, MynumberRequest, ConnectInternationalRequest, BankRequest, DisabilityRequest


@receiver(post_save, sender=StaffProfileBank)
def create_or_update_bank_request(sender, instance, **kwargs):
    """
    StaffProfileBankが作成または更新されたときに、関連するすべての有効な
    ConnectStaffに対してBankRequestを作成または更新します。
    """
    user = instance.user

    # ユーザーに関連する承認済みのConnectStaffを取得
    approved_connections = ConnectStaff.objects.filter(
        email=user.email,
        status='approved'
    )

    # このユーザーの既存のBankRequestをすべて削除
    BankRequest.objects.filter(
        staff_bank_profile__user=user
    ).delete()

    # 承認済みの接続ごとに新しいBankRequestを作成
    for connection in approved_connections:
        BankRequest.objects.create(
            connect_staff=connection,
            staff_bank_profile=instance,
            status='pending'
        )


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


@receiver(post_save, sender=StaffProfileInternational)
def create_or_update_international_request(sender, instance, **kwargs):
    """
    StaffProfileInternationalが作成または更新されたときに、関連するすべての有効な
    ConnectStaffに対してConnectInternationalRequestを作成または更新します。
    """
    user = instance.user

    # ユーザーに関連する承認済みのConnectStaffを取得
    approved_connections = ConnectStaff.objects.filter(
        email=user.email,
        status='approved'
    )

    # このユーザーの既存のConnectInternationalRequestをすべて削除
    ConnectInternationalRequest.objects.filter(
        profile_international__user=user
    ).delete()

    # 承認済みの接続ごとに新しいConnectInternationalRequestを作成
    for connection in approved_connections:
        ConnectInternationalRequest.objects.create(
            connect_staff=connection,
            profile_international=instance,
            status='pending'
        )


@receiver(post_save, sender=StaffProfileDisability)
def create_or_update_disability_request(sender, instance, **kwargs):
    """
    StaffProfileDisabilityが作成または更新されたときに、関連するすべての有効な
    ConnectStaffに対してDisabilityRequestを作成または更新します。
    """
    user = instance.user

    # ユーザーに関連する承認済みのConnectStaffを取得
    approved_connections = ConnectStaff.objects.filter(
        email=user.email,
        status='approved'
    )

    # このユーザーの既存のDisabilityRequestをすべて削除
    DisabilityRequest.objects.filter(
        profile_disability__user=user
    ).delete()

    # 承認済みの接続ごとに新しいDisabilityRequestを作成
    for connection in approved_connections:
        DisabilityRequest.objects.create(
            connect_staff=connection,
            profile_disability=instance,
            status='pending'
        )
