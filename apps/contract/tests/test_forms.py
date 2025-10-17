from django.test import TestCase
from django.contrib.auth import get_user_model
from django import forms
from apps.client.models import Client as ClientModel
from apps.staff.models import Staff
from apps.master.models import JobCategory, ContractPattern, Dropdowns
from ..models import ClientContract, StaffContract
from ..forms import ClientContractForm, StaffContractForm
from apps.common.constants import Constants
from datetime import date

User = get_user_model()

class ContractFormTest(TestCase):
    """契約フォームのテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # テスト用クライアント（基本契約締結日あり）
        self.client_obj = ClientModel.objects.create(
            name='テストクライアント株式会社',
            corporate_number='4000000000001',
            basic_contract_date=date(2024, 1, 1),
            created_by=self.user,
            updated_by=self.user
        )
        self.client_without_cn = ClientModel.objects.create(
            name='法人番号なしクライアント',
            corporate_number=None,
            basic_contract_date=date(2024, 1, 1),
            created_by=self.user,
            updated_by=self.user
        )
        
        # テスト用スタッフ（社員番号・入社日あり）
        self.staff = Staff.objects.create(
            name_last='田中',
            name_first='太郎',
            employee_no='EMP001',
            hire_date=date(2024, 4, 1),
            created_by=self.user,
            updated_by=self.user
        )

        self.job_category = JobCategory.objects.create(name='エンジニア', is_active=True)
        self.client_pattern = ContractPattern.objects.create(name='クライアント向け基本契約', domain='10', contract_type_code='10', is_active=True)
        self.staff_pattern = ContractPattern.objects.create(name='スタッフ向け雇用契約', domain='1', is_active=True)
        self.bill_unit = Dropdowns.objects.create(category='bill_unit', value='10', name='月額', active=True)
        self.pay_unit = Dropdowns.objects.create(category='pay_unit', value='10', name='月給', active=True)

    def test_client_contract_form_with_new_fields(self):
        """クライアント契約フォーム（新しいフィールドあり）のテスト"""
        form = ClientContractForm(initial={'client_contract_type_code': self.client_pattern.contract_type_code})
        self.assertIn('job_category', form.fields)
        self.assertIn('contract_pattern', form.fields)

        # 契約書パターンの選択肢がクライアント向けのものだけになっているか確認
        patterns = form.fields['contract_pattern'].queryset
        self.assertIn(self.client_pattern, patterns)
        self.assertNotIn(self.staff_pattern, patterns)

        form_data = {
            'client': self.client_obj.pk,
            'contract_name': 'フォームテスト契約',
            'job_category': self.job_category.pk,
            'contract_pattern': self.client_pattern.pk,
            'start_date': date(2024, 2, 1),
            'end_date': date(2024, 12, 31),
            'client_contract_type_code': self.client_pattern.contract_type_code,
            'bill_unit': self.bill_unit.value,
        }
        form = ClientContractForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        instance = form.save()
        self.assertEqual(instance.job_category, self.job_category)
        self.assertEqual(instance.contract_pattern, self.client_pattern)

    def test_staff_contract_form_with_new_fields(self):
        """スタッフ契約フォーム（新しいフィールドあり）のテスト"""
        form = StaffContractForm()
        self.assertIn('job_category', form.fields)
        self.assertIn('contract_pattern', form.fields)

        # 契約書パターンの選択肢がスタッフ向けのものだけになっているか確認
        patterns = form.fields['contract_pattern'].queryset
        self.assertNotIn(self.client_pattern, patterns)
        self.assertIn(self.staff_pattern, patterns)

        form_data = {
            'staff': self.staff.pk,
            'contract_name': 'フォームテスト雇用契約',
            'job_category': self.job_category.pk,
            'contract_pattern': self.staff_pattern.pk,
            'start_date': date(2024, 5, 1),
            'end_date': date(2024, 12, 31),
            'pay_unit': self.pay_unit.value,
            'work_location': 'テスト就業場所',
            'business_content': 'テスト業務内容',
        }
        form = StaffContractForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        instance = form.save()
        self.assertEqual(instance.job_category, self.job_category)
        self.assertEqual(instance.contract_pattern, self.staff_pattern)
        self.assertEqual(instance.work_location, 'テスト就業場所')
        self.assertEqual(instance.business_content, 'テスト業務内容')
    
    def test_client_contract_form_initial_display_new(self):
        """クライアント契約フォーム新規作成時の初期表示テスト"""
        form = ClientContractForm()
        
        # client_displayフィールドの初期値は空
        self.assertEqual(form.fields['client_display'].initial, None)
        
        # clientフィールドは隠しフィールド
        self.assertIsInstance(form.fields['client'].widget, forms.HiddenInput)
    
    def test_client_contract_form_initial_display_edit(self):
        """クライアント契約フォーム編集時の初期表示テスト"""
        # 既存の契約を作成
        contract = ClientContract.objects.create(
            client=self.client_obj,
            contract_name='既存契約',
            start_date=date(2024, 2, 1),
            end_date=date(2024, 12, 31),
            contract_amount=1000000,
            created_by=self.user,
            updated_by=self.user,
            contract_pattern=self.client_pattern
        )
        
        # 編集用フォームを作成
        form = ClientContractForm(instance=contract)
        
        # client_displayフィールドにクライアント名が設定される
        self.assertEqual(form.fields['client_display'].initial, 'テストクライアント株式会社')
        
        # clientフィールドに既存のクライアントIDが設定される
        self.assertEqual(form.initial['client'], self.client_obj.pk)
    
    def test_staff_contract_form_initial_display_new(self):
        """スタッフ契約フォーム新規作成時の初期表示テスト"""
        form = StaffContractForm()
        
        # staff_displayフィールドの初期値は空
        self.assertEqual(form.fields['staff_display'].initial, None)
        
        # staffフィールドは隠しフィールド
        self.assertIsInstance(form.fields['staff'].widget, forms.HiddenInput)
    
    def test_staff_contract_form_initial_display_edit(self):
        """スタッフ契約フォーム編集時の初期表示テスト"""
        # 既存の契約を作成
        contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name='雇用契約',
            start_date=date(2024, 4, 1),
            end_date=date(2024, 12, 31),
            contract_amount=300000,
            created_by=self.user,
            updated_by=self.user,
            contract_pattern=self.staff_pattern
        )
        
        # 編集用フォームを作成
        form = StaffContractForm(instance=contract)
        
        # staff_displayフィールドにスタッフ名が設定される
        self.assertEqual(form.fields['staff_display'].initial, '田中 太郎')
        
        # staffフィールドに既存のスタッフIDが設定される
        self.assertEqual(form.initial['staff'], self.staff.pk)
    
    def test_client_contract_form_validation_with_basic_contract_date(self):
        """クライアント契約フォームの基本契約締結日バリデーションテスト"""
        form_data = {
            'client': self.client_obj.pk,
            'contract_name': 'テスト契約',
            'start_date': date(2023, 12, 1),  # 基本契約締結日より前
            'end_date': date(2024, 12, 31),
            'contract_amount': 1000000,
            'contract_pattern': self.client_pattern.pk,
            'job_category': self.job_category.pk,
            'client_contract_type_code': self.client_pattern.contract_type_code,
            'bill_unit': self.bill_unit.value,
        }
        
        form = ClientContractForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('start_date', form.errors)
        self.assertIn('基本契約締結日', str(form.errors['start_date']))
    
    def test_staff_contract_form_validation_with_hire_date(self):
        """スタッフ契約フォームの入社日バリデーションテスト"""
        form_data = {
            'staff': self.staff.pk,
            'contract_name': '雇用契約',
            'start_date': date(2024, 3, 1),  # 入社日より前
            'end_date': date(2024, 12, 31),
            'contract_amount': 300000,
            'contract_pattern': self.staff_pattern.pk,
            'pay_unit': self.pay_unit.value,
        }
        
        form = StaffContractForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('start_date', form.errors)
        self.assertIn('入社日', str(form.errors['start_date']))
    
    def test_client_contract_form_valid_data(self):
        """クライアント契約フォームの正常データテスト"""
        form_data = {
            'client': self.client_obj.pk,
            'contract_name': 'テスト契約',
            'start_date': date(2024, 2, 1),  # 基本契約締結日以降
            'end_date': date(2024, 12, 31),
            'contract_amount': 1000000,
            'contract_pattern': self.client_pattern.pk,
            'client_contract_type_code': self.client_pattern.contract_type_code,
            'bill_unit': self.bill_unit.value,
        }
        
        form = ClientContractForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_client_contract_form_with_bill_unit(self):
        """クライアント契約フォームの請求単位フィールドテスト"""
        from apps.system.settings.models import Dropdowns
        bill_unit_monthly = Dropdowns.objects.create(category='bill_unit', value='10', name='月額', active=True)

        # フォームの初期化とフィールド確認
        form = ClientContractForm(initial={'client_contract_type_code': self.client_pattern.contract_type_code})
        self.assertIn('bill_unit', form.fields)
        self.assertIn((bill_unit_monthly.value, bill_unit_monthly.name), form.fields['bill_unit'].choices)

        # フォームにデータを渡してバリデーション
        form_data = {
            'client': self.client_obj.pk,
            'contract_name': '請求単位テスト契約',
            'job_category': self.job_category.pk,
            'contract_pattern': self.client_pattern.pk,
            'start_date': date(2024, 2, 1),
            'end_date': date(2024, 12, 31),
            'contract_amount': 500000,
            'bill_unit': bill_unit_monthly.value,
            'client_contract_type_code': self.client_pattern.contract_type_code,
        }
        form = ClientContractForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)

        # 保存してインスタンスを確認
        instance = form.save()
        self.assertEqual(instance.bill_unit, bill_unit_monthly.value)

    def test_staff_contract_form_with_pay_unit(self):
        """スタッフ契約フォームの支払単位フィールドテスト"""
        from apps.system.settings.models import Dropdowns
        pay_unit_daily = Dropdowns.objects.create(category='pay_unit', value='20', name='日給', active=True)

        # フォームの初期化とフィールド確認
        form = StaffContractForm()
        self.assertIn('pay_unit', form.fields)
        self.assertIn((pay_unit_daily.value, pay_unit_daily.name), form.fields['pay_unit'].choices)

        # フォームにデータを渡してバリデーション
        form_data = {
            'staff': self.staff.pk,
            'contract_name': '支払単位テスト契約',
            'job_category': self.job_category.pk,
            'contract_pattern': self.staff_pattern.pk,
            'start_date': date(2024, 5, 1),
            'end_date': date(2024, 12, 31),
            'contract_amount': 30000,
            'pay_unit': pay_unit_daily.value,
        }
        form = StaffContractForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)

        # 保存してインスタンスを確認
        instance = form.save()
        self.assertEqual(instance.pay_unit, pay_unit_daily.value)
    
    def test_staff_contract_form_valid_data(self):
        """スタッフ契約フォームの正常データテスト"""
        form_data = {
            'staff': self.staff.pk,
            'contract_name': '雇用契約',
            'start_date': date(2024, 4, 1),  # 入社日以降
            'end_date': date(2024, 12, 31),
            'contract_amount': 300000,
            'contract_pattern': self.staff_pattern.pk,
            'pay_unit': self.pay_unit.value,
        }
        form = StaffContractForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_client_contract_form_validation_for_client_without_corporate_number(self):
        """法人番号のないクライアントを選択した場合のバリデーションテスト"""
        form_data = {
            'client': self.client_without_cn.pk,
            'contract_name': '法人番号なしテスト契約',
            'job_category': self.job_category.pk,
            'contract_pattern': self.client_pattern.pk,
            'start_date': date(2024, 2, 1),
            'end_date': date(2024, 12, 31),
            'client_contract_type_code': self.client_pattern.contract_type_code,
            'bill_unit': self.bill_unit.value,
        }
        form = ClientContractForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('client', form.errors)
        self.assertEqual(form.errors['client'][0], '法人番号が設定されていないクライアントは選択できません。')


class ContractFormDisplayTest(TestCase):
    """契約フォーム表示機能のテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # テスト用クライアント（基本契約締結日あり）
        self.client_obj = ClientModel.objects.create(
            name='株式会社テストクライアント',
            corporate_number='4000000000002',
            basic_contract_date=date(2024, 1, 1),
            created_by=self.user,
            updated_by=self.user
        )
        
        # テスト用スタッフ（社員番号・入社日あり）
        self.staff = Staff.objects.create(
            name_last='山田',
            name_first='花子',
            employee_no='EMP002',
            hire_date=date(2024, 3, 1),
            created_by=self.user,
            updated_by=self.user
        )
    
    def test_client_contract_form_display_field_setup(self):
        """クライアント契約フォームの表示フィールド設定テスト"""
        # 新規作成時
        form = ClientContractForm()
        
        # client_displayフィールドが存在し、適切に設定されている
        self.assertIn('client_display', form.fields)
        self.assertFalse(form.fields['client_display'].required)
        self.assertEqual(form.fields['client_display'].widget.attrs.get('readonly'), True)
        self.assertEqual(form.fields['client_display'].widget.attrs.get('placeholder'), 'クライアントを選択してください')
        
        # clientフィールドが隠しフィールドになっている
        self.assertIsInstance(form.fields['client'].widget, forms.HiddenInput)
    
    def test_staff_contract_form_display_field_setup(self):
        """スタッフ契約フォームの表示フィールド設定テスト"""
        # 新規作成時
        form = StaffContractForm()
        
        # staff_displayフィールドが存在し、適切に設定されている
        self.assertIn('staff_display', form.fields)
        self.assertFalse(form.fields['staff_display'].required)
        self.assertEqual(form.fields['staff_display'].widget.attrs.get('readonly'), True)
        self.assertEqual(form.fields['staff_display'].widget.attrs.get('placeholder'), 'スタッフを選択してください')
        
        # staffフィールドが隠しフィールドになっている
        self.assertIsInstance(form.fields['staff'].widget, forms.HiddenInput)
    
    def test_client_contract_form_edit_display_initialization(self):
        """クライアント契約フォーム編集時の表示初期化テスト"""
        # 既存の契約を作成
        self.client_pattern = ContractPattern.objects.create(name='クライアント向け基本契約', domain='10', contract_type_code='10', is_active=True)
        contract = ClientContract.objects.create(
            client=self.client_obj,
            contract_name='表示テスト契約',
            start_date=date(2024, 2, 1),
            end_date=date(2024, 12, 31),
            contract_amount=500000,
            created_by=self.user,
            updated_by=self.user,
            contract_pattern=self.client_pattern
        )
        
        # 編集用フォームを作成
        form = ClientContractForm(instance=contract)
        
        # client_displayフィールドにクライアント名が正しく設定される
        self.assertEqual(form.fields['client_display'].initial, '株式会社テストクライアント')
        
        # フォームの初期データにクライアントIDが設定される
        self.assertEqual(form.initial['client'], self.client_obj.pk)
        
        # その他のフィールドも正しく設定される
        self.assertEqual(form.initial['contract_name'], '表示テスト契約')
        self.assertEqual(form.initial['contract_amount'], 500000)
    
    def test_staff_contract_form_edit_display_initialization(self):
        """スタッフ契約フォーム編集時の表示初期化テスト"""
        # 既存の契約を作成
        self.staff_pattern = ContractPattern.objects.create(name='スタッフ向け雇用契約', domain='1', is_active=True)
        contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name='表示テスト雇用契約',
            start_date=date(2024, 4, 1),
            end_date=date(2024, 12, 31),
            contract_amount=280000,
            created_by=self.user,
            updated_by=self.user,
            contract_pattern=self.staff_pattern
        )
        
        # 編集用フォームを作成
        form = StaffContractForm(instance=contract)
        
        # staff_displayフィールドにスタッフ名が正しく設定される
        self.assertEqual(form.fields['staff_display'].initial, '山田 花子')
        
        # フォームの初期データにスタッフIDが設定される
        self.assertEqual(form.initial['staff'], self.staff.pk)
        
        # その他のフィールドも正しく設定される
        self.assertEqual(form.initial['contract_name'], '表示テスト雇用契約')
        self.assertEqual(form.initial['contract_amount'], 280000)
    
    def test_client_contract_form_display_with_special_characters(self):
        """クライアント契約フォームの特殊文字を含む名前の表示テスト"""
        # 特殊文字を含むクライアント名
        special_client = ClientModel.objects.create(
            name='株式会社"テスト&クライアント"<script>',
            corporate_number='4000000000003',
            basic_contract_date=date(2024, 1, 1),
            created_by=self.user,
            updated_by=self.user
        )
        
        self.client_pattern = ContractPattern.objects.create(name='クライアント向け基本契約', domain='10', contract_type_code='10', is_active=True)
        contract = ClientContract.objects.create(
            client=special_client,
            contract_name='特殊文字テスト契約',
            start_date=date(2024, 2, 1),
            end_date=date(2024, 12, 31),
            contract_amount=100000,
            created_by=self.user,
            updated_by=self.user,
            contract_pattern=self.client_pattern
        )
        
        form = ClientContractForm(instance=contract)
        
        # 特殊文字を含む名前も正しく設定される
        self.assertEqual(form.fields['client_display'].initial, '株式会社"テスト&クライアント"<script>')
    
    def test_staff_contract_form_display_with_special_characters(self):
        """スタッフ契約フォームの特殊文字を含む名前の表示テスト"""
        # 特殊文字を含むスタッフ名
        special_staff = Staff.objects.create(
            name_last='田中"太郎"',
            name_first='<花子>',
            employee_no='EMP003',
            hire_date=date(2024, 3, 1),
            created_by=self.user,
            updated_by=self.user
        )
        
        self.staff_pattern = ContractPattern.objects.create(name='スタッフ向け雇用契約', domain='1', is_active=True)
        contract = StaffContract.objects.create(
            staff=special_staff,
            contract_name='特殊文字テスト雇用契約',
            start_date=date(2024, 4, 1),
            end_date=date(2024, 12, 31),
            contract_amount=200000,
            created_by=self.user,
            updated_by=self.user,
            contract_pattern=self.staff_pattern
        )
        
        form = StaffContractForm(instance=contract)
        
        # 特殊文字を含む名前も正しく設定される
        self.assertEqual(form.fields['staff_display'].initial, '田中"太郎" <花子>')
    
    def test_client_contract_form_display_without_client(self):
        """クライアント契約フォームでクライアントが未設定の場合のテスト"""
        # クライアントが設定されていない契約（通常は発生しないが、データ整合性テスト）
        form = ClientContractForm()
        
        # client_displayフィールドの初期値は空
        self.assertIsNone(form.fields['client_display'].initial)
    
    def test_staff_contract_form_display_without_staff(self):
        """スタッフ契約フォームでスタッフが未設定の場合のテスト"""
        # スタッフが設定されていない契約（通常は発生しないが、データ整合性テスト）
        form = StaffContractForm()
        
        # staff_displayフィールドの初期値は空
        self.assertIsNone(form.fields['staff_display'].initial)


