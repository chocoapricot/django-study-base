from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.connect.models import ConnectStaff
from apps.staff.models import Staff
from apps.company.models import Company

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
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!'
        )
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
        self.connection.approve(self.user)
        
        response = self.client.post(reverse('connect:staff_unapprove', args=[self.connection.pk]))
        self.assertEqual(response.status_code, 302)  # リダイレクト
        
        # 未承認に戻ったかチェック
        self.connection.refresh_from_db()
        self.assertFalse(self.connection.is_approved)
    
    def test_create_staff_connection(self):
        """スタッフ接続申請作成のテスト"""
        # staff.view_staff権限を付与
        from django.contrib.auth.models import Permission
        permission = Permission.objects.get(codename='view_staff')
        self.user.user_permissions.add(permission)
        
        response = self.client.post(reverse('connect:create_staff_connection'), {
            'staff_id': self.staff.pk
        })
        self.assertEqual(response.status_code, 302)  # リダイレクト
        
        # 接続申請が作成されたかチェック
        connection = ConnectStaff.objects.filter(
            corporate_number=self.company.corporate_number,
            email=self.staff.email
        ).first()
        self.assertIsNotNone(connection)
        self.assertEqual(connection.status, 'pending')
    
    def test_create_staff_connection_duplicate(self):
        """重複する接続申請作成のテスト"""
        # staff.view_staff権限を付与
        from django.contrib.auth.models import Permission
        permission = Permission.objects.get(codename='view_staff')
        self.user.user_permissions.add(permission)
        
        # 既存の接続申請を作成
        ConnectStaff.objects.create(
            corporate_number=self.company.corporate_number,
            email=self.staff.email,
            created_by=self.user,
            updated_by=self.user
        )
        
        response = self.client.post(reverse('connect:create_staff_connection'), {
            'staff_id': self.staff.pk
        })
        self.assertEqual(response.status_code, 302)  # リダイレクト
        
        # 重複チェックが働いて新しい申請は作成されないことを確認
        connections = ConnectStaff.objects.filter(
            corporate_number=self.company.corporate_number,
            email=self.staff.email
        )
        self.assertEqual(connections.count(), 1)