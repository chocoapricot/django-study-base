from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from apps.staff.models import Staff
from apps.staff.forms import StaffForm
from apps.contract.models import StaffContract
from apps.master.models import StaffRegistStatus, ContractPattern

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
        
        # スタッフ登録区分マスタを作成
        self.regist_status_1 = StaffRegistStatus.objects.create(name='正社員', display_order=1, is_active=True)
        self.regist_status_2 = StaffRegistStatus.objects.create(name='契約社員', display_order=2, is_active=True)
        
        # 雇用形態マスタを作成
        from apps.master.models import EmploymentType
        self.employment_type_1 = EmploymentType.objects.create(name='正社員', display_order=1, is_fixed_term=False, is_active=True)
        self.employment_type_2 = EmploymentType.objects.create(name='契約社員', display_order=2, is_fixed_term=True, is_active=True)
        self.employment_type_3 = EmploymentType.objects.create(name='派遣社員', display_order=3, is_fixed_term=True, is_active=True)
        
        # 契約書パターンマスタを作成
        self.contract_pattern_1 = ContractPattern.objects.create(name='テスト', domain='1', is_active=True)

        # テスト用スタッフを作成
        self.staff = Staff.objects.create(
            regist_status=self.regist_status_1,  # StaffRegistStatusインスタンスで指定
            employee_no='EMP001',
            employment_type=self.employment_type_1,  # 雇用形態を追加
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
            contract_pattern=self.contract_pattern_1,
            contract_name='テスト契約',
            start_date=date(2024, 1, 1),
            end_date=contract_end_date,
            created_by=self.user,
            updated_by=self.user
        )
        
        # 契約終了日より前の退職日でフォームを作成
        resignation_date = date(2024, 11, 30)
        form_data = {
            'regist_status': self.regist_status_1.pk,
            'employee_no': 'EMP001',
            'employment_type': self.employment_type_1.pk,  # 雇用形態を追加
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
            contract_pattern=self.contract_pattern_1,
            contract_name='テスト契約',
            start_date=date(2024, 1, 1),
            end_date=contract_end_date,
            created_by=self.user,
            updated_by=self.user
        )
        
        # 契約終了日と同日の退職日でフォームを作成
        resignation_date = contract_end_date
        form_data = {
            'regist_status': self.regist_status_1.pk,
            'employee_no': 'EMP001',
            'employment_type': self.employment_type_1.pk,  # 雇用形態を追加
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
            contract_pattern=self.contract_pattern_1,
            contract_name='テスト契約',
            start_date=date(2024, 1, 1),
            end_date=contract_end_date,
            created_by=self.user,
            updated_by=self.user
        )
        
        # 契約終了日より後の退職日でフォームを作成
        resignation_date = date(2024, 12, 31)
        form_data = {
            'regist_status': self.regist_status_1.pk,
            'employee_no': 'EMP001',
            'employment_type': self.employment_type_1.pk,  # 雇用形態を追加
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
   
    
    def test_resignation_date_validation_with_no_end_date_contract(self):
        """契約終了日がない契約は考慮されないことのテスト"""
        # 契約終了日がないスタッフ契約を作成
        StaffContract.objects.create(
            staff=self.staff,
            contract_pattern=self.contract_pattern_1,
            contract_name='テスト契約',
            start_date=date(2024, 1, 1),
            end_date=None,  # 契約終了日なし
            created_by=self.user,
            updated_by=self.user
        )
        
        # 退職日でフォームを作成
        resignation_date = date(2024, 11, 30)
        form_data = {
            'regist_status': self.regist_status_1.pk,
            'employee_no': 'EMP001',
            'employment_type': self.employment_type_1.pk,  # 雇用形態を追加
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
            'regist_status': self.regist_status_1.pk,
            'employee_no': 'EMP002',
            'employment_type': self.employment_type_2.pk,  # 雇用形態を追加
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
    
    def test_hire_date_employee_no_validation_both_required(self):
        """入社日と社員番号のセット入力バリデーションテスト"""
        # 入社日のみ入力、社員番号なし
        form_data = {
            'regist_status': self.regist_status_1.pk,
            'employee_no': '',  # 社員番号なし
            'name_last': '田中',
            'name_first': '太郎',
            'name_kana_last': 'タナカ',
            'name_kana_first': 'タロウ',
            'birth_date': date(1990, 1, 1),
            'sex': '1',
            'hire_date': date(2020, 4, 1),  # 入社日あり
            'postal_code': '1000001',
            'address1': '東京都千代田区千代田',
            'phone': '03-1234-5678',
            'email': 'tanaka@example.com'
        }
        
        form = StaffForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('入社日を入力する場合は、社員番号も入力してください', str(form.errors))
    
    def test_employee_no_hire_date_validation_both_required(self):
        """社員番号のみ入力、入社日なしのバリデーションテスト"""
        form_data = {
            'regist_status': self.regist_status_1.pk,
            'employee_no': 'EMP001',  # 社員番号あり
            'name_last': '田中',
            'name_first': '太郎',
            'name_kana_last': 'タナカ',
            'name_kana_first': 'タロウ',
            'birth_date': date(1990, 1, 1),
            'sex': '1',
            'hire_date': '',  # 入社日なし
            'postal_code': '1000001',
            'address1': '東京都千代田区千代田',
            'phone': '03-1234-5678',
            'email': 'tanaka@example.com'
        }
        
        form = StaffForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('社員番号を入力する場合は、入社日も入力してください', str(form.errors))
    
    def test_resignation_date_without_hire_date_validation(self):
        """入社日なしに退職日入力のバリデーションテスト"""
        form_data = {
            'regist_status': self.regist_status_1.pk,
            'employee_no': '',
            'name_last': '田中',
            'name_first': '太郎',
            'name_kana_last': 'タナカ',
            'name_kana_first': 'タロウ',
            'birth_date': date(1990, 1, 1),
            'sex': '1',
            'hire_date': '',  # 入社日なし
            'resignation_date': date(2024, 12, 31),  # 退職日あり
            'postal_code': '1000001',
            'address1': '東京都千代田区千代田',
            'phone': '03-1234-5678',
            'email': 'tanaka@example.com'
        }
        
        form = StaffForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('退職日を入力する場合は、入社日も入力してください', str(form.errors))
    
    def test_valid_both_empty_hire_date_employee_no(self):
        """入社日・社員番号ともに空白の場合は有効（契約なしスタッフ）"""
        form_data = {
            'regist_status': self.regist_status_1.pk,
            'employee_no': '',  # 社員番号なし
            'name_last': '佐藤',
            'name_first': '花子',
            'name_kana_last': 'サトウ',
            'name_kana_first': 'ハナコ',
            'birth_date': date(1992, 5, 15),
            'sex': '2',
            'hire_date': '',  # 入社日なし
            'postal_code': '1000002',
            'address1': '東京都千代田区丸の内',
            'phone': '03-9876-5432',
            'email': 'sato1@example.com'  # 異なるメールアドレス
        }
        
        form = StaffForm(data=form_data)
        if not form.is_valid():
            print(f"Form errors: {form.errors}")
        self.assertTrue(form.is_valid())
    
    def test_valid_both_filled_hire_date_employee_no(self):
        """入社日・社員番号ともに入力済みの場合は有効（正社員スタッフ）"""
        form_data = {
            'regist_status': self.regist_status_1.pk,
            'employee_no': 'EMP002',  # 異なる社員番号
            'employment_type': self.employment_type_1.pk,  # 雇用形態を追加
            'name_last': '鈴木',
            'name_first': '一郎',
            'name_kana_last': 'スズキ',
            'name_kana_first': 'イチロウ',
            'birth_date': date(1988, 3, 10),
            'sex': '1',
            'hire_date': date(2021, 4, 1),  # 入社日あり
            'postal_code': '1000003',
            'address1': '東京都千代田区有楽町',
            'phone': '03-1111-2222',
            'email': 'suzuki@example.com'  # 異なるメールアドレス
        }
        
        form = StaffForm(data=form_data)
        if not form.is_valid():
            print(f"Form errors: {form.errors}")
        self.assertTrue(form.is_valid())
    
    def test_valid_resignation_date_with_hire_date(self):
        """入社日入力後の退職日入力は有効"""
        form_data = {
            'regist_status': self.regist_status_1.pk,
            'employee_no': 'EMP003',
            'employment_type': self.employment_type_2.pk,  # 雇用形態を追加
            'name_last': '高橋',
            'name_first': '美咲',
            'name_kana_last': 'タカハシ',
            'name_kana_first': 'ミサキ',
            'birth_date': date(1995, 7, 20),
            'sex': '2',
            'hire_date': date(2022, 4, 1),  # 入社日あり
            'resignation_date': date(2024, 12, 31),  # 退職日あり
            'postal_code': '1000004',
            'address1': '東京都千代田区神田',
            'phone': '03-3333-4444',
            'email': 'takahashi@example.com'  # 異なるメールアドレス
        }
        
        form = StaffForm(data=form_data)
        if not form.is_valid():
            print(f"Form errors: {form.errors}")
        self.assertTrue(form.is_valid())
    
    def test_hire_date_after_resignation_date_validation(self):
        """入社日が退職日より後の場合のバリデーションテスト（既存テスト）"""
        form_data = {
            'regist_status': self.regist_status_1.pk,
            'employee_no': 'EMP004',
            'employment_type': self.employment_type_1.pk,  # 雇用形態を追加
            'name_last': '山田',
            'name_first': '次郎',
            'name_kana_last': 'ヤマダ',
            'name_kana_first': 'ジロウ',
            'birth_date': date(1985, 12, 5),
            'sex': '1',
            'hire_date': date(2024, 12, 31),  # 入社日が後
            'resignation_date': date(2020, 4, 1),  # 退職日が前
            'postal_code': '1000005',
            'address1': '東京都千代田区内幸町',
            'phone': '03-5555-6666',
            'email': 'yamada@example.com'  # 異なるメールアドレス
        }
        
        form = StaffForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('入社日は退職日より前の日付を入力してください', str(form.errors))
    
    def test_hire_date_without_employment_type_validation(self):
        """入社日のみ入力、雇用形態なしのバリデーションテスト"""
        form_data = {
            'regist_status': self.regist_status_1.pk,
            'employee_no': 'EMP005',
            'employment_type': '',  # 雇用形態なし
            'name_last': '田中',
            'name_first': '太郎',
            'name_kana_last': 'タナカ',
            'name_kana_first': 'タロウ',
            'birth_date': date(1990, 1, 1),
            'sex': '1',
            'hire_date': date(2020, 4, 1),  # 入社日あり
            'postal_code': '1000001',
            'address1': '東京都千代田区千代田',
            'phone': '03-1234-5678',
            'email': 'tanaka2@example.com'
        }
        
        form = StaffForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('入社日を入力する場合は、雇用形態も選択してください', str(form.errors))
    
    def test_employment_type_without_hire_date_validation(self):
        """雇用形態のみ選択、入社日なしのバリデーションテスト"""
        form_data = {
            'regist_status': self.regist_status_1.pk,
            'employee_no': '',
            'employment_type': self.employment_type_1.pk,  # 雇用形態あり
            'name_last': '田中',
            'name_first': '太郎',
            'name_kana_last': 'タナカ',
            'name_kana_first': 'タロウ',
            'birth_date': date(1990, 1, 1),
            'sex': '1',
            'hire_date': '',  # 入社日なし
            'postal_code': '1000001',
            'address1': '東京都千代田区千代田',
            'phone': '03-1234-5678',
            'email': 'tanaka3@example.com'
        }
        
        form = StaffForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('雇用形態を選択する場合は、入社日も入力してください', str(form.errors))
    
    def test_valid_all_three_fields_filled(self):
        """入社日・社員番号・雇用形態すべて入力済みの場合は有効"""
        form_data = {
            'regist_status': self.regist_status_1.pk,
            'employee_no': 'EMP006',
            'employment_type': self.employment_type_3.pk,  # 派遣社員
            'name_last': '佐藤',
            'name_first': '花子',
            'name_kana_last': 'サトウ',
            'name_kana_first': 'ハナコ',
            'birth_date': date(1992, 5, 15),
            'sex': '2',
            'hire_date': date(2023, 4, 1),
            'postal_code': '1000002',
            'address1': '東京都千代田区丸の内',
            'phone': '03-9876-5432',
            'email': 'sato2@example.com'
        }
        
        form = StaffForm(data=form_data)
        if not form.is_valid():
            print(f"Form errors: {form.errors}")
        self.assertTrue(form.is_valid())