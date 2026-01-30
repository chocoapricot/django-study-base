from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from apps.staff.models import Staff
from apps.contract.models import StaffContract
from apps.master.models import EmploymentType, ContractPattern
from apps.accounts.models import MyUser
from apps.common.constants import Constants
from apps.company.models import Company
from apps.common.middleware import set_current_tenant_id
from apps.kintai.models import StaffTimecard, StaffTimesheet
from datetime import date
import io


class TimecardImportTestCase(TestCase):
    """勤怠CSV取込機能のテストケース"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        # テナントを作成
        self.company = Company.objects.create(name='Test Company', corporate_number='1234567890123')
        set_current_tenant_id(self.company.tenant_id)

        # テストユーザーを作成
        self.user = MyUser.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            last_name='テスト',
            first_name='太郎',
            tenant_id=self.company.tenant_id
        )
        # 権限を付与
        from django.contrib.auth.models import Permission
        permission = Permission.objects.get(codename='add_stafftimecard')
        self.user.user_permissions.add(permission)
        
        # クライアントを作成
        self.client = Client()
        self.client.login(email='test@example.com', password='testpass123')
        
        # 雇用形態を作成
        self.employment_type = EmploymentType.objects.create(
            name='正社員',
            display_order=1,
            is_active=True
        )
        
        # スタッフを作成
        self.staff = Staff.objects.create(
            employee_no='EMP001',
            name_last='山田',
            name_first='太郎',
            name_kana_last='ヤマダ',
            name_kana_first='タロウ',
            email='yamada@example.com',
            tenant_id=self.company.tenant_id
        )
        
        # スタッフ契約を作成
        self.contract_pattern = ContractPattern.objects.create(
            name='テスト契約パターン',
            domain=Constants.DOMAIN.STAFF,
            # その他の必須フィールドがあれば追加
        )
        self.contract = StaffContract.objects.create(
            staff=self.staff,
            employment_type=self.employment_type,
            contract_name='2024年度契約',
            contract_number='C2024001',
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            contract_pattern=self.contract_pattern,
            tenant_id=self.company.tenant_id
        )
    
    def tearDown(self):
        """テスト後のクリーンアップ"""
        cache.clear()
    
    def test_timecard_import_view(self):
        """CSV取込画面の表示テスト"""
        response = self.client.get(reverse('kintai:timecard_import'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'kintai/kintai_import.html')
        self.assertIn('form', response.context)
    
    def test_timecard_import_upload_success(self):
        """CSVアップロード成功テスト"""
        csv_content = """社員番号,契約番号,勤務日,勤務区分,勤務時間名称,開始時刻,開始翌日フラグ,終了時刻,終了翌日フラグ,休憩時間（分）,有給休暇日数,備考
EMP001,C2024001,2024-12-01,10,通常勤務,09:00,0,18:00,0,60,0,テスト"""
        
        csv_file = SimpleUploadedFile(
            "test.csv",
            csv_content.encode('cp932'),
            content_type="text/csv"
        )
        
        response = self.client.post(
            reverse('kintai:timecard_import_upload'),
            {'csv_file': csv_file}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('task_id', data)
        self.assertIsNotNone(data['task_id'])
    
    def test_timecard_import_process_success(self):
        """CSV処理成功テスト"""
        # タスク情報をキャッシュに保存
        import tempfile
        import os
        
        csv_content = """社員番号,契約番号,勤務日,勤務区分,勤務時間名称,開始時刻,開始翌日フラグ,終了時刻,終了翌日フラグ,休憩時間（分）,有給休暇日数,備考
EMP001,C2024001,2024-12-01,10,通常勤務,09:00,0,18:00,0,60,0,テスト
EMP001,C2024001,2024-12-02,10,通常勤務,09:00,0,20:00,0,60,0,残業"""
        
        # 一時ファイルを作成
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', encoding='cp932') as f:
            f.write(csv_content)
            temp_file_path = f.name
        
        try:
            task_id = 'test-task-id'
            from datetime import datetime, timezone
            cache.set(
                f'import_task_{task_id}',
                {
                    'file_path': temp_file_path,
                    'status': 'uploaded',
                    'progress': 0,
                    'total': 0,
                    'errors': [],
                    'start_time': datetime.now(timezone.utc).isoformat(),
                    'elapsed_time_seconds': 0,
                    'estimated_time_remaining_seconds': 0,
                },
                timeout=3600,
            )
            
            response = self.client.post(
                reverse('kintai:timecard_import_process', kwargs={'task_id': task_id})
            )
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data['status'], 'completed')
            self.assertEqual(data['imported_count'], 2)
            self.assertEqual(len(data['errors']), 0)
            
            # データが正しく登録されているか確認
            self.assertEqual(StaffTimecard.objects.count(), 2)
            self.assertEqual(StaffTimesheet.objects.count(), 1)
            
            timecard1 = StaffTimecard.objects.get(work_date=date(2024, 12, 1))
            self.assertEqual(timecard1.work_type, '10')
            self.assertEqual(timecard1.memo, 'テスト')
            
            timecard2 = StaffTimecard.objects.get(work_date=date(2024, 12, 2))
            self.assertEqual(timecard2.work_type, '10')
            self.assertEqual(timecard2.memo, '残業')
        
        finally:
            # 一時ファイルを削除
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
    
    def test_timecard_import_process_invalid_employee(self):
        """存在しない社員番号のエラーテスト"""
        import tempfile
        import os
        
        csv_content = """社員番号,契約番号,勤務日,勤務区分,勤務時間名称,開始時刻,開始翌日フラグ,終了時刻,終了翌日フラグ,休憩時間（分）,有給休暇日数,備考
