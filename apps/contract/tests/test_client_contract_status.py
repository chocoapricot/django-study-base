import os
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.auth.models import Permission
from apps.client.models import Client
from apps.contract.models import ClientContract, ClientContractPrint
from apps.master.models import ContractPattern

User = get_user_model()

class ClientContractStatusTest(TestCase):
    """クライアント契約のステータス変更に関するテスト"""

    def setUp(self):
        """テストデータの準備"""
        self.user = User.objects.create_user(username='testuser', password='password', email='test@example.com')

        # 必要な権限をユーザーに付与
        permissions = Permission.objects.filter(
            codename__in=['change_clientcontract', 'view_clientcontract']
        )
        self.user.user_permissions.add(*permissions)

        self.client.force_login(self.user)

        self.client_obj = Client.objects.create(
            name='テストクライアント',
            created_by=self.user,
            updated_by=self.user,
        )
        self.pattern = ContractPattern.objects.create(
            name='テストパターン',
            domain='10', # クライアント契約
        )
        self.contract = ClientContract.objects.create(
            client=self.client_obj,
            contract_name='テスト契約',
            contract_pattern=self.pattern,
            start_date=timezone.now().date(),
            created_by=self.user,
            updated_by=self.user,
            contract_status=ClientContract.ContractStatus.DRAFT
        )

    def test_initial_status_is_draft(self):
        """初期ステータスが「作成中」であること"""
        self.assertEqual(self.contract.contract_status, ClientContract.ContractStatus.DRAFT)

    def test_approve_contract_from_pending(self):
        """契約承認アクションのテスト（申請中→承認済）"""
        self.contract.contract_status = ClientContract.ContractStatus.PENDING
        self.contract.save()

        url = reverse('contract:client_contract_approve', kwargs={'pk': self.contract.pk})
        response = self.client.post(url, {'is_approved': 'on'})
        self.assertRedirects(response, reverse('contract:client_contract_detail', kwargs={'pk': self.contract.pk}))

        self.contract.refresh_from_db()
        self.assertEqual(self.contract.contract_status, ClientContract.ContractStatus.APPROVED)
        self.assertIsNotNone(self.contract.approved_at)
        self.assertEqual(self.contract.approved_by, self.user)

    def test_unapprove_contract_from_approved(self):
        """承認解除アクションのテスト（承認済→作成中）"""
        self.contract.contract_status = ClientContract.ContractStatus.APPROVED
        self.contract.approved_at = timezone.now()
        self.contract.approved_by = self.user
        self.contract.save()

        # テスト用の発行履歴を作成
        ClientContractPrint.objects.create(client_contract=self.contract, print_type='10')
        ClientContractPrint.objects.create(client_contract=self.contract, print_type='20')
        self.assertEqual(self.contract.print_history.count(), 2)

        url = reverse('contract:client_contract_approve', kwargs={'pk': self.contract.pk})
        response = self.client.post(url) # is_approved is not sent
        self.assertRedirects(response, reverse('contract:client_contract_detail', kwargs={'pk': self.contract.pk}))

        self.contract.refresh_from_db()
        self.assertEqual(self.contract.contract_status, ClientContract.ContractStatus.DRAFT)
        self.assertIsNone(self.contract.approved_at)
        self.assertIsNone(self.contract.approved_by)

        # 発行履歴が削除されていることを確認
        self.assertEqual(self.contract.print_history.count(), 0)

    def test_issue_contract_from_approved(self):
        """契約書発行アクションのテスト（承認済→発行済）"""
        self.contract.contract_status = ClientContract.ContractStatus.APPROVED
        self.contract.save()

        url = reverse('contract:client_contract_issue', kwargs={'pk': self.contract.pk})
        response = self.client.post(url)
        self.assertRedirects(response, reverse('contract:client_contract_detail', kwargs={'pk': self.contract.pk}))

        self.contract.refresh_from_db()
        self.assertEqual(self.contract.contract_status, ClientContract.ContractStatus.ISSUED)
        self.assertIsNotNone(self.contract.issued_at)
        self.assertEqual(self.contract.issued_by, self.user)
        self.assertTrue(self.contract.print_history.filter(print_type='10').exists())

    def test_issue_quotation_from_approved(self):
        """見積書発行アクションのテスト（承認済から）"""
        self.contract.contract_status = ClientContract.ContractStatus.APPROVED
        self.contract.save()

        url = reverse('contract:issue_quotation', kwargs={'pk': self.contract.pk})
        response = self.client.post(url)
        self.assertRedirects(response, reverse('contract:client_contract_detail', kwargs={'pk': self.contract.pk}))

        self.assertTrue(self.contract.print_history.filter(print_type='20').exists())

    def test_issue_quotation_twice_fails(self):
        """見積書を2回発行できないことのテスト"""
        self.contract.contract_status = ClientContract.ContractStatus.APPROVED
        self.contract.save()
        ClientContractPrint.objects.create(client_contract=self.contract, print_type='20')

        url = reverse('contract:issue_quotation', kwargs={'pk': self.contract.pk})
        response = self.client.post(url)
        self.assertRedirects(response, reverse('contract:client_contract_detail', kwargs={'pk': self.contract.pk}))

        # 1つしか履歴がないことを確認
        self.assertEqual(self.contract.print_history.filter(print_type='20').count(), 1)

    def test_cannot_approve_from_draft(self):
        """作成中からは承認できないことのテスト"""
        self.assertEqual(self.contract.contract_status, ClientContract.ContractStatus.DRAFT)
        url = reverse('contract:client_contract_approve', kwargs={'pk': self.contract.pk})
        response = self.client.post(url, {'is_approved': 'on'}, follow=True)
        self.contract.refresh_from_db()
        # ステータスが変わらないことを確認
        self.assertEqual(self.contract.contract_status, ClientContract.ContractStatus.DRAFT)
        # エラーメッセージが出ていることを確認
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'このステータスからは承認できません。')

    def test_cannot_unapprove_from_pending(self):
        """申請中からは承認解除できないことのテスト"""
        self.contract.contract_status = ClientContract.ContractStatus.PENDING
        self.contract.save()
        url = reverse('contract:client_contract_approve', kwargs={'pk': self.contract.pk})
        response = self.client.post(url, follow=True) # is_approvedなし
        self.contract.refresh_from_db()
        # ステータスが変わらないことを確認
        self.assertEqual(self.contract.contract_status, ClientContract.ContractStatus.PENDING)
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'この契約の承認は解除できません。')
