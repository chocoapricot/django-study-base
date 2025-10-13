from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.client.models import Client, ClientUser
from apps.company.models import Company, CompanyUser
from apps.connect.models import ConnectClient
from apps.contract.models import ClientContract, ClientContractPrint
from apps.master.models import ContractPattern
from django.utils import timezone
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.common.constants import Constants
from apps.system.settings.models import Dropdowns

from django.test import Client as TestClient

class ClientContractConfirmTest(TestCase):
    def setUp(self):
        # Dropdownsデータを作成
        Dropdowns.objects.create(
            category='contract_status',
            value=Constants.CONTRACT_STATUS.ISSUED,
            name='発行済',
            active=True
        )
        Dropdowns.objects.create(
            category='contract_status',
            value=Constants.CONTRACT_STATUS.CONFIRMED,
            name='契約済',
            active=True
        )
        
        self.user_model = get_user_model()
        self.company = Company.objects.create(name='Test Company', corporate_number='1234567890123')

        # クライアントユーザーの作成
        self.user = self.user_model.objects.create_user(
            username='clientuser',
            email='clientuser@example.com',
            password='password'
        )
        self.client_model_instance = Client.objects.create(name='Test Client', corporate_number='9876543210987')
        self.client_user = ClientUser.objects.create(
            client=self.client_model_instance,
            name_last='user',
            name_first='client',
            email=self.user.email
        )
        ConnectClient.objects.create(
            corporate_number=self.company.corporate_number,
            email=self.user.email,
            status='approved'
        )

        # 内部スタッフユーザーの作成
        self.staff_user = self.user_model.objects.create_user(
            username='staffuser',
            password='password',
            is_staff=True,
            email='staffuser@example.com'
        )
        content_type = ContentType.objects.get_for_model(ClientContract)
        permission = Permission.objects.get(
            codename='view_clientcontract',
            content_type=content_type,
        )
        self.staff_user.user_permissions.add(permission)
        CompanyUser.objects.create(name_last="Staff", name_first="Test", email=self.staff_user.email)

        self.contract_pattern = ContractPattern.objects.create(
            name='Test Pattern',
            domain='10',
            contract_type_code='10'
        )
        self.contract = ClientContract.objects.create(
            client=self.client_model_instance,
            corporate_number=self.company.corporate_number,
            contract_name='Test Contract',
            start_date=timezone.now().date(),
            contract_status=Constants.CONTRACT_STATUS.ISSUED,
            contract_pattern=self.contract_pattern
        )

        # テスト用の発行済み書類を作成
        self.contract_pdf = ClientContractPrint.objects.create(
            client_contract=self.contract,
            print_type=ClientContractPrint.PrintType.CONTRACT,
            document_title='Test Contract PDF'
        )
        self.quotation = ClientContractPrint.objects.create(
            client_contract=self.contract,
            print_type=ClientContractPrint.PrintType.QUOTATION,
            document_title='Test Quotation'
        )
        self.clash_day_notification = ClientContractPrint.objects.create(
            client_contract=self.contract,
            print_type=ClientContractPrint.PrintType.CLASH_DAY_NOTIFICATION,
            document_title='Test Clash Day Notification'
        )
        self.dispatch_notification = ClientContractPrint.objects.create(
            client_contract=self.contract,
            print_type=ClientContractPrint.PrintType.DISPATCH_NOTIFICATION,
            document_title='Test Dispatch Notification'
        )

        self.client = TestClient()

    def test_client_contract_confirm_list_view(self):
        self.client.login(username='clientuser', password='password')
        response = self.client.get(reverse('contract:client_contract_confirm_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.contract.contract_name)

    def test_client_contract_confirm_action(self):
        """契約確認時に、確認者と日時が記録されることをテスト"""
        self.client.login(username='clientuser', password='password')
        response = self.client.post(reverse('contract:client_contract_confirm_list'), {
            'contract_id': self.contract.pk,
            'action': 'confirm'
        })
        self.assertEqual(response.status_code, 302)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.contract_status, Constants.CONTRACT_STATUS.CONFIRMED)
        self.assertIsNotNone(self.contract.confirmed_at)
        self.assertEqual(self.contract.confirmed_by, self.client_user)

    def test_client_contract_unconfirm_action(self):
        """契約確認取り消し時に、確認者と日時がクリアされることをテスト"""
        self.contract.contract_status = Constants.CONTRACT_STATUS.CONFIRMED
        self.contract.confirmed_at = timezone.now()
        self.contract.confirmed_by = self.client_user
        self.contract.save()

        self.client.login(username='clientuser', password='password')
        response = self.client.post(reverse('contract:client_contract_confirm_list'), {
            'contract_id': self.contract.pk,
            'action': 'unconfirm'
        })
        self.assertEqual(response.status_code, 302)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.contract_status, Constants.CONTRACT_STATUS.ISSUED)
        self.assertIsNone(self.contract.confirmed_at)
        self.assertIsNone(self.contract.confirmed_by)

    def test_confirm_button_is_present_for_issued_contract(self):
        """
        ステータスが「発行済み」の契約に対して「確認」ボタンが表示されることを確認
        """
        self.client.login(username='clientuser', password='password')
        response = self.client.get(reverse('contract:client_contract_confirm_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="action" value="confirm"')

    def test_unconfirm_button_is_present_for_confirmed_contract(self):
        """
        ステータスが「確認済み」の契約に対して「未確認に戻す」ボタンが表示されることを確認
        """
        self.contract.contract_status = Constants.CONTRACT_STATUS.CONFIRMED
        self.contract.save()
        self.client.login(username='clientuser', password='password')
        response = self.client.get(reverse('contract:client_contract_confirm_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="action" value="unconfirm"')

    def test_related_documents_are_displayed(self):
        """
        契約確認画面に関連書類が表示されることを確認
        """
        self.client.login(username='clientuser', password='password')
        response = self.client.get(reverse('contract:client_contract_confirm_list'))
        self.assertEqual(response.status_code, 200)

        # 契約書
        self.assertContains(response, "契約書")
        self.assertContains(response, reverse('contract:download_client_contract_pdf', args=[self.contract_pdf.pk]))

        # 見積書
        self.assertContains(response, "見積書")
        self.assertContains(response, reverse('contract:download_client_contract_pdf', args=[self.quotation.pk]))

        # 抵触日通知書
        self.assertContains(response, "抵触日通知書")
        self.assertContains(response, reverse('contract:download_client_contract_pdf', args=[self.clash_day_notification.pk]))

        # 派遣通知書
        self.assertContains(response, "派遣通知書")
        self.assertContains(response, reverse('contract:download_client_contract_pdf', args=[self.dispatch_notification.pk]))

    def test_confirmer_name_displayed_on_detail_page(self):
        """
        契約詳細画面で確認者名が表示されることを確認
        """
        self.contract.contract_status = Constants.CONTRACT_STATUS.CONFIRMED
        self.contract.confirmed_by = self.client_user
        self.contract.confirmed_at = timezone.now()
        self.contract.save()

        self.client.login(username='staffuser', password='password')
        response = self.client.get(reverse('contract:client_contract_detail', args=[self.contract.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.client_user.name)