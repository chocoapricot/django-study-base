# apps/contract/tests/test_teishokubi_calculator.py

from datetime import date
from django.test import TestCase
from apps.staff.models import Staff
from apps.client.models import Client, ClientDepartment
from apps.contract.models import ClientContract, StaffContract, ContractAssignment, ClientContractHaken, StaffContractTeishokubi
from apps.master.models import ContractPattern
from apps.system.settings.models import Dropdowns

class TeishokubiCalculatorTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # Dropdowns for contract types and domains
        Dropdowns.objects.create(category='client_contract_type', name='派遣', value='20', disp_seq=1)
        Dropdowns.objects.create(category='domain', name='クライアント', value='10', disp_seq=2)
        
        # 雇用形態マスタを作成
        from apps.master.models import EmploymentType
        cls.employment_type_fixed = EmploymentType.objects.create(
            name='派遣社員(有期)',
            display_order=30,
            is_fixed_term=True,
            is_active=True
        )
        cls.employment_type_indefinite = EmploymentType.objects.create(
            name='派遣社員(無期)',
            display_order=35,
            is_fixed_term=False,
            is_active=True
        )

        # Required ContractPattern
        cls.contract_pattern = ContractPattern.objects.create(
            name='Test Pattern',
            domain='10' # クライアント
        )

        # Common objects
        cls.staff = Staff.objects.create(
            name_last='Test',
            name_first='Staff',
            email='teststaff@example.com',
            employment_type=cls.employment_type_fixed  # 派遣社員(有期)
        )
        cls.client_instance = Client.objects.create(
            name='Test Client',
            corporate_number='1234567890123'
        )
        cls.department = ClientDepartment.objects.create(
            client=cls.client_instance,
            name='Test Department'
        )

    def _create_contracts_and_assignment(self, client_start, client_end, staff_start, staff_end, contract_name):
        """Helper to create contracts and an assignment."""
        client_contract = ClientContract.objects.create(
            client=self.client_instance,
            contract_name=f'Client Contract {contract_name}',
            start_date=client_start,
            end_date=client_end,
            client_contract_type_code='20', # 派遣
            contract_pattern=self.contract_pattern
        )
        ClientContractHaken.objects.create(
            client_contract=client_contract,
            haken_unit=self.department
        )
        staff_contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name=f'Staff Contract {contract_name}',
            start_date=staff_start,
            end_date=staff_end,
            employment_type=self.employment_type_fixed  # 派遣社員(有期)
        )
        ContractAssignment.objects.create(
            client_contract=client_contract,
            staff_contract=staff_contract
        )
        return client_contract, staff_contract

    def test_single_assignment_creates_teishokubi(self):
        """単一の割り当てで抵触日が正しく作成されることをテスト"""
        self._create_contracts_and_assignment(
            client_start=date(2020, 1, 1), client_end=date(2020, 12, 31),
            staff_start=date(2020, 1, 1), staff_end=date(2020, 12, 31),
            contract_name="A"
        )

        teishokubi = StaffContractTeishokubi.objects.get(staff_email=self.staff.email)
        self.assertEqual(teishokubi.dispatch_start_date, date(2020, 1, 1))
        self.assertEqual(teishokubi.conflict_date, date(2023, 1, 1))

    def test_multiple_assignments_small_gap(self):
        """3ヶ月未満のギャップがある複数の割り当てで、派遣開始日がリセットされないことをテスト"""
        # Assignment A: 2020-01-01 to 2020-12-31
        self._create_contracts_and_assignment(
            client_start=date(2020, 1, 1), client_end=date(2020, 12, 31),
            staff_start=date(2020, 1, 1), staff_end=date(2020, 12, 31),
            contract_name="A"
        )
        # Assignment B: 2021-03-31 (Gap is less than 3 months + 1 day)
        self._create_contracts_and_assignment(
            client_start=date(2021, 3, 31), client_end=date(2021, 12, 31),
            staff_start=date(2021, 3, 31), staff_end=date(2021, 12, 31),
            contract_name="B"
        )

        teishokubi = StaffContractTeishokubi.objects.get(staff_email=self.staff.email)
        self.assertEqual(teishokubi.dispatch_start_date, date(2020, 1, 1))
        self.assertEqual(teishokubi.conflict_date, date(2023, 1, 1))

    def test_multiple_assignments_large_gap(self):
        """3ヶ月と1日以上のギャップがある複数の割り当てで、派遣開始日がリセットされることをテスト"""
        # Assignment A: 2020-01-01 to 2020-12-31
        self._create_contracts_and_assignment(
            client_start=date(2020, 1, 1), client_end=date(2020, 12, 31),
            staff_start=date(2020, 1, 1), staff_end=date(2020, 12, 31),
            contract_name="A"
        )
        # Assignment B: 2021-04-01 (Gap is 3 months + 1 day from 2020-12-31)
        self._create_contracts_and_assignment(
            client_start=date(2021, 4, 1), client_end=date(2021, 12, 31),
            staff_start=date(2021, 4, 1), staff_end=date(2021, 12, 31),
            contract_name="B"
        )

        teishokubi = StaffContractTeishokubi.objects.get(staff_email=self.staff.email)
        self.assertEqual(teishokubi.dispatch_start_date, date(2021, 4, 1))
        self.assertEqual(teishokubi.conflict_date, date(2024, 4, 1))

    def test_assignment_deletion_recalculates(self):
        """割り当てが削除された後、抵触日が再計算されることをテスト"""
        # Assignment A: 2020-01-01
        self._create_contracts_and_assignment(
            client_start=date(2020, 1, 1), client_end=date(2020, 12, 31),
            staff_start=date(2020, 1, 1), staff_end=date(2020, 12, 31),
            contract_name="A"
        )
        # Assignment B: 2021-04-01 (resets start date)
        _, staff_contract_b = self._create_contracts_and_assignment(
            client_start=date(2021, 4, 1), client_end=date(2021, 12, 31),
            staff_start=date(2021, 4, 1), staff_end=date(2021, 12, 31),
            contract_name="B"
        )

        teishokubi = StaffContractTeishokubi.objects.get(staff_email=self.staff.email)
        self.assertEqual(teishokubi.dispatch_start_date, date(2021, 4, 1))

        # Delete assignment B
        ContractAssignment.objects.get(staff_contract=staff_contract_b).delete()

        teishokubi.refresh_from_db()
        self.assertEqual(teishokubi.dispatch_start_date, date(2020, 1, 1))
        self.assertEqual(teishokubi.conflict_date, date(2023, 1, 1))

    def test_last_assignment_deletion_removes_teishokubi(self):
        """最後の割り当てが削除された後、抵触日レコードが削除されることをテスト"""
        _, staff_contract_a = self._create_contracts_and_assignment(
            client_start=date(2020, 1, 1), client_end=date(2020, 12, 31),
            staff_start=date(2020, 1, 1), staff_end=date(2020, 12, 31),
            contract_name="A"
        )

        self.assertTrue(StaffContractTeishokubi.objects.filter(staff_email=self.staff.email).exists())

        # Delete the only assignment
        ContractAssignment.objects.get(staff_contract=staff_contract_a).delete()

        self.assertFalse(StaffContractTeishokubi.objects.filter(staff_email=self.staff.email).exists())

    def test_non_relevant_contract_type_is_ignored(self):
        """対象外の契約種別の割り当てでは抵触日が作成されないことをテスト"""
        client_contract = ClientContract.objects.create(
            client=self.client_instance,
            contract_name='Non-Haken Contract',
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
            client_contract_type_code='10', # Not '20' (派遣)
            contract_pattern=self.contract_pattern
        )
        staff_contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name='Test Staff Contract',
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
            employment_type=self.employment_type_fixed
        )
        ContractAssignment.objects.create(
            client_contract=client_contract,
            staff_contract=staff_contract
        )

        self.assertFalse(StaffContractTeishokubi.objects.filter(staff_email=self.staff.email).exists())

    def test_teishokubi_detail_creation(self):
        """抵触日詳細レコードが正しく作成・更新されることをテスト"""
        # Assignment A
        self._create_contracts_and_assignment(
            client_start=date(2020, 1, 1), client_end=date(2020, 12, 31),
            staff_start=date(2020, 1, 1), staff_end=date(2020, 12, 31),
            contract_name="A"
        )
        # Assignment B (gap resets start date)
        self._create_contracts_and_assignment(
            client_start=date(2021, 4, 1), client_end=date(2021, 12, 31),
            staff_start=date(2021, 4, 1), staff_end=date(2021, 12, 31),
            contract_name="B"
        )

        teishokubi = StaffContractTeishokubi.objects.get(staff_email=self.staff.email)
        self.assertEqual(teishokubi.details.count(), 2)

        # Check detail records
        detail_a = teishokubi.details.get(assignment_start_date=date(2020, 1, 1))
        self.assertEqual(detail_a.is_calculated, False)

        detail_b = teishokubi.details.get(assignment_start_date=date(2021, 4, 1))
        self.assertEqual(detail_b.is_calculated, True)

        # Add Assignment C (no gap)
        self._create_contracts_and_assignment(
            client_start=date(2022, 1, 1), client_end=date(2022, 12, 31),
            staff_start=date(2022, 1, 1), staff_end=date(2022, 12, 31),
            contract_name="C"
        )

        teishokubi.refresh_from_db()
        self.assertEqual(teishokubi.details.count(), 3)
        detail_c = teishokubi.details.get(assignment_start_date=date(2022, 1, 1))
        self.assertEqual(detail_c.is_calculated, True)

    def test_non_relevant_employment_type_is_ignored(self):
        """無期雇用の場合は抵触日が作成されないことをテスト"""
        client_contract = ClientContract.objects.create(
            client=self.client_instance,
            contract_name='Haken Contract',
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
            client_contract_type_code='20',
            contract_pattern=self.contract_pattern
        )
        ClientContractHaken.objects.create(
            client_contract=client_contract,
            haken_unit=self.department
        )
        staff_contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name='Non-Yuki Haken Contract',
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
            employment_type=self.employment_type_indefinite  # 派遣社員(無期)
        )
        ContractAssignment.objects.create(
            client_contract=client_contract,
            staff_contract=staff_contract
        )

        self.assertFalse(StaffContractTeishokubi.objects.filter(staff_email=self.staff.email).exists())
