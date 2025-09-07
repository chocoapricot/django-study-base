from django.test import TestCase
from django.contrib.auth import get_user_model
from django import forms
from apps.client.models import Client as ClientModel
from apps.staff.models import Staff
from apps.master.models import JobCategory, ContractPattern
from ..models import ClientContract, StaffContract
from ..forms import ClientContractForm, StaffContractForm
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
        self.client_pattern = ContractPattern.objects.create(name='クライアント向け基本契約', contract_type='client', is_active=True)
        self.staff_pattern = ContractPattern.objects.create(name='スタッフ向け雇用契約', contract_type='staff', is_active=True)

    def test_client_contract_form_with_new_fields(self):
        """クライアント契約フォーム（新しいフィールドあり）のテスト"""
        form = ClientContractForm()
        self.assertIn('job_category', form.fields)
        self.assertIn('contract_pattern', form.fields)

        # 契約パターンの選択肢がクライアント向けのものだけになっているか確認
        patterns = form.fields['contract_pattern'].queryset
        self.assertIn(self.client_pattern, patterns)
        self.assertNotIn(self.staff_pattern, patterns)

        form_data = {
            'client': self.client_obj.pk,
            'contract_name': 'フォームテスト契約',
            'job_category': self.job_category.pk,
            'contract_pattern': self.client_pattern.pk,
            'contract_type': 'service',
            'start_date': date(2024, 2, 1),
            'end_date': date(2024, 12, 31),
            'is_active': True,
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

        # 契約パターンの選択肢がスタッフ向けのものだけになっているか確認
        patterns = form.fields['contract_pattern'].queryset
        self.assertNotIn(self.client_pattern, patterns)
        self.assertIn(self.staff_pattern, patterns)

        form_data = {
            'staff': self.staff.pk,
            'contract_name': 'フォームテスト雇用契約',
            'job_category': self.job_category.pk,
            'contract_pattern': self.staff_pattern.pk,
            'contract_type': 'full_time',
            'start_date': date(2024, 5, 1),
            'end_date': date(2024, 12, 31),
            'is_active': True,
        }
        form = StaffContractForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        instance = form.save()
        self.assertEqual(instance.job_category, self.job_category)
        self.assertEqual(instance.contract_pattern, self.staff_pattern)
    
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
            contract_type='service',
            start_date=date(2024, 2, 1),
            end_date=date(2024, 12, 31),
            contract_amount=1000000,
            created_by=self.user,
            updated_by=self.user
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
            contract_type='full_time',
            start_date=date(2024, 4, 1),
            end_date=date(2024, 12, 31),
            contract_amount=300000,
            created_by=self.user,
            updated_by=self.user
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
            'contract_type': 'service',
            'start_date': date(2023, 12, 1),  # 基本契約締結日より前
            'end_date': date(2024, 12, 31),
            'contract_amount': 1000000,
            'is_active': True
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
            'contract_type': 'full_time',
            'start_date': date(2024, 3, 1),  # 入社日より前
            'end_date': date(2024, 12, 31),
            'contract_amount': 300000,
            'is_active': True
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
            'contract_type': 'service',
            'start_date': date(2024, 2, 1),  # 基本契約締結日以降
            'end_date': date(2024, 12, 31),
            'contract_amount': 1000000,
            'is_active': True
        }
        
        form = ClientContractForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_staff_contract_form_valid_data(self):
        """スタッフ契約フォームの正常データテスト"""
        form_data = {
            'staff': self.staff.pk,
            'contract_name': '雇用契約',
            'contract_type': 'full_time',
            'start_date': date(2024, 4, 1),  # 入社日以降
            'end_date': date(2024, 12, 31),
            'contract_amount': 300000,
            'is_active': True
        }
        
        form = StaffContractForm(data=form_data)
        self.assertTrue(form.is_valid())


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
        contract = ClientContract.objects.create(
            client=self.client_obj,
            contract_name='表示テスト契約',
            contract_type='service',
            start_date=date(2024, 2, 1),
            end_date=date(2024, 12, 31),
            contract_amount=500000,
            created_by=self.user,
            updated_by=self.user
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
        contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name='表示テスト雇用契約',
            contract_type='full_time',
            start_date=date(2024, 4, 1),
            end_date=date(2024, 12, 31),
            contract_amount=280000,
            created_by=self.user,
            updated_by=self.user
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
            basic_contract_date=date(2024, 1, 1),
            created_by=self.user,
            updated_by=self.user
        )
        
        contract = ClientContract.objects.create(
            client=special_client,
            contract_name='特殊文字テスト契約',
            contract_type='service',
            start_date=date(2024, 2, 1),
            end_date=date(2024, 12, 31),
            contract_amount=100000,
            created_by=self.user,
            updated_by=self.user
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
        
        contract = StaffContract.objects.create(
            staff=special_staff,
            contract_name='特殊文字テスト雇用契約',
            contract_type='part_time',
            start_date=date(2024, 4, 1),
            end_date=date(2024, 12, 31),
            contract_amount=200000,
            created_by=self.user,
            updated_by=self.user
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
