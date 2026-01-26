from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.db.models import Q
from allauth.account.models import EmailAddress
from apps.connect.models import ConnectStaff, ConnectClient, ProfileRequest
from apps.staff.models import Staff
from apps.company.models import Company
from apps.profile.models import StaffProfile
from apps.master.models import StaffAgreement

User = get_user_model()


class ConnectStaffModelTest(TestCase):
    """ConnectStaffモデルのテスト"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
    
    def test_connect_staff_creation(self):
        """ConnectStaffの作成テスト"""
        connection = ConnectStaff.objects.create(
            corporate_number='1234567890123',
            email='staff@example.com',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(connection.corporate_number, '1234567890123')
        self.assertEqual(connection.email, 'staff@example.com')
        self.assertEqual(connection.status, 'pending')
        self.assertFalse(connection.is_approved)
    
    def test_approve_connection(self):
        """接続承認のテスト"""
        connection = ConnectStaff.objects.create(
            corporate_number='1234567890123',
            email='staff@example.com',
            created_by=self.user,
            updated_by=self.user
        )
        
        connection.approve(self.user)
        
        self.assertEqual(connection.status, 'approved')
        self.assertTrue(connection.is_approved)
        self.assertIsNotNone(connection.approved_at)
        self.assertEqual(connection.approved_by, self.user)
    
    def test_unapprove_connection(self):
        """接続未承認に戻すテスト"""
        connection = ConnectStaff.objects.create(
            corporate_number='1234567890123',
            email='staff@example.com',
            created_by=self.user,
            updated_by=self.user
        )
        
        # 一度承認してから未承認に戻す
        connection.approve(self.user)
        connection.unapprove()
        
        self.assertEqual(connection.status, 'pending')
        self.assertFalse(connection.is_approved)
        self.assertIsNone(connection.approved_at)
        self.assertIsNone(connection.approved_by)


class ConnectViewTest(TestCase):
    """Connect関連ビューのテスト"""
    
    def setUp(self):
        from django.contrib.auth.models import Group, Permission
        from django.contrib.contenttypes.models import ContentType

        StaffAgreement.objects.all().delete()
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
        self.user.is_staff = True
        self.user.save()
        EmailAddress.objects.create(
            user=self.user, email=self.user.email, primary=True, verified=True
        )

        # --- staff グループのセットアップ ---
        staff_group, _ = Group.objects.get_or_create(name='staff')

        # 必要な権限をリストアップ
        permission_codenames = [
            'view_connectstaff',
            'change_connectstaff',
            'view_connectclient',
        ]

        # ConnectStaff と ConnectClient の ContentType を取得
        content_type_staff = ContentType.objects.get_for_model(ConnectStaff)
        content_type_client = ContentType.objects.get_for_model(ConnectClient)

        # 権限を取得
        permissions = Permission.objects.filter(
            Q(content_type=content_type_staff, codename__in=permission_codenames) |
            Q(content_type=content_type_client, codename__in=permission_codenames)
        )

        staff_group.permissions.add(*permissions)
        self.user.groups.add(staff_group)
        self.user.refresh_from_db()

        # 権限設定後にログイン
        self.client.login(username='testuser', password='TestPass123!')
        
        # テスト用の接続申請を作成
        self.connection = ConnectStaff.objects.create(
            corporate_number='1234567890123',
            email='test@example.com',  # ログインユーザーのメールアドレス
            created_by=self.user,
            updated_by=self.user
        )
        
        # テスト用のスタッフと会社を作成
        self.staff = Staff.objects.create(
            name_last='テスト',
            name_first='太郎',
            email='staff@example.com',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.company = Company.objects.create(
            name='テスト会社',
            corporate_number='9876543210987',
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_connect_index_view(self):
        """接続管理トップページのテスト"""
        response = self.client.get(reverse('connect:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '接続管理')
        self.assertContains(response, '1件')  # 未承認の申請が1件
    
    def test_connect_staff_list_view(self):
        """スタッフ接続一覧のテスト"""
        response = self.client.get(reverse('connect:staff_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'スタッフ接続申請一覧')
        self.assertContains(response, '1234567890123')
    
    def test_connect_staff_approve(self):
        """スタッフ接続承認のテスト"""
        response = self.client.post(reverse('connect:staff_approve', args=[self.connection.pk]))
        self.assertEqual(response.status_code, 302)  # リダイレクト
        
        # 承認されたかチェック
        self.connection.refresh_from_db()
        self.assertTrue(self.connection.is_approved)
    
    def test_connect_staff_unapprove(self):
        """スタッフ接続未承認に戻すテスト"""
        # 一度承認してから未承認に戻す
        StaffAgreement.objects.all().delete()
        self.connection.approve(self.user)
        
        response = self.client.post(reverse('connect:staff_unapprove', args=[self.connection.pk]))
        self.assertEqual(response.status_code, 302)  # リダイレクト
        
        # 未承認に戻ったかチェック
        self.connection.refresh_from_db()
        self.assertFalse(self.connection.is_approved)
    
    
    def test_permission_grant_on_connection_request(self):
        """接続依頼時の権限付与テスト"""
        from apps.connect.utils import grant_permissions_on_connection_request
        from django.contrib.auth.models import Permission
        
        # 既存ユーザーに権限を付与
        result = grant_permissions_on_connection_request(self.user.email)
        self.assertTrue(result)
        
        # 権限が付与されたかチェック
        permission = Permission.objects.get(codename='view_connectstaff')
        self.assertTrue(self.user.has_perm(f'connect.{permission.codename}'))
    
    def test_permission_grant_on_account_creation(self):
        """アカウント作成時の権限付与テスト"""
        from apps.connect.utils import check_and_grant_permissions_for_email
        
        # 接続申請を作成
        ConnectStaff.objects.create(
            corporate_number=self.company.corporate_number,
            email='newuser@example.com',
            created_by=self.user,
            updated_by=self.user
        )
        
        # 新しいユーザーを作成
        new_user = User.objects.create_user(
            username='newuser',
            email='newuser@example.com',
            password='TestPass123!'
        )
        
        # 権限チェックと付与
        result = check_and_grant_permissions_for_email(new_user.email)
        self.assertTrue(result)
        
        # 権限が付与されたかチェック
        from django.contrib.auth.models import Permission
        permission = Permission.objects.get(codename='view_connectstaff')
        new_user.refresh_from_db()
        self.assertTrue(new_user.has_perm(f'connect.{permission.codename}'))


class ConnectStaffApproveMethodTest(TestCase):
    """ConnectStaff.approveメソッドの詳細なテスト"""

    def setUp(self):
        self.approver = User.objects.create_user(
            username='approver',
            email='approver@example.com',
            password='TestPass123!'
        )
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='TestPass123!',
            first_name='Taro',
            last_name='Staff'
        )
        self.staff_master = Staff.objects.create(
            email=self.staff_user.email,
            name_first='Taro',
            name_last='Staff',
        )

    def test_approve_creates_no_request_if_profile_does_not_exist(self):
        """StaffProfileが存在しない場合、ProfileRequestは作成されない"""
        connection = ConnectStaff.objects.create(
            corporate_number='1111111111111',
            email=self.staff_user.email,
        )
        connection.approve(self.approver)
        self.assertEqual(ProfileRequest.objects.count(), 0)

    def test_approve_creates_request_if_profile_differs(self):
        """StaffProfileが存在し、Staffマスターと差分がある場合、ProfileRequestが作成される"""
        StaffProfile.objects.create(
            user=self.staff_user,
            name_first='Jiro',  # Staffマスターと異なる名前
            name_last='Profile',
        )
        connection = ConnectStaff.objects.create(
            corporate_number='2222222222222',
            email=self.staff_user.email,
        )
        connection.approve(self.approver)
        self.assertEqual(ProfileRequest.objects.count(), 1)

    def test_approve_creates_no_request_if_profile_matches(self):
        """StaffProfileが存在し、Staffマスターと差分がない場合、ProfileRequestは作成されない"""
        StaffProfile.objects.create(
            user=self.staff_user,
            name_first='Taro',  # Staffマスターと同じ名前
            name_last='Staff',
        )
        connection = ConnectStaff.objects.create(
            corporate_number='3333333333333',
            email=self.staff_user.email,
        )
        connection.approve(self.approver)
        self.assertEqual(ProfileRequest.objects.count(), 0)
