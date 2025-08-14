from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from .models import ConnectStaff

User = get_user_model()


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
        
        print(f"[INFO] ユーザー {user.email} に接続権限を付与しました")
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
            print(f"[INFO] {email} に対する接続申請はありません")
            return False
            
    except User.DoesNotExist:
        print(f"[INFO] ユーザー {email} は存在しません")
        return False
    except Exception as e:
        print(f"[ERROR] 権限チェックエラー: {e}")
        return False


def grant_permissions_on_connection_request(email):
    """接続依頼時に既存ユーザーがいる場合は権限を付与"""
    try:
        user = User.objects.get(email=email)
        grant_connect_permissions(user)
        print(f"[INFO] 接続依頼時に権限を付与: {email}")
        return True
    except User.DoesNotExist:
        print(f"[INFO] ユーザー {email} は未登録のため、権限付与をスキップ")
        return False
    except Exception as e:
        print(f"[ERROR] 接続依頼時の権限付与エラー: {e}")
        return False