from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from apps.contract.forms import StaffContractForm
from apps.contract.models import ClientContract, ClientContractHaken
from apps.staff.models import Staff, StaffInternational
from apps.client.models import Client
from apps.master.models import ContractPattern, JobCategory, EmploymentType, OvertimePattern
from apps.master.models_worktime import WorkTimePattern
from apps.system.settings.models import Dropdowns
from apps.common.constants import Constants

User = get_user_model()


class StaffContractFormValidationTest(TestCase):
    """スタッフ契約フォームの新しいバリデーションテスト"""

    def setUp(self):
        """テストデータのセットアップ"""
        self.user = User.objects.create_user(username='testuser', password='testpass')
        
        # 雇用形態
        self.fixed_term_employment = EmploymentType.objects.create(
            name='有期雇用',
            is_fixed_term=True,
            is_active=True
        )
        
        self.indefinite_employment = EmploymentType.objects.create(
            name='無期雇用',
            is_fixed_term=False,
            is_active=True
        )
        
        # 職種（特定技能対応・農業漁業派遣対応）
        self.job_category_skilled_agri = JobCategory.objects.create(
            name='特定技能・農業漁業派遣対応職種',
            is_specified_skilled_worker=True,
            is_agriculture_fishery_dispatch=True,
            is_active=True
        )
        
        # 職種（特定技能対応・農業漁業派遣非対応）
        self.job_category_skilled_only = JobCategory.objects.create(
            name='特定技能対応職種',
            is_specified_skilled_worker=True,
            is_agriculture_fishery_dispatch=False,
            is_active=True
        )
        
        # 職種（特定技能非対応）
        self.job_category_normal = JobCategory.objects.create(
            name='通常職種',
            is_specified_skilled_worker=False,
            is_agriculture_fishery_dispatch=False,
            is_active=True
        )
        
        # 外国籍スタッフ
        self.foreign_staff = Staff.objects.create(
            name_last='外国籍',
            name_first='太郎',
            birth_date=date(1990, 1, 1),
            hire_date=date(2020, 1, 1),
            employment_type=self.fixed_term_employment,
            created_by=self.user,
            updated_by=self.user
        )
        
        # 外国籍情報
        self.international_info = StaffInternational.objects.create(
            staff=self.foreign_staff,
            residence_card_number='AB1234567890',
            residence_status='特定技能',
            residence_period_from=date.today() - timedelta(days=365),
            residence_period_to=date.today() + timedelta(days=365),
            created_by=self.user,
            updated_by=self.user
        )
        
        # 日本人スタッフ
        self.japanese_staff = Staff.objects.create(
            name_last='日本人',
            name_first='花子',
            birth_date=date(1990, 1, 1),
            hire_date=date(2020, 1, 1),
            employment_type=self.fixed_term_employment,
            created_by=self.user,
            updated_by=self.user
        )
        
        # 契約パターン
        self.contract_pattern = ContractPattern.objects.create(
            name='テスト契約パターン',
            domain=Constants.DOMAIN.STAFF,
            is_active=True
        )
        
        # クライアント契約パターン
        self.client_contract_pattern = ContractPattern.objects.create(
            name='テストクライアント契約パターン',
            domain=Constants.DOMAIN.CLIENT,
            is_active=True
        )
        
        # 支払単位
        self.pay_unit = Dropdowns.objects.create(
            category='pay_unit',
            value='10',
            name='月給',
            active=True
        )
        
        # 就業時間パターン
        self.worktime_pattern = WorkTimePattern.objects.create(
            name='標準勤務',
            is_active=True
        )
        
        # 時間外算出パターン
        self.overtime_pattern = OvertimePattern.objects.create(
            name='標準時間外算出',
            calculation_type='premium',
            is_active=True
        )
        
        # クライアント
        self.client = Client.objects.create(
            name='テストクライアント',
            created_by=self.user,
            updated_by=self.user
        )
        
        # 派遣クライアント契約
        self.dispatch_client_contract = ClientContract.objects.create(
            contract_name='派遣契約',
            client=self.client,
            contract_pattern=self.client_contract_pattern,
            client_contract_type_code=Constants.CLIENT_CONTRACT_TYPE.DISPATCH,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=90),
            created_by=self.user,
            updated_by=self.user
        )
        
        # 派遣情報
        ClientContractHaken.objects.create(
            client_contract=self.dispatch_client_contract,
            limit_indefinite_or_senior=Constants.LIMIT_BY_AGREEMENT.NOT_LIMITED,
            created_by=self.user,
            updated_by=self.user
        )
        
        # 非派遣クライアント契約（準委任として作成）
        self.non_dispatch_client_contract = ClientContract.objects.create(
            contract_name='非派遣契約',
            client=self.client,
            contract_pattern=self.client_contract_pattern,
            client_contract_type_code='10',  # 準委任
            start_date=date.today(),
            end_date=date.today() + timedelta(days=90),
            created_by=self.user,
            updated_by=self.user
        )

    def _get_base_form_data(self, staff, employment_type, job_category, start_date=None, end_date=None):
        """基本的なフォームデータを取得"""
        return {
            'staff': staff.pk,
            'employment_type': employment_type.pk,
            'contract_name': 'テスト契約',
            'job_category': job_category.pk,
            'contract_pattern': self.contract_pattern.pk,
            'start_date': start_date or date.today(),
            'end_date': end_date or (date.today() + timedelta(days=30)),
            'contract_amount': 200000,
            'pay_unit': '10',
            'work_location': 'テスト勤務地',
            'business_content': 'テスト業務内容',
            'worktime_pattern': self.worktime_pattern.pk,
            'overtime_pattern': self.overtime_pattern.pk,
        }

    def test_foreign_staff_dispatch_agriculture_fishery_valid(self):
        """外国籍スタッフの派遣契約で農業漁業派遣対応職種の場合は成功する"""
        form_data = self._get_base_form_data(
            self.foreign_staff, 
            self.fixed_term_employment, 
            self.job_category_skilled_agri
        )
        
        form = StaffContractForm(data=form_data, client_contract=self.dispatch_client_contract)
        
        self.assertTrue(form.is_valid(), f"フォームエラー: {form.errors}")

    def test_foreign_staff_dispatch_not_agriculture_fishery_invalid(self):
        """外国籍スタッフの派遣契約で農業漁業派遣非対応職種の場合はエラーになる"""
        form_data = self._get_base_form_data(
            self.foreign_staff, 
            self.fixed_term_employment, 
            self.job_category_skilled_only
        )
        
        form = StaffContractForm(data=form_data, client_contract=self.dispatch_client_contract)
        
        self.assertFalse(form.is_valid())
        self.assertIn('job_category', form.errors)
        self.assertIn('農業漁業派遣該当の職種を選択してください', str(form.errors['job_category']))

    def test_foreign_staff_non_dispatch_no_agriculture_fishery_check(self):
        """外国籍スタッフの非派遣契約では農業漁業派遣チェックをスキップする"""
        form_data = self._get_base_form_data(
            self.foreign_staff, 
            self.fixed_term_employment, 
            self.job_category_skilled_only
        )
        
        form = StaffContractForm(data=form_data, client_contract=self.non_dispatch_client_contract)
        
        self.assertTrue(form.is_valid(), f"フォームエラー: {form.errors}")

    def test_japanese_staff_no_agriculture_fishery_check(self):
        """日本人スタッフでは農業漁業派遣チェックをスキップする"""
        form_data = self._get_base_form_data(
            self.japanese_staff, 
            self.fixed_term_employment, 
            self.job_category_skilled_only
        )
        
        form = StaffContractForm(data=form_data, client_contract=self.dispatch_client_contract)
        
        self.assertTrue(form.is_valid(), f"フォームエラー: {form.errors}")

    def test_contract_period_staff_start_after_client_end_invalid(self):
        """スタッフ契約開始日がクライアント契約終了日より後の場合はエラーになる"""
        client_end_date = date.today() + timedelta(days=30)
        staff_start_date = client_end_date + timedelta(days=1)
        staff_end_date = staff_start_date + timedelta(days=10)  # 開始日より後に設定
        
        # クライアント契約の終了日を設定
        self.dispatch_client_contract.end_date = client_end_date
        self.dispatch_client_contract.save()
        
        form_data = self._get_base_form_data(
            self.japanese_staff, 
            self.fixed_term_employment, 
            self.job_category_normal,
            start_date=staff_start_date,
            end_date=staff_end_date
        )
        
        form = StaffContractForm(data=form_data, client_contract=self.dispatch_client_contract)
        
        self.assertFalse(form.is_valid())
        self.assertIn('start_date', form.errors)
        self.assertIn('クライアント契約終了日', str(form.errors['start_date']))

    def test_contract_period_staff_end_before_client_start_invalid(self):
        """スタッフ契約終了日がクライアント契約開始日より前の場合はエラーになる"""
        client_start_date = date.today() + timedelta(days=10)
        staff_end_date = client_start_date - timedelta(days=1)
        
        # クライアント契約の開始日を設定
        self.dispatch_client_contract.start_date = client_start_date
        self.dispatch_client_contract.save()
        
        form_data = self._get_base_form_data(
            self.japanese_staff, 
            self.fixed_term_employment, 
            self.job_category_normal,
            end_date=staff_end_date
        )
        
        form = StaffContractForm(data=form_data, client_contract=self.dispatch_client_contract)
        
        self.assertFalse(form.is_valid())
        self.assertIn('end_date', form.errors)
        self.assertIn('クライアント契約開始日', str(form.errors['end_date']))

    def test_contract_period_overlap_valid(self):
        """スタッフ契約とクライアント契約の期間が重複する場合は成功する"""
        client_start_date = date.today()
        client_end_date = date.today() + timedelta(days=60)
        staff_start_date = date.today() + timedelta(days=10)
        staff_end_date = date.today() + timedelta(days=50)
        
        # クライアント契約の期間を設定
        self.dispatch_client_contract.start_date = client_start_date
        self.dispatch_client_contract.end_date = client_end_date
        self.dispatch_client_contract.save()
        
        form_data = self._get_base_form_data(
            self.japanese_staff, 
            self.fixed_term_employment, 
            self.job_category_normal,
            start_date=staff_start_date,
            end_date=staff_end_date
        )
        
        form = StaffContractForm(data=form_data, client_contract=self.dispatch_client_contract)
        
        self.assertTrue(form.is_valid(), f"フォームエラー: {form.errors}")

    def test_normal_staff_contract_no_client_contract_checks(self):
        """通常のスタッフ契約作成（client_contract=None）では追加チェックが実行されない"""
        form_data = self._get_base_form_data(
            self.foreign_staff, 
            self.fixed_term_employment, 
            self.job_category_skilled_only  # 農業漁業派遣非対応だが、チェックされない
        )
        
        form = StaffContractForm(data=form_data, client_contract=None)
        
        self.assertTrue(form.is_valid(), f"フォームエラー: {form.errors}")

    def test_foreign_staff_residence_period_exceeded_invalid(self):
        """外国籍スタッフの契約終了日が在留期限を超える場合はエラーになる"""
        # 在留期限を短く設定
        self.international_info.residence_period_to = date.today() + timedelta(days=10)
        self.international_info.save()
        
        form_data = self._get_base_form_data(
            self.foreign_staff, 
            self.fixed_term_employment, 
            self.job_category_skilled_agri,
            end_date=date.today() + timedelta(days=20)  # 在留期限を超える
        )
        
        form = StaffContractForm(data=form_data, client_contract=self.dispatch_client_contract)
        
        self.assertFalse(form.is_valid())
        self.assertIn('end_date', form.errors)
        self.assertIn('在留期限', str(form.errors['end_date']))

    def test_foreign_staff_not_specified_skilled_worker_invalid(self):
        """外国籍スタッフで特定技能外国人受入非該当職種の場合はエラーになる"""
        form_data = self._get_base_form_data(
            self.foreign_staff, 
            self.fixed_term_employment, 
            self.job_category_normal  # 特定技能非対応
        )
        
        form = StaffContractForm(data=form_data, client_contract=self.dispatch_client_contract)
        
        self.assertFalse(form.is_valid())
        self.assertIn('job_category', form.errors)
        self.assertIn('特定技能外国人受入該当の職種を選択してください', str(form.errors['job_category']))