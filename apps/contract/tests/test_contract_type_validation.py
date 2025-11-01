# -*- coding: utf-8 -*-
"""
契約タイプ別バリデーションのテストケース
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from datetime import date
from apps.contract.models import ClientContract, ClientContractHaken, ClientContractTtp
from apps.client.models import Client
from apps.master.models import ContractPattern
from apps.common.constants import Constants

User = get_user_model()


class ContractTypeValidationTest(TestCase):
    """契約タイプ別バリデーションのテストクラス"""

    def setUp(self):
        """テストデータのセットアップ"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()

        # テスト用クライアント
        self.client_model = Client.objects.create(
            name='テストクライアント',
            corporate_number='1234567890123',
            created_by=self.user,
            updated_by=self.user
        )

        # 契約書パターン
        self.contract_pattern = ContractPattern.objects.create(
            name='テスト契約パターン',
            domain=Constants.DOMAIN.CLIENT,
            created_by=self.user,
            updated_by=self.user
        )

    def test_quasi_mandate_contract_approval_over_6_months(self):
        """準委任契約（6ヶ月超）の承認が成功することをテスト"""
        # 準委任契約を作成（10ヶ月）
        contract = ClientContract.objects.create(
            client=self.client_model,
            client_contract_type_code=Constants.CLIENT_CONTRACT_TYPE.QUASI_MANDATE,
            contract_name='準委任契約テスト',
            contract_pattern=self.contract_pattern,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 10, 31),  # 10ヶ月
            contract_status=Constants.CONTRACT_STATUS.PENDING,
            created_by=self.user,
            updated_by=self.user
        )

        # 承認処理を実行
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('contract:client_contract_approve', args=[contract.pk]),
            {'is_approved': 'true'}
        )

        # 成功してリダイレクト
        self.assertEqual(response.status_code, 302)

        # 契約が承認済みになっていることを確認
        contract.refresh_from_db()
        self.assertEqual(contract.contract_status, Constants.CONTRACT_STATUS.APPROVED)

    def test_contract_type_contract_approval_over_6_months(self):
        """請負契約（6ヶ月超）の承認が成功することをテスト"""
        # 請負契約を作成（8ヶ月）
        contract = ClientContract.objects.create(
            client=self.client_model,
            client_contract_type_code=Constants.CLIENT_CONTRACT_TYPE.CONTRACT,
            contract_name='請負契約テスト',
            contract_pattern=self.contract_pattern,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 8, 31),  # 8ヶ月
            contract_status=Constants.CONTRACT_STATUS.PENDING,
            created_by=self.user,
            updated_by=self.user
        )

        # 承認処理を実行
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('contract:client_contract_approve', args=[contract.pk]),
            {'is_approved': 'true'}
        )

        # 成功してリダイレクト
        self.assertEqual(response.status_code, 302)

        # 契約が承認済みになっていることを確認
        contract.refresh_from_db()
        self.assertEqual(contract.contract_status, Constants.CONTRACT_STATUS.APPROVED)

    def test_dispatch_contract_without_ttp_approval_over_6_months(self):
        """派遣契約（TTP情報なし、6ヶ月超）の承認が成功することをテスト"""
        # 派遣契約を作成（8ヶ月）
        contract = ClientContract.objects.create(
            client=self.client_model,
            client_contract_type_code=Constants.CLIENT_CONTRACT_TYPE.DISPATCH,
            contract_name='派遣契約テスト（TTPなし）',
            contract_pattern=self.contract_pattern,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 8, 31),  # 8ヶ月
            contract_status=Constants.CONTRACT_STATUS.PENDING,
            created_by=self.user,
            updated_by=self.user
        )

        # 派遣情報を作成（TTP情報は作成しない）
        ClientContractHaken.objects.create(
            client_contract=contract,
            created_by=self.user,
            updated_by=self.user
        )

        # 承認処理を実行
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('contract:client_contract_approve', args=[contract.pk]),
            {'is_approved': 'true'}
        )

        # 成功してリダイレクト
        self.assertEqual(response.status_code, 302)

        # 契約が承認済みになっていることを確認
        contract.refresh_from_db()
        self.assertEqual(contract.contract_status, Constants.CONTRACT_STATUS.APPROVED)

    def test_dispatch_contract_with_ttp_approval_over_6_months_fails(self):
        """派遣契約（TTP情報あり、6ヶ月超）の承認が失敗することをテスト"""
        # 派遣契約を作成（8ヶ月）
        contract = ClientContract.objects.create(
            client=self.client_model,
            client_contract_type_code=Constants.CLIENT_CONTRACT_TYPE.DISPATCH,
            contract_name='派遣契約テスト（TTPあり）',
            contract_pattern=self.contract_pattern,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 8, 31),  # 8ヶ月
            contract_status=Constants.CONTRACT_STATUS.PENDING,
            created_by=self.user,
            updated_by=self.user
        )

        # 派遣情報を作成
        haken_info = ClientContractHaken.objects.create(
            client_contract=contract,
            created_by=self.user,
            updated_by=self.user
        )

        # TTP情報を作成
        ClientContractTtp.objects.create(
            haken=haken_info,
            contract_period='8ヶ月',
            business_content='テスト業務',
            created_by=self.user,
            updated_by=self.user
        )

        # 承認処理を実行
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('contract:client_contract_approve', args=[contract.pk]),
            {'is_approved': 'true'}
        )

        # リダイレクト（エラーメッセージ付き）
        self.assertEqual(response.status_code, 302)

        # 契約が承認されていないことを確認
        contract.refresh_from_db()
        self.assertEqual(contract.contract_status, Constants.CONTRACT_STATUS.PENDING)

    def test_dispatch_contract_with_ttp_approval_within_6_months_succeeds(self):
        """派遣契約（TTP情報あり、6ヶ月以内）の承認が成功することをテスト"""
        # 派遣契約を作成（5ヶ月）
        contract = ClientContract.objects.create(
            client=self.client_model,
            client_contract_type_code=Constants.CLIENT_CONTRACT_TYPE.DISPATCH,
            contract_name='派遣契約テスト（TTPあり、6ヶ月以内）',
            contract_pattern=self.contract_pattern,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 5, 31),  # 5ヶ月
            contract_status=Constants.CONTRACT_STATUS.PENDING,
            created_by=self.user,
            updated_by=self.user
        )

        # 派遣情報を作成
        haken_info = ClientContractHaken.objects.create(
            client_contract=contract,
            created_by=self.user,
            updated_by=self.user
        )

        # TTP情報を作成
        ClientContractTtp.objects.create(
            haken=haken_info,
            contract_period='5ヶ月',
            business_content='テスト業務',
            created_by=self.user,
            updated_by=self.user
        )

        # 承認処理を実行
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('contract:client_contract_approve', args=[contract.pk]),
            {'is_approved': 'true'}
        )

        # 成功してリダイレクト
        self.assertEqual(response.status_code, 302)

        # 契約が承認済みになっていることを確認
        contract.refresh_from_db()
        self.assertEqual(contract.contract_status, Constants.CONTRACT_STATUS.APPROVED)