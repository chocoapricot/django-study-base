from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from apps.staff.models import Staff
from apps.staff.forms import StaffForm
from apps.contract.models import StaffContract

User = get_user_model()


class StaffFormTest(TestCase):
    """スタッフフォームのテストケース"""
    
    def setUp(self):
        """テストデータの準備"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        
        # ドロップダウンデータを作成
        from apps.system.settings.models import Dropdowns
        
        # 性別のドロップダウン
        Dropdowns.objects.create(
            category='sex',
            value='1',
            name='男性',
            disp_seq=1,
            active=True
        )
        Dropdowns.objects.create(
            category='sex',
            value='2',
            name='女性',
            disp_seq=2,
            active=True
        )
        
        # 登録区分のドロップダウン
        Dropdowns.objects.create(
            category='regist_form',
            value='1',
            name='正社員',
            disp_seq=1,
            active=True
        )
        Dropdowns.objects.create(
            category='regist_form',
            value='2',
            name='契約社員',
            disp_seq=2,
            active=True
        )
        
        # テスト用スタッフを作成
        self.staff = Staff.objects.create(
            regist_form_code=1,  # 数値で指定
            employee_no='EMP001',
            name_last='田中',
            name_first='太郎',
            name_kana_last='タナカ',
            name_kana_first='タロウ',
            birth_date=date(1990, 1, 1),
            sex=1,  # 数値で指定
            hire_date=date(2020, 4, 1),
            postal_code='1000001',
            address1='東京都千代田区千代田',
            phone='03-1234-5678',
            email='tanaka@example.com',
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_resignation_date_validation_with_future_contract(self):
        """退職日とスタッフ契約の契約終了日の整合性チェックテスト"""
        # スタッフ契約を作成（退職予定日より後に終了）
        contract_end_date = date(2024, 12, 31)
        StaffContract.objects.create(
            staff=self.staff,
            contract_name='テスト契約',
            contract_type='full_time',
            start_date=date(2024, 1, 1),
            end_date=contract_end_date,
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        # 契約終了日より前の退職日でフォームを作成
        resignation_date = date(2024, 11, 30)
        form_data = {
            'regist_form_code': '1',
            'employee_no': 'EMP001',
            'name_last': '田中',
            'name_first': '太郎',
            'name_kana_last': 'タナカ',
            'name_kana_first': 'タロウ',
            'birth_date': date(1990, 1, 1),
            'sex': '1',
            'hire_date': date(2020, 4, 1),
            'resignation_date': resignation_date,
            'postal_code': '1000001',
            'address1': '東京都千代田区千代田',
            'phone': '03-1234-5678',
            'email': 'tanaka@example.com'
        }
        
        form = StaffForm(data=form_data, instance=self.staff)
        self.assertFalse(form.is_valid())
        self.assertIn('契約終了日以降に退職日を設定してください', str(form.errors))
    
    def test_resignation_date_validation_with_same_date_contract(self):
        """退職日と契約終了日が同日の場合のテスト（同日はOK）"""
        # スタッフ契約を作成（退職予定日と同日に終了）
        contract_end_date = date(2024, 12, 31)
        StaffContract.objects.create(
            staff=self.staff,
            contract_name='テスト契約',
            contract_type='full_time',
            start_date=date(2024, 1, 1),
            end_date=contract_end_date,
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        # 契約終了日と同日の退職日でフォームを作成
        resignation_date = contract_end_date
        form_data = {
            'regist_form_code': '1',
            'employee_no': 'EMP001',
            'name_last': '田中',
            'name_first': '太郎',
            'name_kana_last': 'タナカ',
            'name_kana_first': 'タロウ',
            'birth_date': date(1990, 1, 1),
            'sex': '1',
            'hire_date': date(2020, 4, 1),
            'resignation_date': resignation_date,
            'postal_code': '1000001',
            'address1': '東京都千代田区千代田',
            'phone': '03-1234-5678',
            'email': 'tanaka@example.com'
        }
        
        form = StaffForm(data=form_data, instance=self.staff)
        self.assertTrue(form.is_valid())
    
    def test_resignation_date_validation_with_past_contract(self):
        """退職日より前に終了する契約がある場合のテスト（問題なし）"""
        # スタッフ契約を作成（退職予定日より前に終了）
        contract_end_date = date(2024, 10, 31)
        StaffContract.objects.create(
            staff=self.staff,
            contract_name='テスト契約',
            contract_type='full_time',
            start_date=date(2024, 1, 1),
            end_date=contract_end_date,
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        # 契約終了日より後の退職日でフォームを作成
        resignation_date = date(2024, 12, 31)
        form_data = {
            'regist_form_code': '1',
            'employee_no': 'EMP001',
            'name_last': '田中',
            'name_first': '太郎',
            'name_kana_last': 'タナカ',
            'name_kana_first': 'タロウ',
            'birth_date': date(1990, 1, 1),
            'sex': '1',
            'hire_date': date(2020, 4, 1),
            'resignation_date': resignation_date,
            'postal_code': '1000001',
            'address1': '東京都千代田区千代田',
            'phone': '03-1234-5678',
            'email': 'tanaka@example.com'
        }
        
        form = StaffForm(data=form_data, instance=self.staff)
        self.assertTrue(form.is_valid())
    
    def test_resignation_date_validation_with_inactive_contract(self):
        """無効な契約は考慮されないことのテスト"""
        # 無効なスタッフ契約を作成（退職予定日より後に終了するが無効）
        contract_end_date = date(2024, 12, 31)
        StaffContract.objects.create(
            staff=self.staff,
            contract_name='テスト契約',
            contract_type='full_time',
            start_date=date(2024, 1, 1),
            end_date=contract_end_date,
            is_active=False,  # 無効な契約
            created_by=self.user,
            updated_by=self.user
        )
        
        # 契約終了日より前の退職日でフォームを作成
        resignation_date = date(2024, 11, 30)
        form_data = {
            'regist_form_code': '1',
            'employee_no': 'EMP001',
            'name_last': '田中',
            'name_first': '太郎',
            'name_kana_last': 'タナカ',
            'name_kana_first': 'タロウ',
            'birth_date': date(1990, 1, 1),
            'sex': '1',
            'hire_date': date(2020, 4, 1),
            'resignation_date': resignation_date,
            'postal_code': '1000001',
            'address1': '東京都千代田区千代田',
            'phone': '03-1234-5678',
            'email': 'tanaka@example.com'
        }
        
        form = StaffForm(data=form_data, instance=self.staff)
        self.assertTrue(form.is_valid())  # 無効な契約は考慮されないのでOK
    
    def test_resignation_date_validation_with_no_end_date_contract(self):
        """契約終了日がない契約は考慮されないことのテスト"""
        # 契約終了日がないスタッフ契約を作成
        StaffContract.objects.create(
            staff=self.staff,
            contract_name='テスト契約',
            contract_type='full_time',
            start_date=date(2024, 1, 1),
            end_date=None,  # 契約終了日なし
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        # 退職日でフォームを作成
        resignation_date = date(2024, 11, 30)
        form_data = {
            'regist_form_code': '1',
            'employee_no': 'EMP001',
            'name_last': '田中',
            'name_first': '太郎',
            'name_kana_last': 'タナカ',
            'name_kana_first': 'タロウ',
            'birth_date': date(1990, 1, 1),
            'sex': '1',
            'hire_date': date(2020, 4, 1),
            'resignation_date': resignation_date,
            'postal_code': '1000001',
            'address1': '東京都千代田区千代田',
            'phone': '03-1234-5678',
            'email': 'tanaka@example.com'
        }
        
        form = StaffForm(data=form_data, instance=self.staff)
        self.assertTrue(form.is_valid())  # 契約終了日がない契約は考慮されないのでOK
    
    def test_resignation_date_validation_new_staff(self):
        """新規スタッフ作成時は契約チェックが実行されないことのテスト"""
        # 新規スタッフ作成時のフォーム
        form_data = {
            'regist_form_code': '1',
            'employee_no': 'EMP002',
            'name_last': '佐藤',
            'name_first': '花子',
            'name_kana_last': 'サトウ',
            'name_kana_first': 'ハナコ',
            'birth_date': date(1992, 5, 15),
            'sex': '2',
            'hire_date': date(2024, 1, 1),
            'resignation_date': date(2024, 11, 30),
            'postal_code': '1000002',
            'address1': '東京都千代田区丸の内',
            'phone': '03-9876-5432',
            'email': 'sato@example.com'
        }
        
        form = StaffForm(data=form_data)  # instanceなし（新規作成）
        self.assertTrue(form.is_valid())  # 新規作成時は契約チェックなしでOK