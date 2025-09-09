from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.client.models import Client, ClientUser
from apps.company.models import Company
from apps.connect.models import ConnectClient
from apps.contract.models import ClientContract
from django.utils import timezone

from django.test import Client as TestClient

class ClientContractConfirmTest(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.company = Company.objects.create(name='Test Company', corporate_number='1234567890123')
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

        self.contract = ClientContract.objects.create(
            client=self.client_model_instance,
            corporate_number=self.company.corporate_number,
            contract_name='Test Contract',
            start_date=timezone.now().date(),
            contract_status=ClientContract.ContractStatus.ISSUED
        )
        self.client = TestClient()

    def test_client_contract_confirm_list_view(self):
        self.client.login(username='clientuser', password='password')
        response = self.client.get(reverse('contract:client_contract_confirm_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.contract.contract_name)

    def test_client_contract_confirm_action(self):
        self.client.login(username='clientuser', password='password')
        response = self.client.post(reverse('contract:client_contract_confirm_list'), {
            'contract_id': self.contract.pk,
            'action': 'confirm'
        })
        self.assertEqual(response.status_code, 302)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.contract_status, ClientContract.ContractStatus.CONFIRMED)

    def test_client_contract_unconfirm_action(self):
        self.contract.contract_status = ClientContract.ContractStatus.CONFIRMED
        self.contract.save()
        self.client.login(username='clientuser', password='password')
        response = self.client.post(reverse('contract:client_contract_confirm_list'), {
            'contract_id': self.contract.pk,
            'action': 'unconfirm'
        })
        self.assertEqual(response.status_code, 302)
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.contract_status, ClientContract.ContractStatus.ISSUED)