EMP999,C2024001,2024-12-01,10,通常勤務,09:00,0,18:00,0,60,0,"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', encoding='cp932') as f:
            f.write(csv_content)
            temp_file_path = f.name
        
        try:
            task_id = 'test-task-id-2'
            from datetime import datetime, timezone
            cache.set(
                f'import_task_{task_id}',
                {
                    'file_path': temp_file_path,
                    'status': 'uploaded',
                    'progress': 0,
                    'total': 0,
                    'errors': [],
                    'start_time': datetime.now(timezone.utc).isoformat(),
                    'elapsed_time_seconds': 0,
                    'estimated_time_remaining_seconds': 0,
                },
                timeout=3600,
            )
            
            response = self.client.post(
                reverse('kintai:timecard_import_process', kwargs={'task_id': task_id})
            )
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data['status'], 'completed')
            self.assertEqual(data['imported_count'], 0)
            self.assertGreater(len(data['errors']), 0)
            self.assertIn('社員番号 EMP999 が見つかりません', data['errors'][0])
        
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
    
    def test_timecard_import_process_invalid_contract(self):
        """存在しない契約番号のエラーテスト"""
        import tempfile
        import os
        
        csv_content = """社員番号,契約番号,勤務日,勤務区分,勤務時間名称,開始時刻,開始翌日フラグ,終了時刻,終了翌日フラグ,休憩時間（分）,有給休暇日数,備考
EMP001,C9999999,2024-12-01,10,通常勤務,09:00,0,18:00,0,60,0,"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', encoding='cp932') as f:
            f.write(csv_content)
            temp_file_path = f.name
        
        try:
            task_id = 'test-task-id-3'
            from datetime import datetime, timezone
            cache.set(
                f'import_task_{task_id}',
                {
                    'file_path': temp_file_path,
                    'status': 'uploaded',
                    'progress': 0,
                    'total': 0,
                    'errors': [],
                    'start_time': datetime.now(timezone.utc).isoformat(),
                    'elapsed_time_seconds': 0,
                    'estimated_time_remaining_seconds': 0,
                },
                timeout=3600,
            )
            
            response = self.client.post(
                reverse('kintai:timecard_import_process', kwargs={'task_id': task_id})
            )
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data['status'], 'completed')
            self.assertEqual(data['imported_count'], 0)
            self.assertGreater(len(data['errors']), 0)
            self.assertIn('契約番号 C9999999 が見つかりません', data['errors'][0])
        
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
    
    def test_timecard_import_progress(self):
        """進捗確認テスト"""
        task_id = 'test-task-id-4'
        from datetime import datetime, timezone
        task_info = {
            'file_path': '/tmp/test.csv',
            'status': 'uploaded',
            'progress': 5,
            'total': 10,
            'errors': [],
            'start_time': datetime.now(timezone.utc).isoformat(),
            'elapsed_time_seconds': 10,
            'estimated_time_remaining_seconds': 10,
        }
        cache.set(f'import_task_{task_id}', task_info, timeout=3600)
        
        response = self.client.get(
            reverse('kintai:timecard_import_progress', kwargs={'task_id': task_id})
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'uploaded')
        self.assertEqual(data['progress'], 5)
        self.assertEqual(data['total'], 10)
    
    def test_timecard_import_with_paid_leave(self):
        """有給休暇データの取込テスト"""
        import tempfile
        import os
        
        csv_content = """社員番号,契約番号,勤務日,勤務区分,勤務時間名称,開始時刻,開始翌日フラグ,終了時刻,終了翌日フラグ,休憩時間（分）,有給休暇日数,備考
EMP001,C2024001,2024-12-03,40,,,,,,0,1.0,有給休暇取得"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', encoding='cp932') as f:
            f.write(csv_content)
            temp_file_path = f.name
        
        try:
            task_id = 'test-task-id-5'
            from datetime import datetime, timezone
            cache.set(
                f'import_task_{task_id}',
                {
                    'file_path': temp_file_path,
                    'status': 'uploaded',
                    'progress': 0,
                    'total': 0,
                    'errors': [],
                    'start_time': datetime.now(timezone.utc).isoformat(),
                    'elapsed_time_seconds': 0,
                    'estimated_time_remaining_seconds': 0,
                },
                timeout=3600,
            )
            
            response = self.client.post(
                reverse('kintai:timecard_import_process', kwargs={'task_id': task_id})
            )
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data['status'], 'completed')
            self.assertEqual(data['imported_count'], 1)
            
            timecard = StaffTimecard.objects.get(work_date=date(2024, 12, 3))
            self.assertEqual(timecard.work_type, '40')
            self.assertEqual(float(timecard.paid_leave_days), 1.0)
        
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
