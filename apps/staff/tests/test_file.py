from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from apps.staff.models import Staff, StaffFile
from apps.master.models import StaffRegistStatus, EmploymentType
from apps.system.settings.models import Dropdowns
import tempfile
import shutil
import os

User = get_user_model()

@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class StaffFileTestCase(TestCase):
    @classmethod
    def tearDownClass(cls):
        # MEDIA_ROOT で使用した一時ディレクトリを削除
        if os.path.exists(settings.MEDIA_ROOT):
            shutil.rmtree(settings.MEDIA_ROOT)
        super().tearDownClass()

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
            category='staff_regist_status',
            value='1',
            name='正社員',
            active=True,
            disp_seq=1
        )
        
        # マスターデータを作成
        self.regist_status = StaffRegistStatus.objects.create(
            name='正社員',
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        self.employment_type = EmploymentType.objects.create(
            name='正社員',
            display_order=1,
            created_by=self.user,
            updated_by=self.user
        )
        
        # テスト用スタッフ作成
        self.staff = Staff.objects.create(
            name_last='テスト',
            name_first='太郎',
            name_kana_last='テスト',
            name_kana_first='タロウ',
            sex=1,
            regist_status=self.regist_status,
            employment_type=self.employment_type,
            email='staff@example.com',
            created_by=self.user,
            updated_by=self.user
        )
        
        self.client = Client()
        self.client.login(email='test@example.com', password='testpass123')

        # テスト内で作成したオブジェクトを保存するリスト
        self.created_files = []

    def tearDown(self):
        """テスト後のクリーンアップ"""
        # アップロードされたファイルを削除
        for staff_file in self.created_files:
            if staff_file.file:
                staff_file.file.delete(save=False)
    
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
        self.created_files.append(staff_file)
        
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
        self.assertContains(response, 'ファイルアップロード')
    
    def test_staff_file_create_post(self):
        """ファイル作成POSTのテスト"""
        test_file = SimpleUploadedFile(
            "test_upload.txt",
            b"test upload content",
            content_type="text/plain"
        )
        
        response = self.client.post(
            reverse('staff:staff_file_create', kwargs={'staff_pk': self.staff.pk}),
            {
                'file': test_file,
                'description': 'アップロードテスト'
            }
        )
        
        # 作成後はスタッフ詳細画面にリダイレクト
        self.assertEqual(response.status_code, 302)
        self.assertTrue(StaffFile.objects.filter(staff=self.staff, description='アップロードテスト').exists())
        self.created_files.append(StaffFile.objects.get(description='アップロードテスト'))
    
    def test_staff_file_delete_view(self):
        """ファイル削除ビューのテスト"""
        # テスト用ファイル作成
        test_file = SimpleUploadedFile(
            "delete_test.txt",
            b"delete test content",
            content_type="text/plain"
        )
        
        staff_file = StaffFile.objects.create(
            staff=self.staff,
            file=test_file,
            description="削除テストファイル"
        )
        
        # 削除確認画面のテスト
        response = self.client.get(
            reverse('staff:staff_file_delete', kwargs={'pk': staff_file.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'delete_test.txt')
        self.assertContains(response, '削除しますか？')
        
        # 削除実行のテスト
        response = self.client.post(
            reverse('staff:staff_file_delete', kwargs={'pk': staff_file.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(StaffFile.objects.filter(pk=staff_file.pk).exists())
    
    def test_staff_file_download_view(self):
        """ファイルダウンロードビューのテスト"""
        # テスト用ファイル作成
        test_file = SimpleUploadedFile(
            "download_test.txt",
            b"download test content",
            content_type="text/plain"
        )
        
        staff_file = StaffFile.objects.create(
            staff=self.staff,
            file=test_file,
            description="ダウンロードテストファイル"
        )
        self.created_files.append(staff_file)
        
        response = self.client.get(
            reverse('staff:staff_file_download', kwargs={'pk': staff_file.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain')
    
    def test_staff_detail_with_files(self):
        """ファイル付きスタッフ詳細のテスト"""
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
        self.created_files.append(staff_file)
        
        response = self.client.get(
            reverse('staff:staff_detail', kwargs={'pk': self.staff.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test.txt')