# -*- coding: utf-8 -*-
"""
契約アサインの外国籍情報バリデーションテスト
"""
from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from apps.staff.models import Staff, StaffInternational
from apps.client.models import Client, ClientDepartment
from apps.contract.models import ClientContract, StaffContract, ContractAssignment, ClientContractHaken
from apps.master.models import JobCategory, ContractPattern, EmploymentType, StaffRegistStatus
from apps.common.constants import Constants


class ContractAssignmentForeignValidationTest(TestCase):
    """契約アサインの外国籍情報バリデーションテスト"""

    def setUp(self):
        """テストデータのセットアップ"""
        # Dropdownsデータ作成
        from apps.system.settings.models import Dropdowns
        
        # 契約状況のドロップダウン
        Dropdowns.objects.create(
            category='contract_status',
            value='1',
            name='作成中',
            disp_seq=1,
            active=True
        )
        
        # 支払単位のドロップダウン
        Dropdowns.objects.create(
            category='pay_unit',
            value='30',
            name='月給',
            disp_seq=3,
            active=True
        )

        # クライアント契約種別のドロップダウン
        Dropdowns.objects.create(
            category='client_contract_type',
            value='20',
            name='派遣',
            disp_seq=2,
            active=True
        )

        # スタッフ登録ステータス作成
        self.regist_status = StaffRegistStatus.objects.create(
            name='正社員',
            is_active=True
        )

        # 雇用形態作成
        self.employment_type = EmploymentType.objects.create(
            name='正社員',
            is_fixed_term=False,
            is_active=True
        )

        # 契約書パターン作成
        self.staff_pattern = ContractPattern.objects.create(
            name='スタッフ標準契約',
            domain=Constants.DOMAIN.STAFF,
            is_active=True
        )
        
        self.client_pattern = ContractPattern.objects.create(
            name='クライアント標準契約',
            domain=Constants.DOMAIN.CLIENT,
            is_active=True
        )

        # 職種作成（特定技能外国人受入該当 + 農業漁業派遣該当）
        self.job_category_skilled_agri = JobCategory.objects.create(
            name='特定技能対応農業職種',
            is_specified_skilled_worker=True,
            is_agriculture_fishery_dispatch=True,
            is_active=True
        )

        # 職種作成（特定技能外国人受入該当のみ）
        self.job_category_skilled_only = JobCategory.objects.create(
            name='特定技能対応職種',
            is_specified_skilled_worker=True,
            is_agriculture_fishery_dispatch=False,
            is_active=True
        )

        # 職種作成（農業漁業派遣該当のみ）
        self.job_category_agri_only = JobCategory.objects.create(
            name='農業派遣職種',
            is_specified_skilled_worker=False,
            is_agriculture_fishery_dispatch=True,
            is_active=True
        )

        # 職種作成（どちらも非該当）
        self.job_category_normal = JobCategory.objects.create(
            name='一般職種',
            is_specified_skilled_worker=False,
            is_agriculture_fishery_dispatch=False,
            is_active=True
        )

        # クライアント作成
        self.client = Client.objects.create(
            name='テストクライアント',
            corporate_number='1234567890123'
        )

        # クライアント部署作成
        self.client_department = ClientDepartment.objects.create(
            client=self.client,
            name='テスト部署',
            valid_from=date.today() - timedelta(days=365),
            valid_to=date.today() + timedelta(days=365)
        )

        # 外国籍スタッフ作成
        self.foreign_staff = Staff.objects.create(
            name_last='Smith',
            name_first='John',
            name_kana_last='スミス',
            name_kana_first='ジョン',
            email='smith@example.com',
            birth_date=date(1985, 5, 15),
            hire_date=date(2020, 4, 1),
            regist_status=self.regist_status,
            employment_type=self.employment_type
        )

        # 外国籍情報作成
        self.international_info = StaffInternational.objects.create(
            staff=self.foreign_staff,
            residence_card_number='AB1234567890',
            residence_status='特定技能',
            residence_period_from=date.today() - timedelta(days=365),
            residence_period_to=date.today() + timedelta(days=300)  # 300日後まで有効
        )

        # 日本人スタッフ作成
        self.japanese_staff = Staff.objects.create(
            name_last='田中',
            name_first='太郎',
            name_kana_last='タナカ',
            name_kana_first='タロウ',
            email='tanaka@example.com',
            birth_date=date(1990, 1, 1),
            hire_date=date(2020, 4, 1),
            regist_status=self.regist_status,
            employment_type=self.employment_type
        )

    def _create_client_contract(self, contract_type_code='20', end_date=None):
        """クライアント契約を作成するヘルパーメソッド"""
        if end_date is None:
            end_date = date.today() + timedelta(days=180)
            
        return ClientContract.objects.create(
            client=self.client,
            client_contract_type_code=contract_type_code,
            contract_name='テストクライアント契約',
            job_category=self.job_category_skilled_agri,
            contract_pattern=self.client_pattern,
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            start_date=date.today(),
            end_date=end_date,
            contract_amount=500000
        )

    def _create_staff_contract(self, staff, job_category, end_date=None):
        """スタッフ契約を作成するヘルパーメソッド"""
        if end_date is None:
            end_date = date.today() + timedelta(days=180)
            
        return StaffContract.objects.create(
            staff=staff,
            employment_type=self.employment_type,
            contract_name='テストスタッフ契約',
            job_category=job_category,
            contract_pattern=self.staff_pattern,
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            start_date=date.today(),
            end_date=end_date,
            contract_amount=300000,
            pay_unit='30'
        )

    def test_japanese_staff_assignment_no_validation(self):
        """日本人スタッフのアサインでは外国籍バリデーションが実行されないことを確認"""
        client_contract = self._create_client_contract()
        staff_contract = self._create_staff_contract(self.japanese_staff, self.job_category_normal)
        
        assignment = ContractAssignment(
            client_contract=client_contract,
            staff_contract=staff_contract
        )
        
        # バリデーションエラーが発生しないことを確認
        try:
            assignment.clean()
        except ValidationError:
            self.fail("日本人スタッフのアサインでバリデーションエラーが発生しました")

    def test_foreign_staff_valid_assignment(self):
        """外国籍スタッフで適切な職種・期限の場合は正常にアサインできることを確認"""
        client_contract = self._create_client_contract()
        staff_contract = self._create_staff_contract(
            self.foreign_staff, 
            self.job_category_skilled_agri,
            date.today() + timedelta(days=180)  # 在留期限内
        )
        
        assignment = ContractAssignment(
            client_contract=client_contract,
            staff_contract=staff_contract
        )
        
        # バリデーションエラーが発生しないことを確認
        try:
            assignment.clean()
        except ValidationError:
            self.fail("適切な条件でバリデーションエラーが発生しました")

    def test_foreign_staff_residence_period_exceeded(self):
        """外国籍スタッフの割当終了日が在留期限を超える場合はエラーになることを確認"""
        # 在留期限より後に終了するクライアント契約を作成
        client_contract = self._create_client_contract(
            end_date=date.today() + timedelta(days=400)  # 在留期限（300日後）を超える
        )
        staff_contract = self._create_staff_contract(
            self.foreign_staff, 
            self.job_category_skilled_agri,
            date.today() + timedelta(days=400)  # 在留期限を超える
        )
        
        assignment = ContractAssignment(
            client_contract=client_contract,
            staff_contract=staff_contract
        )
        
        with self.assertRaises(ValidationError) as cm:
            assignment.clean()
        
        self.assertIn('在留期限', str(cm.exception))
        self.assertIn('を超えています', str(cm.exception))

    def test_foreign_staff_not_specified_skilled_worker(self):
        """外国籍スタッフで特定技能外国人受入非該当職種の場合はエラーになることを確認"""
        client_contract = self._create_client_contract()
        staff_contract = self._create_staff_contract(
            self.foreign_staff, 
            self.job_category_normal,  # 特定技能非対応
            date.today() + timedelta(days=180)
        )
        
        assignment = ContractAssignment(
            client_contract=client_contract,
            staff_contract=staff_contract
        )
        
        with self.assertRaises(ValidationError) as cm:
            assignment.clean()
        
        self.assertIn('特定技能外国人受入該当の職種を選択してください', str(cm.exception))

    def test_foreign_staff_dispatch_not_agriculture_fishery(self):
        """外国籍スタッフの派遣契約で農業漁業派遣非該当職種の場合はエラーになることを確認"""
        client_contract = self._create_client_contract(contract_type_code='20')  # 派遣
        staff_contract = self._create_staff_contract(
            self.foreign_staff, 
            self.job_category_skilled_only,  # 特定技能対応だが農業漁業派遣非対応
            date.today() + timedelta(days=180)
        )
        
        assignment = ContractAssignment(
            client_contract=client_contract,
            staff_contract=staff_contract
        )
        
        with self.assertRaises(ValidationError) as cm:
            assignment.clean()
        
        self.assertIn('農業漁業派遣該当の職種を選択してください', str(cm.exception))

    def test_foreign_staff_non_dispatch_contract_valid(self):
        """外国籍スタッフの非派遣契約では農業漁業派遣チェックをスキップすることを確認"""
        client_contract = self._create_client_contract(contract_type_code='10')  # 非派遣
        staff_contract = self._create_staff_contract(
            self.foreign_staff, 
            self.job_category_skilled_only,  # 特定技能対応だが農業漁業派遣非対応
            date.today() + timedelta(days=180)
        )
        
        assignment = ContractAssignment(
            client_contract=client_contract,
            staff_contract=staff_contract
        )
        
        # 非派遣契約なので農業漁業派遣チェックはスキップされ、エラーにならない
        try:
            assignment.clean()
        except ValidationError:
            self.fail("非派遣契約で農業漁業派遣チェックが実行されました")

    def test_foreign_staff_no_job_category_error(self):
        """外国籍スタッフで職種が未設定の場合はエラーになることを確認"""
        client_contract = self._create_client_contract()
        staff_contract = self._create_staff_contract(
            self.foreign_staff, 
            None,  # 職種未設定
            date.today() + timedelta(days=180)
        )
        
        assignment = ContractAssignment(
            client_contract=client_contract,
            staff_contract=staff_contract
        )
        
        # 職種が未設定の場合、特定技能チェックでエラーになる
        with self.assertRaises(ValidationError) as cm:
            assignment.clean()
        
        self.assertIn('特定技能外国人受入該当の職種を選択してください', str(cm.exception))

    def test_multiple_validation_errors(self):
        """複数のバリデーションエラーが同時に発生する場合を確認"""
        client_contract = self._create_client_contract(contract_type_code='20')  # 派遣
        staff_contract = self._create_staff_contract(
            self.foreign_staff, 
            self.job_category_normal,  # 特定技能非対応かつ農業漁業派遣非対応
            date.today() + timedelta(days=400)  # 在留期限を超える
        )
        
        assignment = ContractAssignment(
            client_contract=client_contract,
            staff_contract=staff_contract
        )
        
        with self.assertRaises(ValidationError) as cm:
            assignment.clean()
        
        # 最初に検出されるエラー（在留期限チェック）が表示される
        error_message = str(cm.exception)
        self.assertTrue(
            '在留期限' in error_message or '特定技能外国人受入該当' in error_message,
            f"期待されるエラーメッセージが含まれていません: {error_message}"
        )