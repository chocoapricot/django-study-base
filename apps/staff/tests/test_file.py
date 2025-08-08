from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.staff.models import Staff, StaffFile
from apps.system.settings.models import Dropdowns
import tempfile
import os

User = get_user_model()

class StaffFileTestCase(TestCase):
    def setUp(self):
        """テスト用データの準備"""
        # テスト用ユーザー作成
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # 必要な権限を付与
        from django.contrib.auth.models import Permission
        permissions = Permission.objects.filter(
            codename__in=[
                'view_staff', 'add_staff', 'change_staff', 'delete_staff',
                'view_stafffile', 'add_stafffile', 'change_stafffile', 'delete_stafffile'
            ]
        )
        self.user.user_permissions.set(permissions)
        
        # テスト用ドロップダウン作成
        Dropdowns.objects.create(
            category='sex',
            value='1',
            name='男性',
            active=True,
            disp_seq=1
        )
        
        Dropdowns.objects.create(
            category='regist_form',
            value='1',
            name='正社員',
            active=True,
            disp_seq=1
        )
        
        # テスト用スタッフ作成
        self.staff = Staff.objects.create(
            name_last='テスト',
            name_first='太郎',
            name_kana_last='テスト',
            name_kana_first='タロウ',
            sex=1,
            regist_form_code=1,
            email='staff@example.com'
        )
        
        self.client = Client()
        self.client.login(email='test@example.com', password='testpass123')
    
    def test_staff_file_model(self):
        """StaffFileモデルのテスト"""
        # テスト用ファイル作成
        test_file = SimpleUploadedFile(
            "test.txt",
            b"test content",
            content_type="text/plain"
        )
        
        staff_file = StaffFile.objects.create(
            staff=self.staff,
            file=test_file,
            description="テストファイル"
        )
        
        self.assertEqual(staff_file.staff, self.staff)
        self.assertEqual(staff_file.original_filename, "test.txt")
        self.assertEqual(staff_file.description, "テストファイル")
        self.assertTrue(staff_file.file_size > 0)
        self.assertEqual(staff_file.file_extension, '.txt')
        self.assertFalse(staff_file.is_image)
        self.assertTrue(staff_file.is_document)
    
    def test_staff_file_list_view(self):
        """ファイル一覧ビューのテスト"""
        response = self.client.get(
            reverse('staff:staff_file_list', kwargs={'staff_pk': self.staff.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ファイル一覧')
    
    def test_staff_file_create_view(self):
        """ファイル作成ビューのテスト"""
        response = self.client.get(
            reverse('staff:staff_file_create', kwargs={'staff_pk': self.staff.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ファイル追加')
    
    def test_staff_detail_with_files(self):
        """ファイル付きスタッフ詳細のテスト"""
        # テスト用ファイル作成
        test_file = SimpleUploadedFile(
            "test.txt",
            b"test content",
            content_type="text/plain"
        )
        
        StaffFile.objects.create(
            staff=self.staff,
            file=test_file,
            description="テストファイル"
        )
        
        response = self.client.get(
            reverse('staff:staff_detail', kwargs={'pk': self.staff.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test.txt')
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        # アップロードされたファイルを削除
        for staff_file in StaffFile.objects.all():
            if staff_file.file:
                try:
                    staff_file.file.delete()
                except:
                    pass