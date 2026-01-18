from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from apps.connect.models import ConnectClient
from apps.connect.utils import grant_client_connect_permissions, remove_user_from_client_group_if_no_requests
from apps.connect.views import connect_client_approve
from django.test.client import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware

User = get_user_model()

class ClientGroupPermissionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testclient',
            email='testclient@example.com',
            password='password'
        )
        self.staff_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='password',
            is_staff=True
        )
        self.group_name = 'client'
        # グループは自動作成されるはずだが、権限がある前提なので作りはしない（utilsが作ってくれるか確認）

    def test_grant_client_connect_permissions_adds_to_group_and_assigns_permissions(self):
        """申請時の権限付与関数がユーザーをグループに追加し、グループに権限を付与するか"""
        # 実行
        grant_client_connect_permissions(self.user)
        
        # 検証
        self.assertTrue(Group.objects.filter(name=self.group_name).exists())
        group = Group.objects.get(name=self.group_name)
        self.assertTrue(self.user.groups.filter(name=self.group_name).exists())

        # グループに権限が付与されているか確認
        content_type = ContentType.objects.get_for_model(ConnectClient)
        required_permissions = Permission.objects.filter(
            content_type=content_type,
            codename__in=['view_connectclient', 'change_connectclient']
        )
        self.assertEqual(group.permissions.count(), 2)
        for perm in required_permissions:
            self.assertIn(perm, group.permissions.all())

    def test_remove_from_group_if_no_requests(self):
        """申請がない場合にグループから削除されるか"""
        # 準備: グループに追加しておく
        grant_client_connect_permissions(self.user)
        self.assertTrue(self.user.groups.filter(name=self.group_name).exists())
        
        # 申請を作成
        ConnectClient.objects.create(
            corporate_number='1234567890123',
            email=self.user.email,
            created_by=self.staff_user,
            updated_by=self.staff_user
        )
        
        # 申請がある状態で削除判定実行 -> 削除されないはず
        remove_user_from_client_group_if_no_requests(self.user.email)
        self.assertTrue(self.user.groups.filter(name=self.group_name).exists())
        
        # 申請を削除
        ConnectClient.objects.all().delete()
        
        # 申請がない状態で削除判定実行 -> 削除されるはず
        remove_user_from_client_group_if_no_requests(self.user.email)
        self.assertFalse(self.user.groups.filter(name=self.group_name).exists())

    def test_connect_client_approve_does_not_error(self):
        """承認ビューがエラーなく動作し、余計な権限付与をしていないか（既存関数削除確認）"""
        # 準備
        connect_request = ConnectClient.objects.create(
            corporate_number='1234567890123',
            email=self.user.email,
            created_by=self.staff_user,
            updated_by=self.staff_user,
            status='pending'
        )
        
        # 権限を付与
        content_type = ContentType.objects.get_for_model(ConnectClient)
        permission = Permission.objects.get(
            content_type=content_type,
            codename='change_connectclient'
        )
        self.staff_user.user_permissions.add(permission)

        # ダミーリクエスト作成
        factory = RequestFactory()
        request = factory.post(f'/connect/client/{connect_request.pk}/approve/')
        request.user = self.staff_user
        
        # ミドルウェアでセッションとメッセージを有効化
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(request)
        request.session.save()
        middleware = MessageMiddleware(lambda r: None)
        middleware.process_request(request)

        # 実行
        response = connect_client_approve(request, connect_request.pk)
        
        # 検証
        self.assertEqual(response.status_code, 302) # リダイレクト
        connect_request.refresh_from_db()
        self.assertEqual(connect_request.status, 'approved')
        
        # ダイレクトな権限付与が行われていないことの確認
        # contract.confirm_clientcontract 権限を持っているかチェック (グループ経由で持っている可能性はあるが、user_permissionsにはないはず)
        # ただし今回はグループに権限を設定していないので、持っていないはず
        self.assertFalse(self.user.has_perm('contract.confirm_clientcontract')) 
        # has_permはグループも含めてチェックする。グループに権限入れてないのでFalseになるはず。

    def test_client_user_can_access_views_with_permission(self):
        """権限を持つクライアントユーザーがビューにアクセスできるか"""
        from django.test import Client
        # 準備: 権限を付与
        grant_client_connect_permissions(self.user)

        # ログイン
        client = Client()
        client.login(username='testclient', password='password')

        # connect:client_list へのアクセス
        response = client.get('/connect/client/')
        self.assertEqual(response.status_code, 200)

        # connect:client_approve へのアクセス (POST)
        connect_request = ConnectClient.objects.create(
            corporate_number='1234567890123',
            email=self.user.email,
            created_by=self.staff_user,
            updated_by=self.staff_user,
            status='pending'
        )
        response = client.post(f'/connect/client/{connect_request.pk}/approve/')
        self.assertEqual(response.status_code, 302)
