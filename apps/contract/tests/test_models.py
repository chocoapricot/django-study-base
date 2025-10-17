from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.master.models import JobCategory, ContractPattern
from django.utils import timezone
from datetime import timedelta
from apps.client.models import Client as ClientModel
from apps.staff.models import Staff
from ..models import ClientContract, StaffContract

User = get_user_model()

class ContractModelTest(TestCase):
    """契約モデルのテスト"""

    def setUp(self):
        """テストデータの準備"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # テスト用クライアント
        self.client_obj = ClientModel.objects.create(
            name='テストクライアント',
            created_by=self.user,
            updated_by=self.user
        )

        # テスト用スタッフ
        self.staff = Staff.objects.create(
            name_last='田中',
            name_first='太郎',
            created_by=self.user,
            updated_by=self.user
        )

        self.job_category = JobCategory.objects.create(name='エンジニア', is_active=True)
        self.client_pattern = ContractPattern.objects.create(name='クライアント向け基本契約', domain='10', is_active=True)
        self.staff_pattern = ContractPattern.objects.create(name='スタッフ向け雇用契約', domain='1', is_active=True)

    def test_client_contract_with_new_fields(self):
        """クライアント契約モデル（新しいフィールドあり）のテスト"""
        contract = ClientContract.objects.create(
            client=self.client_obj,
            contract_name='新機能テスト契約',
            job_category=self.job_category,
            contract_pattern=self.client_pattern,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=365),
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(contract.job_category, self.job_category)
        self.assertEqual(contract.contract_pattern, self.client_pattern)

    def test_staff_contract_with_new_fields(self):
        """スタッフ契約モデル（新しいフィールドあり）のテスト"""
        contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name='新機能テスト雇用契約',
            job_category=self.job_category,
            contract_pattern=self.staff_pattern,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=365),
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(contract.job_category, self.job_category)
        self.assertEqual(contract.contract_pattern, self.staff_pattern)

    def test_client_contract_creation(self):
        """クライアント契約の作成テスト"""
        contract = ClientContract.objects.create(
            client=self.client_obj,
            contract_name='テスト契約',
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=365),
            contract_amount=1000000,
            created_by=self.user,
            updated_by=self.user,
            contract_pattern=self.client_pattern
        )

        self.assertEqual(contract.client, self.client_obj)
        self.assertEqual(contract.contract_name, 'テスト契約')

    def test_staff_contract_creation(self):
        """スタッフ契約の作成テスト"""
        contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name='雇用契約',
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=365),
            contract_amount=300000,
            created_by=self.user,
            updated_by=self.user,
            contract_pattern=self.staff_pattern
        )

        self.assertEqual(contract.staff, self.staff)
        self.assertEqual(contract.contract_name, '雇用契約')

    def test_staff_contract_with_work_location_and_business_content(self):
        """スタッフ契約モデルに就業場所と業務内容が保存されることをテスト"""
        work_location_text = "東京都千代田区"
        business_content_text = "システム開発"
        contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name='雇用契約（就業場所・業務内容あり）',
            start_date=timezone.now().date(),
            work_location=work_location_text,
            business_content=business_content_text,
            created_by=self.user,
            updated_by=self.user,
            contract_pattern=self.staff_pattern
        )
        self.assertEqual(contract.work_location, work_location_text)
        self.assertEqual(contract.business_content, business_content_text)


from django.core.exceptions import ValidationError
from datetime import date
from apps.company.models import Company
from ..models import ClientContract, ClientContractHaken, ClientContractTtp
from apps.system.settings.models import Dropdowns
from apps.client.models import ClientDepartment

class ClientContractModelPropertyTests(TestCase):
    def setUp(self):
        # 必要なオブジェクトを作成
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='password')
        self.company = Company.objects.create(name='Test Company', corporate_number='1234567890123')
        self.client = ClientModel.objects.create(
            name='Test Client',
            created_by=self.user,
            corporate_number=self.company.corporate_number
        )
        self.contract_pattern = ContractPattern.objects.create(
            domain='10', name='Test Pattern', contract_type_code='20'
        )
        Dropdowns.objects.create(category='client_contract_type', value='20', name='派遣')
        Dropdowns.objects.create(category='client_contract_type', value='10', name='準委任')

    def test_contract_type_display_name(self):
        """TTP情報に基づいて契約種別の表示名が正しく変わることをテストする"""
        # 1. 派遣契約（TTPなし）
        contract_haken = ClientContract.objects.create(
            client=self.client,
            contract_name='Haken Contract',
            client_contract_type_code='20',
            contract_pattern=self.contract_pattern,
            start_date=date(2023, 1, 1),
            created_by=self.user,
        )
        self.assertEqual(contract_haken.contract_type_display_name, '派遣')

        # 2. 派遣契約（TTPあり）
        haken_info = ClientContractHaken.objects.create(client_contract=contract_haken)
        ClientContractTtp.objects.create(haken=haken_info)
        # refresh_from_dbは関連オブジェクトのキャッシュを更新しないため、再度オブジェクトを取得
        contract_haken_with_ttp = ClientContract.objects.get(pk=contract_haken.pk)
        self.assertEqual(contract_haken_with_ttp.contract_type_display_name, '派遣（TTP）')

        # 3. 派遣以外の契約
        contract_other = ClientContract.objects.create(
            client=self.client,
            contract_name='Other Contract',
            client_contract_type_code='10',  # 準委任
            contract_pattern=self.contract_pattern,
            start_date=date(2023, 1, 1),
            created_by=self.user,
        )
        self.assertEqual(contract_other.contract_type_display_name, '準委任')


class ContractAssignmentValidationTest(TestCase):
    """ContractAssignmentモデルのバリデーションテスト"""

    def setUp(self):
        """テストデータの準備"""
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client = ClientModel.objects.create(
            name='テストクライアント',
            corporate_number='1234567890123',
            created_by=self.user
        )
        self.haken_unit = ClientDepartment.objects.create(
            client=self.client,
            name='テスト派遣部署',
            created_by=self.user
        )
        self.client_pattern = ContractPattern.objects.create(
            name='テスト契約パターン',
            domain='10',  # Client
            contract_type_code='20', # Haken
            is_active=True
        )
        self.staff_pattern = ContractPattern.objects.create(name='スタッフ向け基本契約', domain='1', is_active=True)
        from apps.master.models import EmploymentType
        self.employment_type_fixed = EmploymentType.objects.create(name='派遣社員(有期)', is_fixed_term=True)
        self.employment_type_indefinite = EmploymentType.objects.create(name='派遣社員(無期)', is_fixed_term=False)


    def test_conflict_date_validation(self):
        """割当終了日が抵触日を超える場合にValidationErrorが発生することを確認"""
        from ..models import ContractAssignment

        # 60歳未満のスタッフ（抵触日チェック対象）
        staff_under_60 = Staff.objects.create(
            name_last='テスト', name_first='スタッフ', email='test@example.com', 
            birth_date=date.today() - timedelta(days=30*365),  # 30歳
            created_by=self.user
        )

        # 60歳以上のスタッフ（抵触日チェック対象外）
        staff_over_60 = Staff.objects.create(
            name_last='ベテラン', name_first='スタッフ', email='veteran@example.com',
            birth_date=date.today() - timedelta(days=65*365),  # 65歳
            created_by=self.user
        )

        # --- 抵触日を超えるケース（60歳未満の有期雇用スタッフ） ---
        client_contract_ng = ClientContract.objects.create(
            client=self.client,
            contract_name='長期派遣契約',
            client_contract_type_code='20',  # 派遣
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365 * 4), # 4年後
            created_by=self.user,
            contract_pattern=self.client_pattern
        )
        ClientContractHaken.objects.create(client_contract=client_contract_ng, haken_unit=self.haken_unit)

        staff_contract_ng = StaffContract.objects.create(
            staff=staff_under_60,
            contract_name='長期スタッフ契約',
            employment_type=self.employment_type_fixed,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365 * 4), # 4年後
            created_by=self.user,
            contract_pattern=self.staff_pattern
        )

        assignment_ng = ContractAssignment(
            client_contract=client_contract_ng,
            staff_contract=staff_contract_ng,
            created_by=self.user,
            updated_by=self.user
        )

        with self.assertRaises(ValidationError):
            assignment_ng.full_clean()

        # --- 60歳以上のスタッフは抵触日チェック対象外 ---
        staff_contract_over_60 = StaffContract.objects.create(
            staff=staff_over_60,
            contract_name='長期スタッフ契約（60歳以上）',
            employment_type=self.employment_type_fixed,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365 * 4), # 4年後
            created_by=self.user,
            contract_pattern=self.staff_pattern
        )

        assignment_over_60 = ContractAssignment(
            client_contract=client_contract_ng,
            staff_contract=staff_contract_over_60,
            created_by=self.user,
            updated_by=self.user
        )

        try:
            assignment_over_60.full_clean()
            assignment_over_60.save()
        except ValidationError:
            self.fail("60歳以上のスタッフで抵触日チェックが実行されました。")

        # --- 抵触日を超えないケース ---
        client_contract_ok = ClientContract.objects.create(
            client=self.client,
            contract_name='短期派遣契約',
            client_contract_type_code='20',  # 派遣
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365), # 1年後
            created_by=self.user,
            contract_pattern=self.client_pattern
        )
        ClientContractHaken.objects.create(client_contract=client_contract_ok, haken_unit=self.haken_unit)

        staff_contract_ok = StaffContract.objects.create(
            staff=staff_under_60,
            contract_name='短期スタッフ契約',
            employment_type=self.employment_type_fixed,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365), # 1年後
            created_by=self.user,
            contract_pattern=self.staff_pattern
        )

        assignment_ok = ContractAssignment(
            client_contract=client_contract_ok,
            staff_contract=staff_contract_ok,
            created_by=self.user,
            updated_by=self.user
        )

        try:
            assignment_ok.full_clean()
            assignment_ok.save()
        except ValidationError:
            self.fail("抵触日を超えない場合にValidationErrorが発生しました。")

    def test_age_boundary_for_conflict_date_validation(self):
        """60歳の境界値での抵触日チェックをテスト"""
        from ..models import ContractAssignment

        # 60歳ちょうどのスタッフ（抵触日チェック対象外）
        # より正確な60歳の計算（うるう年を考慮）
        from dateutil.relativedelta import relativedelta
        today = date.today()
        birth_date_60 = today - relativedelta(years=60)
        staff_exactly_60 = Staff.objects.create(
            name_last='境界', name_first='スタッフ', email='boundary@example.com',
            birth_date=birth_date_60,
            created_by=self.user
        )

        # 59歳のスタッフ（抵触日チェック対象）
        birth_date_59 = today - relativedelta(years=59)
        staff_59 = Staff.objects.create(
            name_last='若手', name_first='スタッフ', email='young@example.com',
            birth_date=birth_date_59,
            created_by=self.user
        )

        # 長期契約（4年）
        client_contract_long = ClientContract.objects.create(
            client=self.client,
            contract_name='長期派遣契約',
            client_contract_type_code='20',  # 派遣
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365 * 4), # 4年後
            created_by=self.user,
            contract_pattern=self.client_pattern
        )
        ClientContractHaken.objects.create(client_contract=client_contract_long, haken_unit=self.haken_unit)

        # 60歳ちょうどのスタッフは抵触日チェック対象外
        staff_contract_60 = StaffContract.objects.create(
            staff=staff_exactly_60,
            contract_name='60歳スタッフ契約',
            employment_type=self.employment_type_fixed,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365 * 4), # 4年後
            created_by=self.user,
            contract_pattern=self.staff_pattern
        )

        assignment_60 = ContractAssignment(
            client_contract=client_contract_long,
            staff_contract=staff_contract_60,
            created_by=self.user,
            updated_by=self.user
        )

        try:
            assignment_60.full_clean()
            assignment_60.save()
        except ValidationError:
            self.fail("60歳ちょうどのスタッフで抵触日チェックが実行されました。")

        # 59歳のスタッフは抵触日チェック対象
        staff_contract_59 = StaffContract.objects.create(
            staff=staff_59,
            contract_name='59歳スタッフ契約',
            employment_type=self.employment_type_fixed,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365 * 4), # 4年後
            created_by=self.user,
            contract_pattern=self.staff_pattern
        )

        assignment_59 = ContractAssignment(
            client_contract=client_contract_long,
            staff_contract=staff_contract_59,
            created_by=self.user,
            updated_by=self.user
        )

        with self.assertRaises(ValidationError):
            assignment_59.full_clean()

    def test_senior_limited_contract_validation(self):
        """無期雇用又は60歳以上限定契約のバリデーションをテスト"""
        from ..models import ContractAssignment, ClientContractHaken, Constants

        # --- テストデータ準備 ---
        staff_under_60_fixed = Staff.objects.create(
            name_last='若手', name_first='有期', email='s1@test.com',
            birth_date=date.today() - timedelta(days=30*365) # 30歳
        )
        staff_under_60_indefinite = Staff.objects.create(
            name_last='若手', name_first='無期', email='s2@test.com',
            birth_date=date.today() - timedelta(days=30*365) # 30歳
        )
        staff_over_60_fixed = Staff.objects.create(
            name_last='ベテラン', name_first='有期', email='s3@test.com',
            birth_date=date.today() - timedelta(days=65*365) # 65歳
        )
        staff_over_60_indefinite = Staff.objects.create(
            name_last='ベテラン', name_first='無期', email='s4@test.com',
            birth_date=date.today() - timedelta(days=65*365) # 65歳
        )

        client_contract_limited = ClientContract.objects.create(
            client=self.client, contract_name='限定契約', client_contract_type_code='20',
            start_date=date.today(), contract_pattern=self.client_pattern, created_by=self.user
        )
        ClientContractHaken.objects.create(
            client_contract=client_contract_limited, haken_unit=self.haken_unit,
            limit_indefinite_or_senior=Constants.LIMIT_BY_AGREEMENT.LIMITED
        )

        # --- テスト実行 ---
        test_cases = [
            # staff, employment_type, expected_pass, message
            (staff_under_60_fixed, self.employment_type_fixed, False, "NG: 60歳未満・有期"),
            (staff_under_60_indefinite, self.employment_type_indefinite, True, "OK: 60歳未満・無期"),
            (staff_over_60_fixed, self.employment_type_fixed, True, "OK: 60歳以上・有期"),
            (staff_over_60_indefinite, self.employment_type_indefinite, True, "OK: 60歳以上・無期"),
        ]

        for staff, emp_type, expected_pass, message in test_cases:
            with self.subTest(message):
                staff_contract = StaffContract.objects.create(
                    staff=staff, contract_name=f'契約_{staff.email}', start_date=date.today(),
                    end_date=date.today() + timedelta(days=365),
                    employment_type=emp_type, contract_pattern=self.staff_pattern, created_by=self.user
                )
                assignment = ContractAssignment(
                    client_contract=client_contract_limited,
                    staff_contract=staff_contract,
                    created_by=self.user,
                    updated_by=self.user
                )
                if expected_pass:
                    try:
                        assignment.full_clean()
                    except ValidationError:
                        self.fail(f"{message} でValidationErrorが発生しました。")
                else:
                    with self.assertRaises(ValidationError, msg=f"{message} でValidationErrorが発生しませんでした。"):
                        assignment.full_clean()
