import io
import os
import uuid
from datetime import datetime, date, timedelta, timezone
from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.conf import settings
from apps.master.models import Grade
from apps.common.constants import Constants
from apps.common.middleware import set_current_tenant_id

User = get_user_model()
TEST_MEDIA_ROOT = os.path.join(settings.BASE_DIR, 'test_media_grade')

@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class GradeImportTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username='admin',
            password='password',
            email='admin@example.com'
        )
        self.client.login(username='admin', password='password')
        set_current_tenant_id(1)
        cache.clear()

    def tearDown(self):
        import shutil
        if os.path.exists(TEST_MEDIA_ROOT):
            shutil.rmtree(TEST_MEDIA_ROOT)
        cache.clear()
        set_current_tenant_id(None)

    def test_get_import_page(self):
        """CSV取込ページにアクセスできるか"""
        response = self.client.get(reverse('master:grade_import'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'master/grade_import.html')

    def test_upload_view(self):
        """ファイルのアップロードが成功し、タスクIDが返されるか"""
        csv_data = "2024/01/01,G01,Test,時給,1000\n"
        csv_file = SimpleUploadedFile("test.csv", csv_data.encode('utf-8'), content_type="text/csv")

        response = self.client.post(reverse('master:grade_import_upload'), {'csv_file': csv_file})

        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertIn('task_id', json_response)

        task_id = json_response['task_id']
        task_info = cache.get(f'import_task_{task_id}')
        self.assertIsNotNone(task_info)
        self.assertEqual(task_info['status'], 'uploaded')

    def test_process_view_success_with_overlap(self):
        """正常なデータで処理が成功し、期間重複が解消されるか"""
        # 既存データ作成
        Grade.objects.create(
            code='G01',
            name='旧等級',
            salary_type=Constants.PAY_UNIT.HOURLY,
            amount=1000,
            start_date=date(2023, 1, 1),
            is_active=True,
            tenant_id=1
        )

        csv_data = "2024/01/01,G01,新等級,時給,1200\n"

        task_id = str(uuid.uuid4())
        temp_dir = os.path.join(TEST_MEDIA_ROOT, 'temp_uploads')
        os.makedirs(temp_dir, exist_ok=True)
        temp_file_path = os.path.join(temp_dir, f'{task_id}.csv')
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            f.write(csv_data)

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

        response = self.client.post(reverse('master:grade_import_process', kwargs={'task_id': task_id}))

        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'completed')
        self.assertEqual(json_response['imported_count'], 1)

        # 検証：既存データの終了日が更新されていること
        old_grade = Grade.objects.get(code='G01', start_date=date(2023, 1, 1))
        self.assertEqual(old_grade.end_date, date(2023, 12, 31))

        # 検証：新規データが登録されていること
        new_grade = Grade.objects.get(code='G01', start_date=date(2024, 1, 1))
        self.assertEqual(new_grade.name, '新等級')
        self.assertEqual(new_grade.amount, 1200)
        self.assertEqual(new_grade.salary_type, Constants.PAY_UNIT.HOURLY)

    def test_process_invalid_data(self):
        """不正なデータでエラーが記録されるか"""
        csv_data = "invalid-date,G02,Name,時給,1000\n" # 不正な日付
        csv_data += "2024/01/01,G02,Name,不正種別,1000\n" # 不正な給与種別
        csv_data += "2024/01/01,G02,Name,時給,abc\n" # 不正な金額

        task_id = str(uuid.uuid4())
        temp_dir = os.path.join(TEST_MEDIA_ROOT, 'temp_uploads')
        os.makedirs(temp_dir, exist_ok=True)
        temp_file_path = os.path.join(temp_dir, f'{task_id}.csv')
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            f.write(csv_data)

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

        response = self.client.post(reverse('master:grade_import_process', kwargs={'task_id': task_id}))

        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(len(json_response['errors']), 3)

    def test_progress_view(self):
        """進捗状況が正しく返されるか"""
        task_id = str(uuid.uuid4())
        cache.set(f'import_task_{task_id}', {
            'status': 'processing',
            'progress': 10,
            'total': 20,
            'errors': [],
            'elapsed_time_seconds': 0,
            'estimated_time_remaining_seconds': 0,
        }, timeout=3600)

        response = self.client.get(reverse('master:grade_import_progress', kwargs={'task_id': task_id}))

        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertEqual(json_response['status'], 'processing')
        self.assertEqual(json_response['progress'], 10)
        self.assertEqual(json_response['total'], 20)
