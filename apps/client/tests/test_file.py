from django.test import TestCase, Client as TestClient, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from apps.client.models import Client, ClientFile
from apps.company.models import Company

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
import tempfile
import shutil
import os

User = get_user_model()

@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class ClientFileTestCase(TestCase):
    @classmethod
    def tearDownClass(cls):
        # MEDIA_ROOT で使用した一時ディレクトリを削除
        if os.path.exists(settings.MEDIA_ROOT):
            shutil.rmtree(settings.MEDIA_ROOT)
        super().tearDownClass()

    def setUp(self):
        """テスト用データの準備"""
        self.company = Company.objects.create(name='Test Company', tenant_id=1)
        # テスト用ユーザー作成
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            tenant_id=1
        )
        
        # 必要な権限を付与
        client_content_type = ContentType.objects.get_for_model(Client)
        file_content_type = ContentType.objects.get_for_model(ClientFile)
        
        permissions = Permission.objects.filter(
            content_type__in=[client_content_type, file_content_type]
        )
        self.user.user_permissions.set(permissions)
        
        # テスト用登録区分作成
        from apps.master.models import ClientRegistStatus
        regist_status = ClientRegistStatus.objects.create(
            name='正社員',
            display_order=1,
            is_active=True,
            tenant_id=1
        )
        
        # テスト用クライアント作成
        self.client_obj = Client.objects.create(
            corporate_number='1234567890123',
            name='テストクライアント',
            name_furigana='テストクライアント',
            regist_status=regist_status,
            basic_contract_date='2024-01-15',
            tenant_id=1
        )
        
        self.client = TestClient()
        self.client.login(email='test@example.com', password='testpass123')

        # セッションにテナントIDを設定
        session = self.client.session
        session['current_tenant_id'] = 1
        session.save()

        # テスト内で作成したオブジェクトを保存するリスト
        self.created_files = []

    def tearDown(self):
        """テスト後のクリーンアップ"""
        # アップロードされたファイルを削除
        for client_file in self.created_files:
            if client_file.file:
                try:
                    # ファイルを閉じてから削除
                    client_file.file.close()
                    client_file.file.delete(save=False)
                except (OSError, PermissionError):
                    # Windowsでファイルが使用中の場合は無視
                    pass
    
    def test_client_file_model(self):
        """ClientFileモデルのテスト"""
        # テスト用ファイル作成
        test_file = SimpleUploadedFile(
            "test.txt",
            b"test content",
            content_type="text/plain"
        )
        
        client_file = ClientFile.objects.create(
            client=self.client_obj,
            file=test_file,
            description="テストファイル",
            tenant_id=1
        )
        self.created_files.append(client_file)
        
        self.assertEqual(client_file.client, self.client_obj)
        self.assertEqual(client_file.original_filename, "test.txt")
        self.assertEqual(client_file.description, "テストファイル")
        self.assertTrue(client_file.file_size > 0)
        self.assertEqual(client_file.file_extension, '.txt')
        self.assertFalse(client_file.is_image)
        self.assertTrue(client_file.is_document)
    
    def test_client_file_list_view(self):
        """ファイル一覧ビューのテスト"""
        response = self.client.get(
            reverse('client:client_file_list', kwargs={'client_pk': self.client_obj.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ファイル一覧')
    
    def test_client_file_create_view(self):
        """ファイル作成ビューのテスト"""
        response = self.client.get(
            reverse('client:client_file_create', kwargs={'client_pk': self.client_obj.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ファイルアップロード')
    
    def test_client_file_create_post(self):
        """ファイル作成POSTのテスト"""
        test_file = SimpleUploadedFile(
            "test_upload.txt",
            b"test upload content",
            content_type="text/plain"
        )
        
        response = self.client.post(
            reverse('client:client_file_create', kwargs={'client_pk': self.client_obj.pk}),
            {
                'file': test_file,
                'description': 'アップロードテスト'
            }
        )
        
        # 作成後はクライアント詳細画面にリダイレクト
        self.assertEqual(response.status_code, 302)
        self.assertTrue(ClientFile.objects.filter(client=self.client_obj, description='アップロードテスト').exists())
        # 作成したファイルを後で削除するために保存
        self.created_files.append(ClientFile.objects.get(description='アップロードテスト'))

    def test_client_file_delete_view(self):
        """ファイル削除ビューのテスト"""
        # テスト用ファイル作成
        test_file = SimpleUploadedFile(
            "delete_test.txt",
            b"delete test content",
            content_type="text/plain"
        )
        
        client_file = ClientFile.objects.create(
            client=self.client_obj,
            file=test_file,
            description="削除テストファイル",
            tenant_id=1
        )
        # このテストではファイルがDBから削除されるので、tearDownでの削除は不要
        
        # 削除確認画面のテスト
        response = self.client.get(
            reverse('client:client_file_delete', kwargs={'pk': client_file.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'delete_test.txt')
        self.assertContains(response, '削除しますか？')
        
        # 削除実行のテスト
        response = self.client.post(
            reverse('client:client_file_delete', kwargs={'pk': client_file.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ClientFile.objects.filter(pk=client_file.pk).exists())
    
    def test_client_file_download_view(self):
        """ファイルダウンロードビューのテスト"""
        # テスト用ファイル作成
        test_file = SimpleUploadedFile(
            "download_test.txt",
            b"download test content",
            content_type="text/plain"
        )
        
        client_file = ClientFile.objects.create(
            client=self.client_obj,
            file=test_file,
            description="ダウンロードテストファイル",
            tenant_id=1
        )
        self.created_files.append(client_file)
        
        response = self.client.get(
            reverse('client:client_file_download', kwargs={'pk': client_file.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain')
    
    def test_client_detail_with_files(self):
        """ファイル付きクライアント詳細のテスト"""
        # テスト用ファイル作成
        test_file = SimpleUploadedFile(
            "test.txt",
            b"test content",
            content_type="text/plain"
        )
        
        client_file = ClientFile.objects.create(
            client=self.client_obj,
            file=test_file,
            description="テストファイル",
            tenant_id=1
        )
        self.created_files.append(client_file)
        
        response = self.client.get(
            reverse('client:client_detail', kwargs={'pk': self.client_obj.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test.txt')
        # 基本契約締結日の表示もテスト
        self.assertContains(response, '2024年01月15日')