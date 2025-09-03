import io
import os
import uuid
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.contrib.auth import get_user_model
from apps.master.models import Bank, BankBranch
from django.conf import settings

User = get_user_model()

# テスト用に一時的なメディアディレクトリを設定
TEST_MEDIA_ROOT = os.path.join(settings.BASE_DIR, 'test_media')

@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class BankImportTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword',
            email='test@example.com'
        )
        self.user.user_permissions.add(*self.get_permissions())
        self.client.login(username='testuser', password='testpassword')
        cache.clear()

    def tearDown(self):
        # テスト後に一時ディレクトリをクリーンアップ
        import shutil
        if os.path.exists(TEST_MEDIA_ROOT):
            shutil.rmtree(TEST_MEDIA_ROOT)
        cache.clear()

    def get_permissions(self):
        from django.contrib.auth.models import Permission
        permissions = Permission.objects.filter(
            content_type__app_label='master',
            codename__in=['view_bank', 'add_bank', 'change_bank', 'delete_bank', 
                          'view_bankbranch', 'add_bankbranch', 'change_bankbranch', 'delete_bankbranch']
        )
        return permissions

    def test_get_import_page(self):
        """CSV取込ページにアクセスできるか"""
        response = self.client.get(reverse('master:bank_import'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'master/bank_import.html')

    def test_upload_view(self):
        """ファイルのアップロードが成功し、タスクIDが返されるか"""
        csv_data = "test\n"
        csv_file = SimpleUploadedFile("test.csv", csv_data.encode('utf-8'), content_type="text/csv")

        response = self.client.post(reverse('master:bank_import_upload'), {'csv_file': csv_file})
        
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertIn('task_id', json_response)

        task_id = json_response['task_id']
        task_info = cache.get(f'import_task_{task_id}')
        self.assertIsNotNone(task_info)
        self.assertEqual(task_info['status'], 'uploaded')
        self.assertTrue(os.path.exists(task_info['file_path']))

    def test_process_view_success(self):
        """正常なデータで処理が成功するか"""
        # 事前に銀行データを作成
        Bank.objects.create(bank_code='0001', name='みずほ銀行', is_active=True)

        csv_data = "0001,001,ﾄｳｷﾖｳ          ,東京営業部,2\n"

        task_id = str(uuid.uuid4())
        temp_dir = os.path.join(TEST_MEDIA_ROOT, 'temp_uploads')
        os.makedirs(temp_dir, exist_ok=True)
        temp_file_path = os.path.join(temp_dir, f'{task_id}.csv')
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            f.write(csv_data)

        from datetime import datetime, timezone
        cache.set(f'import_task_{task_id}', {
            'file_path': temp_file_path,
            'status': 'uploaded',
            'progress': 0,
            'total': 0,
            'errors': [],
            'start_time': datetime.now(timezone.utc).isoformat(),
            'elapsed_time_seconds': 0,
            'estimated_time_remaining_seconds': 0,
        }, timeout=3600)

        response = self.client.post(reverse('master:bank_import_process', kwargs={'task_id': task_id}))
        
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'completed')
        self.assertEqual(json_response['imported_count'], 1)
        self.assertEqual(len(json_response['errors']), 0)
        
        self.assertTrue(BankBranch.objects.filter(bank__bank_code='0001', branch_code='001').exists())

        task_info = cache.get(f'import_task_{task_id}')
        self.assertEqual(task_info['status'], 'completed')

    def test_process_view_invalid_bank(self):
        """不正な銀行コードでエラーが記録されるか"""
        csv_data = "9999,001,無効な支店     ,むこうなしてん,2\n"
        
        task_id = str(uuid.uuid4())
        temp_dir = os.path.join(TEST_MEDIA_ROOT, 'temp_uploads')
        os.makedirs(temp_dir, exist_ok=True)
        temp_file_path = os.path.join(temp_dir, f'{task_id}.csv')
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            f.write(csv_data)

        from datetime import datetime, timezone
        cache.set(f'import_task_{task_id}', {
            'file_path': temp_file_path,
            'status': 'uploaded',
            'progress': 0,
            'total': 0,
            'errors': [],
            'start_time': datetime.now(timezone.utc).isoformat(),
            'elapsed_time_seconds': 0,
            'estimated_time_remaining_seconds': 0,
        }, timeout=3600)

        response = self.client.post(reverse('master:bank_import_process', kwargs={'task_id': task_id}))
        
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'completed')
        self.assertEqual(len(json_response['errors']), 1)
        self.assertIn('銀行コード 9999 が見つかりません。', json_response['errors'][0])
        
        self.assertFalse(BankBranch.objects.filter(branch_code='001').exists())

    def test_progress_view(self):
        """進捗状況が正しく返されるか"""
        task_id = str(uuid.uuid4())
        cache.set(f'import_task_{task_id}', {
            'status': 'processing',
            'progress': 50,
            'total': 100,
            'errors': [],
        }, timeout=3600)

        response = self.client.get(reverse('master:bank_import_progress', kwargs={'task_id': task_id}))

        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'processing')
        self.assertEqual(json_response['progress'], 50)
        self.assertEqual(json_response['total'], 100)
