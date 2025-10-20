# -*- coding: utf-8 -*-
"""
粗利率計算機能のテスト
"""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.common.constants import Constants
from apps.client.models import Client
from apps.staff.models import Staff
from apps.master.models import ContractPattern, EmploymentType
from apps.system.settings.models import Dropdowns
from apps.contract.models import ClientContract, StaffContract
from apps.contract.views_assignment import _calculate_profit_margin

User = get_user_model()


class ProfitMarginCalculationTest(TestCase):
    """粗利率計算のテスト"""

    def setUp(self):
        """テストデータのセットアップ"""
        # ユーザー作成
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # クライアント作成
        self.client_obj = Client.objects.create(
            name='テストクライアント',
            corporate_number='1234567890123',
            created_by=self.user,
            updated_by=self.user
        )

        # スタッフ作成
        self.staff = Staff.objects.create(
            name_last='田中',
            name_first='太郎',
            email='tanaka@example.com',
            created_by=self.user,
            updated_by=self.user
        )

        # 雇用形態作成
        self.employment_type = EmploymentType.objects.create(
            name='正社員',
            is_fixed_term=False,
            created_by=self.user,
            updated_by=self.user
        )

        # 契約パターン作成
        self.client_pattern = ContractPattern.objects.create(
            name='クライアント契約パターン',
            domain=Constants.DOMAIN.CLIENT,
            created_by=self.user,
            updated_by=self.user
        )

        self.staff_pattern = ContractPattern.objects.create(
            name='スタッフ契約パターン',
            domain=Constants.DOMAIN.STAFF,
            created_by=self.user,
            updated_by=self.user
        )

        # ドロップダウン作成
        self.bill_unit_hourly = Dropdowns.objects.create(
            category='bill_unit',
            value=Constants.BILL_UNIT.HOURLY_RATE,
            name='時間単価',
            active=True
        )
        self.bill_unit_daily = Dropdowns.objects.create(
            category='bill_unit',
            value=Constants.BILL_UNIT.DAILY_RATE,
            name='日額',
            active=True
        )
        self.bill_unit_monthly = Dropdowns.objects.create(
            category='bill_unit',
            value=Constants.BILL_UNIT.MONTHLY_RATE,
            name='月額',
            active=True
        )

        self.pay_unit_hourly = Dropdowns.objects.create(
            category='pay_unit',
            value=Constants.PAY_UNIT.HOURLY,
            name='時給',
            active=True
        )
        self.pay_unit_daily = Dropdowns.objects.create(
            category='pay_unit',
            value=Constants.PAY_UNIT.DAILY,
            name='日給',
            active=True
        )
        self.pay_unit_monthly = Dropdowns.objects.create(
            category='pay_unit',
            value=Constants.PAY_UNIT.MONTHLY,
            name='月給',
            active=True
        )

        self.client.login(username='testuser', password='testpass123')

    def test_profit_margin_calculation_hourly_positive(self):
        """時給ベースでの粗利率計算（正の値）"""
        # クライアント契約（時間単価3000円）
        client_contract = ClientContract.objects.create(
            client=self.client_obj,
            contract_name='時給テスト契約',
            contract_pattern=self.client_pattern,
            start_date='2024-01-01',
            end_date='2024-12-31',
            contract_amount=Decimal('3000'),
            bill_unit=Constants.BILL_UNIT.HOURLY_RATE,
            created_by=self.user,
            updated_by=self.user
        )

        # スタッフ契約（時給2000円）
        staff_contract = StaffContract.objects.create(
            staff=self.staff,
            employment_type=self.employment_type,
            contract_name='時給テストスタッフ契約',
            contract_pattern=self.staff_pattern,
            start_date='2024-01-01',
            end_date='2024-12-31',
            contract_amount=Decimal('2000'),
            pay_unit=Constants.PAY_UNIT.HOURLY,
            created_by=self.user,
            updated_by=self.user
        )

        result = _calculate_profit_margin(client_contract, staff_contract)

        self.assertTrue(result['can_calculate'])
        self.assertEqual(result['profit_margin'], 33.33)  # (3000-2000)/3000*100 = 33.33%
        self.assertFalse(result['show_warning'])
        self.assertEqual(result['client_amount'], 3000.0)
        self.assertEqual(result['staff_amount'], 2000.0)

    def test_profit_margin_calculation_daily_zero(self):
        """日給ベースでの粗利率計算（0%）"""
        # クライアント契約（日額10000円）
        client_contract = ClientContract.objects.create(
            client=self.client_obj,
            contract_name='日給テスト契約',
            contract_pattern=self.client_pattern,
            start_date='2024-01-01',
            end_date='2024-12-31',
            contract_amount=Decimal('10000'),
            bill_unit=Constants.BILL_UNIT.DAILY_RATE,
            created_by=self.user,
            updated_by=self.user
        )

        # スタッフ契約（日給10000円）
        staff_contract = StaffContract.objects.create(
            staff=self.staff,
            employment_type=self.employment_type,
            contract_name='日給テストスタッフ契約',
            contract_pattern=self.staff_pattern,
            start_date='2024-01-01',
            end_date='2024-12-31',
            contract_amount=Decimal('10000'),
            pay_unit=Constants.PAY_UNIT.DAILY,
            created_by=self.user,
            updated_by=self.user
        )

        result = _calculate_profit_margin(client_contract, staff_contract)

        self.assertTrue(result['can_calculate'])
        self.assertEqual(result['profit_margin'], 0.0)  # (10000-10000)/10000*100 = 0%
        self.assertTrue(result['show_warning'])  # 0%以下なので警告

    def test_profit_margin_calculation_monthly_negative(self):
        """月給ベースでの粗利率計算（負の値）"""
        # クライアント契約（月額200000円）
        client_contract = ClientContract.objects.create(
            client=self.client_obj,
            contract_name='月給テスト契約',
            contract_pattern=self.client_pattern,
            start_date='2024-01-01',
            end_date='2024-12-31',
            contract_amount=Decimal('200000'),
            bill_unit=Constants.BILL_UNIT.MONTHLY_RATE,
            created_by=self.user,
            updated_by=self.user
        )

        # スタッフ契約（月給250000円）
        staff_contract = StaffContract.objects.create(
            staff=self.staff,
            employment_type=self.employment_type,
            contract_name='月給テストスタッフ契約',
            contract_pattern=self.staff_pattern,
            start_date='2024-01-01',
            end_date='2024-12-31',
            contract_amount=Decimal('250000'),
            pay_unit=Constants.PAY_UNIT.MONTHLY,
            created_by=self.user,
            updated_by=self.user
        )

        result = _calculate_profit_margin(client_contract, staff_contract)

        self.assertTrue(result['can_calculate'])
        self.assertEqual(result['profit_margin'], -25.0)  # (200000-250000)/200000*100 = -25%
        self.assertTrue(result['show_warning'])  # 0%以下なので警告

    def test_profit_margin_calculation_unit_mismatch(self):
        """単位が一致しない場合（計算不可）"""
        # クライアント契約（時間単価）
        client_contract = ClientContract.objects.create(
            client=self.client_obj,
            contract_name='単位不一致テスト契約',
            contract_pattern=self.client_pattern,
            start_date='2024-01-01',
            end_date='2024-12-31',
            contract_amount=Decimal('3000'),
            bill_unit=Constants.BILL_UNIT.HOURLY_RATE,
            created_by=self.user,
            updated_by=self.user
        )

        # スタッフ契約（日給）
        staff_contract = StaffContract.objects.create(
            staff=self.staff,
            employment_type=self.employment_type,
            contract_name='単位不一致テストスタッフ契約',
            contract_pattern=self.staff_pattern,
            start_date='2024-01-01',
            end_date='2024-12-31',
            contract_amount=Decimal('10000'),
            pay_unit=Constants.PAY_UNIT.DAILY,
            created_by=self.user,
            updated_by=self.user
        )

        result = _calculate_profit_margin(client_contract, staff_contract)

        self.assertFalse(result['can_calculate'])
        self.assertIsNone(result['profit_margin'])
        self.assertFalse(result['show_warning'])

    def test_profit_margin_calculation_missing_amount(self):
        """金額が設定されていない場合（計算不可）"""
        # クライアント契約（金額なし）
        client_contract = ClientContract.objects.create(
            client=self.client_obj,
            contract_name='金額なしテスト契約',
            contract_pattern=self.client_pattern,
            start_date='2024-01-01',
            end_date='2024-12-31',
            contract_amount=None,
            bill_unit=Constants.BILL_UNIT.HOURLY_RATE,
            created_by=self.user,
            updated_by=self.user
        )

        # スタッフ契約（時給2000円）
        staff_contract = StaffContract.objects.create(
            staff=self.staff,
            employment_type=self.employment_type,
            contract_name='金額ありテストスタッフ契約',
            contract_pattern=self.staff_pattern,
            start_date='2024-01-01',
            end_date='2024-12-31',
            contract_amount=Decimal('2000'),
            pay_unit=Constants.PAY_UNIT.HOURLY,
            created_by=self.user,
            updated_by=self.user
        )

        result = _calculate_profit_margin(client_contract, staff_contract)

        self.assertFalse(result['can_calculate'])
        self.assertIsNone(result['profit_margin'])
        self.assertFalse(result['show_warning'])

    def test_profit_margin_calculation_missing_unit(self):
        """単位が設定されていない場合（計算不可）"""
        # クライアント契約（単位なし）
        client_contract = ClientContract.objects.create(
            client=self.client_obj,
            contract_name='単位なしテスト契約',
            contract_pattern=self.client_pattern,
            start_date='2024-01-01',
            end_date='2024-12-31',
            contract_amount=Decimal('3000'),
            bill_unit=None,
            created_by=self.user,
            updated_by=self.user
        )

        # スタッフ契約（時給2000円）
        staff_contract = StaffContract.objects.create(
            staff=self.staff,
            employment_type=self.employment_type,
            contract_name='単位ありテストスタッフ契約',
            contract_pattern=self.staff_pattern,
            start_date='2024-01-01',
            end_date='2024-12-31',
            contract_amount=Decimal('2000'),
            pay_unit=Constants.PAY_UNIT.HOURLY,
            created_by=self.user,
            updated_by=self.user
        )

        result = _calculate_profit_margin(client_contract, staff_contract)

        self.assertFalse(result['can_calculate'])
        self.assertIsNone(result['profit_margin'])
        self.assertFalse(result['show_warning'])

    def test_profit_margin_calculation_zero_client_amount(self):
        """クライアント金額が0の場合"""
        # クライアント契約（金額0円）
        client_contract = ClientContract.objects.create(
            client=self.client_obj,
            contract_name='金額0テスト契約',
            contract_pattern=self.client_pattern,
            start_date='2024-01-01',
            end_date='2024-12-31',
            contract_amount=Decimal('0'),
            bill_unit=Constants.BILL_UNIT.HOURLY_RATE,
            created_by=self.user,
            updated_by=self.user
        )

        # スタッフ契約（時給2000円）
        staff_contract = StaffContract.objects.create(
            staff=self.staff,
            employment_type=self.employment_type,
            contract_name='通常金額テストスタッフ契約',
            contract_pattern=self.staff_pattern,
            start_date='2024-01-01',
            end_date='2024-12-31',
            contract_amount=Decimal('2000'),
            pay_unit=Constants.PAY_UNIT.HOURLY,
            created_by=self.user,
            updated_by=self.user
        )

        result = _calculate_profit_margin(client_contract, staff_contract)

        self.assertTrue(result['can_calculate'])
        self.assertEqual(result['profit_margin'], 0.0)  # 0で割る場合は0%
        self.assertTrue(result['show_warning'])  # 0%以下なので警告


