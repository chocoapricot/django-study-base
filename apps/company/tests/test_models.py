from django.test import TestCase
from ..models import Company, CompanyDepartment

class CompanyModelTest(TestCase):
    """会社モデルのテスト"""

    def setUp(self):
        self.company = Company.objects.create(
            name="テスト会社",
            corporate_number="1234567890123",
            postal_code="1000001",
            address="東京都千代田区千代田1-1",
            phone_number="03-1234-5678"
        )

    def test_company_creation(self):
        """会社の作成テスト"""
        self.assertEqual(self.company.name, "テスト会社")
        self.assertEqual(self.company.corporate_number, "1234567890123")
        self.assertEqual(str(self.company), "テスト会社")

    def test_company_unique_name(self):
        """会社名の一意性テスト"""
        with self.assertRaises(Exception):
            Company.objects.create(name="テスト会社")

class CompanyDepartmentModelTest(TestCase):
    """部署モデルのテスト"""

    def setUp(self):
        self.department = CompanyDepartment.objects.create(
            name="開発部",
            department_code="DEV001",
            accounting_code="ACC001",
            display_order=1
        )

    def test_department_creation(self):
        """部署の作成テスト"""
        self.assertEqual(self.department.name, "開発部")
        self.assertEqual(self.department.department_code, "DEV001")
        self.assertEqual(self.department.accounting_code, "ACC001")
        self.assertEqual(self.department.display_order, 1)
        self.assertEqual(str(self.department), "開発部")

    def test_department_period_overlap_validation(self):
        """部署の期間重複バリデーションテスト"""
        from datetime import date
        from django.core.exceptions import ValidationError

        # 同じ部署コードで期間重複する部署を作成しようとする
        overlapping_dept = CompanyDepartment(
            name="開発部2",
            department_code="DEV001",  # 同じ部署コード
            valid_from=date(2024, 1, 1),
            valid_to=date(2024, 12, 31)
        )

        with self.assertRaises(ValidationError):
            overlapping_dept.full_clean()

    def test_department_valid_period_check(self):
        """部署の有効期間チェックテスト"""
        from datetime import date

        # 有効期限付きの部署を作成
        dept_with_period = CompanyDepartment.objects.create(
            name="期間限定部署",
            department_code="TEMP001",
            valid_from=date(2024, 1, 1),
            valid_to=date(2024, 12, 31)
        )

        # 有効期間内の日付でテスト
        self.assertTrue(dept_with_period.is_valid_on_date(date(2024, 6, 1)))

        # 有効期間外の日付でテスト
        self.assertFalse(dept_with_period.is_valid_on_date(date(2025, 1, 1)))

        # 無期限部署のテスト
        self.assertTrue(self.department.is_valid_on_date())

    def test_get_valid_departments(self):
        """有効な部署一覧取得のテスト"""
        from datetime import date

        # 期間限定部署を作成
        CompanyDepartment.objects.create(
            name="期間限定部署",
            department_code="TEMP001",
            valid_from=date(2024, 1, 1),
            valid_to=date(2024, 12, 31)
        )

        # 2024年6月時点で有効な部署を取得
        valid_depts = CompanyDepartment.get_valid_departments(date(2024, 6, 1))
        self.assertEqual(valid_depts.count(), 2)  # 無期限部署 + 期間限定部署

        # 2025年時点で有効な部署を取得
        valid_depts = CompanyDepartment.get_valid_departments(date(2025, 1, 1))
        self.assertEqual(valid_depts.count(), 1)  # 無期限部署のみ
