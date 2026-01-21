from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from .models import ConnectStaff, ConnectClient
from apps.profile.models import StaffProfile, StaffProfileMynumber, StaffProfileBank, StaffProfileContact, StaffProfileInternational, StaffProfileDisability
from apps.contract.models import StaffContract, ClientContract

User = get_user_model()


def grant_profile_permissions(user):
    """ユーザーにプロファイル関連の権限を付与 (staff_connectedグループへの追加に集約)"""
    return grant_staff_connected_permissions(user)


def grant_connect_permissions(user):
    """ユーザーに接続関連の権限を付与 (staffグループへの追加に集約)"""
    return grant_staff_connect_permissions(user)


def check_and_grant_permissions_for_email(email):
    """メールアドレスに対する接続申請があるかチェックし、権限を付与"""
    try:
        # 該当するユーザーを取得
        user = User.objects.get(email=email)
        
        # 該当するメールアドレスの接続申請があるかチェック
        connections = ConnectStaff.objects.filter(email=email)
        
        if connections.exists():
            # 接続申請がある場合、staffグループを付与
            grant_staff_connect_permissions(user)
            
            # 既に承認済みの場合はstaff_connectedグループも付与
            if connections.filter(status='approved').exists():
                grant_staff_connected_permissions(user)
            
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
        grant_staff_connect_permissions(user)
        return True
    except User.DoesNotExist:
        return False
    except Exception as e:
        print(f"[ERROR] 接続依頼時の権限付与エラー: {e}")
        return False


def grant_client_connect_permissions(user):
    """ユーザーをclientグループに追加し、関連権限をグループに付与"""
    try:
        from django.contrib.auth.models import Group
        group, created = Group.objects.get_or_create(name='client')

        # 権限をグループに付与
        content_type = ContentType.objects.get_for_model(ConnectClient)
        permissions = Permission.objects.filter(
            content_type=content_type,
            codename__in=['view_connectclient', 'change_connectclient']
        )
        group.permissions.add(*permissions)

        # ユーザーをグループに追加
        user.groups.add(group)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] clientグループへの追加エラー: {e}")
        return False


def grant_client_connected_permissions(user):
    """ユーザーをclient_connectedグループに追加し、関連権限をグループに付与"""
    try:
        from django.contrib.auth.models import Group
        group, created = Group.objects.get_or_create(name='client_connected')

        # 権限をグループに付与
        content_type = ContentType.objects.get_for_model(ClientContract)
        permission = Permission.objects.get(
            content_type=content_type,
            codename='confirm_clientcontract'
        )
        group.permissions.add(permission)
        
        # ユーザーをグループに追加
        user.groups.add(group)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] client_connectedグループへの追加エラー: {e}")
        return False


def remove_user_from_client_group_if_no_requests(email):
    """接続申請がない場合、ユーザーをclientグループから削除"""
    try:
        # 申請が残っているか確認
        if not ConnectClient.objects.filter(email=email).exists():
            user = User.objects.get(email=email)
            from django.contrib.auth.models import Group
            try:
                group = Group.objects.get(name='client')
                user.groups.remove(group)
                print(f"[INFO] clientグループから削除: {email}")
            except Group.DoesNotExist:
                pass
            
            try:
                connected_group = Group.objects.get(name='client_connected')
                user.groups.remove(connected_group)
                print(f"[INFO] client_connectedグループから削除: {email}")
            except Group.DoesNotExist:
                pass
        return True
    except User.DoesNotExist:
        return False
    except Exception as e:
        print(f"[ERROR] クライアントグループ削除判定エラー: {e}")
        return False


def grant_staff_connect_permissions(user):
    """ユーザーをstaffグループに追加し、関連権限をグループに付与"""
    try:
        from django.contrib.auth.models import Group
        group, created = Group.objects.get_or_create(name='staff')

        # 権限をグループに付与
        content_type = ContentType.objects.get_for_model(ConnectStaff)
        permissions = Permission.objects.filter(
            content_type=content_type,
            codename__in=['view_connectstaff', 'change_connectstaff']
        )
        group.permissions.add(*permissions)
        
        # ユーザーをグループに追加
        user.groups.add(group)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] staffグループへの追加エラー: {e}")
        return False


def grant_staff_connected_permissions(user):
    """ユーザーをstaff_connectedグループに追加し、関連権限をグループに付与"""
    try:
        from django.contrib.auth.models import Group
        from apps.kintai.models import StaffTimesheet, StaffTimecard, StaffTimerecord, StaffTimerecordBreak
        group, created = Group.objects.get_or_create(name='staff_connected')

        # 対象となるモデルのリスト
        models_to_grant_all = [
            StaffProfile, StaffProfileMynumber, StaffProfileBank, StaffProfileContact,
            StaffProfileInternational, StaffProfileDisability,
            StaffTimesheet, StaffTimecard, StaffTimerecord, StaffTimerecordBreak
        ]

        permissions_to_add = []

        # 'profile.*' と 'kintai.*' の全権限を取得
        for model in models_to_grant_all:
            content_type = ContentType.objects.get_for_model(model)
            permissions = Permission.objects.filter(content_type=content_type)
            permissions_to_add.extend(permissions)

        # 'contract' の特定権限を取得
        contract_content_type = ContentType.objects.get_for_model(StaffContract)
        contract_permissions = Permission.objects.filter(
            content_type=contract_content_type,
            codename__in=['confirm_staffcontract', 'view_staffcontract']
        )
        permissions_to_add.extend(contract_permissions)

        # 権限をグループに一括で追加
        group.permissions.add(*permissions_to_add)
        
        # ユーザーをグループに追加
        user.groups.add(group)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] staff_connectedグループへの追加エラー: {e}")
        return False


def check_and_grant_client_permissions_for_email(email):
    """メールアドレスに対するクライアント接続申請があるかチェックし、権限を付与"""
    try:
        # 該当するユーザーを取得
        user = User.objects.get(email=email)
        
        # 該当するメールアドレスのクライアント接続申請があるかチェック
        connections = ConnectClient.objects.filter(email=email)
        
        if connections.exists():
            # 接続申請がある場合、clientグループを付与
            grant_client_connect_permissions(user)
            
            # 既に承認済みの場合はclient_connectedグループも付与
            if connections.filter(status='approved').exists():
                grant_client_connected_permissions(user)
            
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
    """ユーザーにスタッフ契約確認の権限を付与 (staff_connectedグループへの追加に集約)"""
    return grant_staff_connected_permissions(user)
