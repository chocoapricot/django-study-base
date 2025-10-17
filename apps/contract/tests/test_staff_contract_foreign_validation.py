# -*- coding: utf-8 -*-
"""
スタッフ契約の外国籍情報バリデーションテスト
"""
from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from apps.staff.models import Staff, StaffInternational
from apps.contract.models import StaffContract
from apps.contract.forms import StaffContractForm
from apps.master.models import JobCategory, ContractPattern, EmploymentType, StaffRegistStatus
from apps.common.constants import Constants


class StaffContractForeignValidationTest(TestCase):
    """スタッフ契約の外国籍情報バリデーションテスト"""

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
        self.contract_pattern = ContractPattern.objects.create(
            name='標準契約',
            domain=Constants.DOMAIN.STAFF,
            is_active=True
        )

        # 職種作成（特定技能外国人受入該当）
        self.job_category_skilled = JobCategory.objects.create(
            name='特定技能対応職種',
            is_specified_skilled_worker=True,
            is_active=True
        )

        # 職種作成（特定技能外国人受入非該当）
        self.job_category_normal = JobCategory.objects.create(
            name='一般職種',
            is_specified_skilled_worker=False,
            is_active=True
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
            residence_period_to=date.today() + timedelta(days=365)
        )

    def test_japanese_staff_contract_no_validation(self):
        """日本人スタッフの契約では外国籍バリデーションが実行されないことを確認"""
        form_data = {
            'staff': self.japanese_staff.pk,
            'employment_type': self.employment_type.pk,
            'contract_name': 'テスト契約',
            'job_category': self.job_category_normal.pk,
            'contract_pattern': self.contract_pattern.pk,
            'contract_status': Constants.CONTRACT_STATUS.DRAFT,
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=365),
            'contract_amount': 300000,
            'pay_unit': '30',  # 月給
        }

        form = StaffContractForm(data=form_data)
        self.assertTrue(form.is_valid(), f"フォームエラー: {form.errors}")

    def test_foreign_staff_with_skilled_job_category_valid(self):
        """外国籍スタッフで特定技能対応職種の場合は正常に登録できることを確認"""
        form_data = {
            'staff': self.foreign_staff.pk,
            'employment_type': self.employment_type.pk,
            'contract_name': 'テスト契約',
            'job_category': self.job_category_skilled.pk,
            'contract_pattern': self.contract_pattern.pk,
            'contract_status': Constants.CONTRACT_STATUS.DRAFT,
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=180),  # 在留期限内
            'contract_amount': 300000,
            'pay_unit': '30',  # 月給
        }

        form = StaffContractForm(data=form_data)
        self.assertTrue(form.is_valid(), f"フォームエラー: {form.errors}")

    def test_foreign_staff_with_normal_job_category_invalid(self):
        """外国籍スタッフで特定技能非対応職種の場合はエラーになることを確認"""
        form_data = {
            'staff': self.foreign_staff.pk,
            'employment_type': self.employment_type.pk,
            'contract_name': 'テスト契約',
            'job_category': self.job_category_normal.pk,
            'contract_pattern': self.contract_pattern.pk,
            'contract_status': Constants.CONTRACT_STATUS.DRAFT,
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=180),
            'contract_amount': 300000,
            'pay_unit': '30',  # 月給
        }

        form = StaffContractForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('job_category', form.errors)
        self.assertIn('特定技能外国人受入該当の職種を選択してください', str(form.errors['job_category']))

    def test_foreign_staff_contract_end_after_residence_period_invalid(self):
        """外国籍スタッフの契約終了日が在留期限を超える場合はエラーになることを確認"""
        form_data = {
            'staff': self.foreign_staff.pk,
            'employment_type': self.employment_type.pk,
            'contract_name': 'テスト契約',
            'job_category': self.job_category_skilled.pk,
            'contract_pattern': self.contract_pattern.pk,
            'contract_status': Constants.CONTRACT_STATUS.DRAFT,
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=400),  # 在留期限を超える
            'contract_amount': 300000,
            'pay_unit': '30',  # 月給
        }

        form = StaffContractForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('end_date', form.errors)
        self.assertIn('在留期限', str(form.errors['end_date']))
        self.assertIn('を超えています', str(form.errors['end_date']))

    def test_foreign_staff_contract_end_within_residence_period_valid(self):
        """外国籍スタッフの契約終了日が在留期限内の場合は正常に登録できることを確認"""
        form_data = {
            'staff': self.foreign_staff.pk,
            'employment_type': self.employment_type.pk,
            'contract_name': 'テスト契約',
            'job_category': self.job_category_skilled.pk,
            'contract_pattern': self.contract_pattern.pk,
            'contract_status': Constants.CONTRACT_STATUS.DRAFT,
            'start_date': date.today(),
            'end_date': self.international_info.residence_period_to,  # 在留期限と同日
            'contract_amount': 300000,
            'pay_unit': '30',  # 月給
        }

        form = StaffContractForm(data=form_data)
        self.assertTrue(form.is_valid(), f"フォームエラー: {form.errors}")

    def test_foreign_staff_no_end_date_valid(self):
        """外国籍スタッフで契約終了日が未設定の場合は正常に登録できることを確認"""
        form_data = {
            'staff': self.foreign_staff.pk,
            'employment_type': self.employment_type.pk,
            'contract_name': 'テスト契約',
            'job_category': self.job_category_skilled.pk,
            'contract_pattern': self.contract_pattern.pk,
            'contract_status': Constants.CONTRACT_STATUS.DRAFT,
            'start_date': date.today(),
            # end_dateは未設定
            'contract_amount': 300000,
            'pay_unit': '30',  # 月給
        }

        form = StaffContractForm(data=form_data)
        self.assertTrue(form.is_valid(), f"フォームエラー: {form.errors}")

    def test_foreign_staff_no_job_category_valid(self):
        """外国籍スタッフで職種が未設定の場合は職種チェックをスキップすることを確認"""
        form_data = {
            'staff': self.foreign_staff.pk,
            'employment_type': self.employment_type.pk,
            'contract_name': 'テスト契約',
            # job_categoryは未設定
            'contract_pattern': self.contract_pattern.pk,
            'contract_status': Constants.CONTRACT_STATUS.DRAFT,
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=180),
            'contract_amount': 300000,
            'pay_unit': '30',  # 月給
        }

        form = StaffContractForm(data=form_data)
        self.assertTrue(form.is_valid(), f"フォームエラー: {form.errors}")

    def test_both_validations_fail(self):
        """職種と在留期限の両方でエラーになる場合を確認"""
        form_data = {
            'staff': self.foreign_staff.pk,
            'employment_type': self.employment_type.pk,
            'contract_name': 'テスト契約',
            'job_category': self.job_category_normal.pk,  # 特定技能非対応
            'contract_pattern': self.contract_pattern.pk,
            'contract_status': Constants.CONTRACT_STATUS.DRAFT,
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=400),  # 在留期限を超える
            'contract_amount': 300000,
            'pay_unit': '30',  # 月給
        }

        form = StaffContractForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('job_category', form.errors)
        self.assertIn('end_date', form.errors)