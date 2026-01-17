from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from .models import ConnectStaff, ConnectClient
from apps.profile.models import StaffProfile, StaffProfileMynumber, StaffProfileBank, StaffProfileContact, StaffProfileInternational, StaffProfileDisability
from apps.contract.models import StaffContract, ClientContract

User = get_user_model()


def grant_profile_permissions(user):
    """ユーザーにプロファイル関連の権限を付与"""
    try:
        models_to_grant = [
            StaffProfile,
            StaffProfileMynumber,
            StaffProfileBank,
            StaffProfileContact,
            StaffProfileInternational,
            StaffProfileDisability,
        ]

        for model_class in models_to_grant:
            content_type = ContentType.objects.get_for_model(model_class)
            permissions = Permission.objects.filter(content_type=content_type)
            user.user_permissions.add(*permissions)

        return True

    except Exception as e:
        print(f"[ERROR] プロファイル権限付与エラー: {e}")
        return False


def grant_connect_permissions(user):
    """ユーザーに接続関連の権限を付与"""
    try:
        # ConnectStaffモデルのContentTypeを取得
        content_type = ContentType.objects.get_for_model(ConnectStaff)
        
        # 必要な権限を取得
        permissions = Permission.objects.filter(
            content_type=content_type,
            codename__in=['view_connectstaff', 'change_connectstaff']
        )
        
        # 権限を付与
        for permission in permissions:
            user.user_permissions.add(permission)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] 権限付与エラー: {e}")
        return False


def check_and_grant_permissions_for_email(email):
    """メールアドレスに対する接続申請があるかチェックし、権限を付与"""
    try:
        # 該当するユーザーを取得
        user = User.objects.get(email=email)
        
        # 該当するメールアドレスの接続申請があるかチェック
        connections = ConnectStaff.objects.filter(email=email)
        
        if connections.exists():
            # 接続申請がある場合、権限を付与
            grant_connect_permissions(user)
            
            # 接続申請のログを出力
            for connection in connections:
                print(f"[INFO] 接続申請発見: {connection.corporate_number} -> {email}")
            
            return True
        else:
            return False
            
    except User.DoesNotExist:
        return False
    except Exception as e:
        #print(f"[ERROR] 権限チェックエラー: {e}")
        return False


def grant_permissions_on_connection_request(email):
    """接続依頼時に既存ユーザーがいる場合は権限を付与"""
    try:
        user = User.objects.get(email=email)
        grant_connect_permissions(user)
        return True
    except User.DoesNotExist:
        return False
    except Exception as e:
        print(f"[ERROR] 接続依頼時の権限付与エラー: {e}")
        return False


def grant_client_connect_permissions(user):
    """ユーザーにクライアント接続関連の権限を付与"""
    try:
        # ConnectClientモデルのContentTypeを取得
        content_type = ContentType.objects.get_for_model(ConnectClient)

        # 必要な権限を取得
        permissions = Permission.objects.filter(
            content_type=content_type,
            codename__in=['view_connectclient', 'change_connectclient']
        )

        # 権限を付与
        for permission in permissions:
            user.user_permissions.add(permission)
        
        return True

    except Exception as e:
        print(f"[ERROR] クライアント権限付与エラー: {e}")
        return False


def check_and_grant_client_permissions_for_email(email):
    """メールアドレスに対するクライアント接続申請があるかチェックし、権限を付与"""
    try:
        # 該当するユーザーを取得
        user = User.objects.get(email=email)
        
        # 該当するメールアドレスのクライアント接続申請があるかチェック
        connections = ConnectClient.objects.filter(email=email)
        
        if connections.exists():
            # 接続申請がある場合、権限を付与
            grant_client_connect_permissions(user)
            
            # 接続申請のログを出力
            for connection in connections:
                print(f"[INFO] クライアント接続申請発見: {connection.corporate_number} -> {email}")
            
            return True
        else:
            return False
            
    except User.DoesNotExist:
        #print(f"[INFO] ユーザー {email} は存在しません")
        return False
    except Exception as e:
        print(f"[ERROR] クライアント権限チェックエラー: {e}")
        return False


def grant_client_permissions_on_connection_request(email):
    """クライアント接続依頼時に既存ユーザーがいる場合は権限を付与"""
    try:
        user = User.objects.get(email=email)
        grant_client_connect_permissions(user)
        return True
    except User.DoesNotExist:
        return False
    except Exception as e:
        print(f"[ERROR] クライアント接続依頼時の権限付付与エラー: {e}")
        return False


def grant_staff_contract_confirmation_permission(user):
    """ユーザーにスタッフ契約確認の権限を付与"""
    try:
        content_type = ContentType.objects.get_for_model(StaffContract)
        permission = Permission.objects.get(
            content_type=content_type,
            codename='confirm_staffcontract'
        )
        user.user_permissions.add(permission)
        return True
    except Exception as e:
        print(f"[ERROR] スタッフ契約確認権限付与エラー: {e}")
        return False


def grant_client_contract_confirmation_permission(user):
    """ユーザーにクライアント契約確認の権限を付与"""
    try:
        content_type = ContentType.objects.get_for_model(ClientContract)
        permission = Permission.objects.get(
            content_type=content_type,
            codename='confirm_clientcontract'
        )
        user.user_permissions.add(permission)
        return True
    except Exception as e:
        print(f"[ERROR] クライアント契約確認権限付与エラー: {e}")
        return False
