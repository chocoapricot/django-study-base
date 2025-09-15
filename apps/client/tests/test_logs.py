from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.client.models import Client as ClientModel, ClientFile
from apps.system.logs.models import AppLog
from apps.system.settings.models import Dropdowns

User = get_user_model()

class ClientLogsTestCase(TestCase):
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
                'view_client', 'add_client', 'change_client', 'delete_client',
                'view_clientfile', 'add_clientfile', 'change_clientfile', 'delete_clientfile'
            ]
        )
        self.user.user_permissions.set(permissions)
        
        # テスト用ドロップダウン作成
        Dropdowns.objects.create(
            category='client_regist_status',
            value='1',
            name='優良企業',
            active=True,
            disp_seq=1
        )
        
        # テスト用クライアント作成
        self.client_model = ClientModel.objects.create(
            name='テスト株式会社',
            name_furigana='テストカブシキガイシャ',
            corporate_number='1234567890123',
            client_regist_status=1
        )
        
        self.client = Client()
        self.client.login(email='test@example.com', password='testpass123')
    
    def test_client_file_log(self):
        """クライアントファイルのログ記録テスト"""
        initial_log_count = AppLog.objects.filter(model_name='ClientFile').count()
        
        # テスト用ファイル作成
        test_file = SimpleUploadedFile(
            "test.txt",
            b"test content",
            content_type="text/plain"
        )
        
        # ファイル追加
        client_file = ClientFile.objects.create(
            client=self.client_model,
            file=test_file,
            description="テストファイル"
        )
        
        # ログが作成されたことを確認
        self.assertGreater(AppLog.objects.filter(model_name='ClientFile').count(), initial_log_count)
        
        # 最新のログを確認
        latest_log = AppLog.objects.latest('timestamp')
        self.assertEqual(latest_log.action, 'create')
        self.assertEqual(latest_log.model_name, 'ClientFile')
        self.assertEqual(latest_log.object_id, str(client_file.pk))
        
        # ファイル更新
        client_file.description = "更新されたテストファイル"
        client_file.save()
        
        # 更新ログが作成されたことを確認
        self.assertGreater(AppLog.objects.filter(model_name='ClientFile', action='update').count(), 0)
        
        # ファイル削除
        client_file.delete()
        
        # 削除ログが作成されたことを確認
        self.assertGreater(AppLog.objects.filter(model_name='ClientFile', action='delete').count(), 0)
        
        # 削除ログを確認
        delete_log = AppLog.objects.latest('timestamp')
        self.assertEqual(delete_log.action, 'delete')
        self.assertEqual(delete_log.model_name, 'ClientFile')
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        # アップロードされたファイルを削除
        for client_file in ClientFile.objects.all():
            if client_file.file:
                try:
                    client_file.file.delete()
                except:
                    pass