class StaffContractFormStatusTest(TestCase):
    """スタッフ契約フォームのステータス別制御のテスト"""
    def setUp(self):
        """テストデータの準備"""
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.staff = Staff.objects.create(
            name_last='Test',
            name_first='User',
            hire_date=date(2024, 1, 1)
        )
        self.base_data = {
            'staff': self.staff.pk,
            'contract_name': 'Test Contract',
            'start_date': date(2024, 1, 1),
            'end_date': date(2024, 12, 31),
        }


    def test_form_draft_status_fields_enabled(self):
        """ステータスが作成中の場合にフィールドが有効かテスト"""
        self.staff_pattern = ContractPattern.objects.create(name='スタッフ向け雇用契約', domain='1', is_active=True)
        contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name='Draft Contract',
            start_date=date(2024, 1, 1),
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            contract_pattern=self.staff_pattern
        )
        form = StaffContractForm(instance=contract)
        for field_name, field in form.fields.items():
            self.assertIsNone(field.widget.attrs.get('disabled'))


class StaffContractFormMinimumWageValidationTest(TestCase):
    """スタッフ契約フォームの最低賃金バリデーションテスト"""

    def setUp(self):
        """テストデータの準備"""
        User = get_user_model()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.staff = Staff.objects.create(
            name_last='テスト',
            name_first='スタッフ',
            employee_no='EMP001',
            hire_date=date(2024, 4, 1),
            created_by=self.user,
            updated_by=self.user
        )
        self.job_category = JobCategory.objects.create(name='エンジニア', is_active=True)
        self.staff_pattern = ContractPattern.objects.create(name='スタッフ向け雇用契約', domain='1', is_active=True)

        # Dropdowns for pay_unit
        self.pay_unit_hourly = Dropdowns.objects.create(category='pay_unit', value='10', name='時給', active=True)
        self.pay_unit_monthly = Dropdowns.objects.create(category='pay_unit', value='30', name='月給', active=True)

        # Dropdowns for prefecture
        self.tokyo_pref = Dropdowns.objects.create(category='pref', value='13', name='東京都', active=True)

        # MinimumPay data
        from apps.master.models import MinimumPay
        MinimumPay.objects.create(pref='13', start_date=date(2023, 10, 1), hourly_wage=1113, is_active=True)

        self.base_form_data = {
            'staff': self.staff.pk,
            'contract_name': '最低賃金テスト契約',
            'job_category': self.job_category.pk,
            'contract_pattern': self.staff_pattern.pk,
            'start_date': date(2024, 5, 1),
            'end_date': date(2024, 12, 31),
            'pay_unit': self.pay_unit_hourly.value,
            'work_location': '東京都新宿区',
        }

    def test_minimum_wage_validation_success(self):
        """最低賃金バリデーション成功テスト（最低賃金以上）"""
        form_data = self.base_form_data.copy()
        form_data['contract_amount'] = 1200

        form = StaffContractForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_minimum_wage_validation_failure(self):
        """最低賃金バリデーション失敗テスト（最低賃金未満）"""
        form_data = self.base_form_data.copy()
        form_data['contract_amount'] = 1000

        form = StaffContractForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('contract_amount', form.errors)
        self.assertIn('東京都の最低賃金（1113円）を下回っています。', str(form.errors['contract_amount']))

    def test_minimum_wage_validation_no_prefecture(self):
        """最低賃金バリデーションスキップテスト（勤務地に都道府県なし）"""
        form_data = self.base_form_data.copy()
        form_data['work_location'] = '新宿区'
        form_data['contract_amount'] = 1000 # This would fail if validation ran

        form = StaffContractForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_minimum_wage_validation_not_hourly(self):
        """最低賃金バリデーションスキップテスト（時給でない）"""
        form_data = self.base_form_data.copy()
        form_data['pay_unit'] = self.pay_unit_monthly.value
        form_data['contract_amount'] = 1000 # This would fail if validation ran

        form = StaffContractForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