class ProfitMarginViewTest(TestCase):
    """粗利率表示のビューテスト"""

    def setUp(self):
        """テストデータのセットアップ"""
        # ユーザー作成
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.user.user_permissions.add(
            *self.user._meta.model.objects.get(username='testuser').get_all_permissions()
        )

        # クライアント作成
        self.client_obj = Client.objects.create(
            name='テストクライアント',
            corporate_number='1234567890123',
            created_by=self.user,
            updated_by=self.user
        )

        # スタッフ作成
        self.staff = Staff.objects.create(
            name_last='田中',
            name_first='太郎',
            email='tanaka@example.com',
            created_by=self.user,
            updated_by=self.user
        )

        # 雇用形態作成
        self.employment_type = EmploymentType.objects.create(
            name='正社員',
            is_fixed_term=False,
            created_by=self.user,
            updated_by=self.user
        )

        # 契約パターン作成
        self.client_pattern = ContractPattern.objects.create(
            name='クライアント契約パターン',
            domain=Constants.DOMAIN.CLIENT,
            created_by=self.user,
            updated_by=self.user
        )

        self.staff_pattern = ContractPattern.objects.create(
            name='スタッフ契約パターン',
            domain=Constants.DOMAIN.STAFF,
            created_by=self.user,
            updated_by=self.user
        )

        # ドロップダウン作成
        Dropdowns.objects.create(
            category='bill_unit',
            value=Constants.BILL_UNIT.HOURLY_RATE,
            name='時間単価',
            active=True
        )
        Dropdowns.objects.create(
            category='pay_unit',
            value=Constants.PAY_UNIT.HOURLY,
            name='時給',
            active=True
        )

        self.client.login(username='testuser', password='testpass123')

    def test_staff_assignment_confirm_with_profit_margin(self):
        """スタッフ割当確認画面での粗利率表示テスト"""
        # クライアント契約作成
        client_contract = ClientContract.objects.create(
            client=self.client_obj,
            contract_name='粗利率テスト契約',
            contract_pattern=self.client_pattern,
            start_date='2024-01-01',
            end_date='2024-12-31',
            contract_amount=Decimal('3000'),
            bill_unit=Constants.BILL_UNIT.HOURLY_RATE,
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            created_by=self.user,
            updated_by=self.user
        )

        # スタッフ契約作成
        staff_contract = StaffContract.objects.create(
            staff=self.staff,
            employment_type=self.employment_type,
            contract_name='粗利率テストスタッフ契約',
            contract_pattern=self.staff_pattern,
            start_date='2024-01-01',
            end_date='2024-12-31',
            contract_amount=Decimal('2000'),
            pay_unit=Constants.PAY_UNIT.HOURLY,
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            created_by=self.user,
            updated_by=self.user
        )

        # 確認画面にPOST
        url = reverse('contract:staff_assignment_confirm')
        response = self.client.post(url, {
            'client_contract_id': client_contract.pk,
            'staff_contract_id': staff_contract.pk,
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '粗利率: 33.33%')
        self.assertContains(response, 'クライアント: 3,000円')
        self.assertContains(response, 'スタッフ: 2,000円')

    def test_client_assignment_confirm_with_profit_margin_warning(self):
        """クライアント割当確認画面での粗利率警告表示テスト"""
        # クライアント契約作成（低い金額）
        client_contract = ClientContract.objects.create(
            client=self.client_obj,
            contract_name='粗利率警告テスト契約',
            contract_pattern=self.client_pattern,
            start_date='2024-01-01',
            end_date='2024-12-31',
            contract_amount=Decimal('1500'),
            bill_unit=Constants.BILL_UNIT.HOURLY_RATE,
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            created_by=self.user,
            updated_by=self.user
        )

        # スタッフ契約作成（高い金額）
        staff_contract = StaffContract.objects.create(
            staff=self.staff,
            employment_type=self.employment_type,
            contract_name='粗利率警告テストスタッフ契約',
            contract_pattern=self.staff_pattern,
            start_date='2024-01-01',
            end_date='2024-12-31',
            contract_amount=Decimal('2000'),
            pay_unit=Constants.PAY_UNIT.HOURLY,
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            created_by=self.user,
            updated_by=self.user
        )

        # 確認画面にPOST
        url = reverse('contract:client_assignment_confirm')
        response = self.client.post(url, {
            'client_contract_id': client_contract.pk,
            'staff_contract_id': staff_contract.pk,
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '粗利率: -33.33%')
        self.assertContains(response, '粗利率が0%以下です。契約金額を確認してください。')
        self.assertContains(response, 'alert-warning')  # 警告アラート