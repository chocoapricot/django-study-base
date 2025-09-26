from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.client.models import Client
from apps.contract.models import ClientContract
from apps.master.models import ContractPattern
import datetime
from django.conf import settings

class ClientContractFilterTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser@example.com', email='testuser@example.com', password='password')

        content_type = ContentType.objects.get_for_model(ClientContract)
        permission = Permission.objects.get(
            codename='view_clientcontract',
            content_type=content_type,
        )
        self.user.user_permissions.add(permission)

        self.client = TestClient()
        self.client.login(email='testuser@example.com', password='password')

        contract_types = [
            ("10", "Type A"),
            ("20", "Type B")
        ]
        settings.DROPDOWN_CLIENT_CONTRACT_TYPE = contract_types

        self.client1 = Client.objects.create(name='Client A')
        self.client2 = Client.objects.create(name='Client B')
        self.contract_pattern = ContractPattern.objects.create(name='Test Pattern', domain='10')

        self.contract1 = ClientContract.objects.create(
            client=self.client1,
            contract_name='Contract 1',
            client_contract_type_code='10',
            start_date=datetime.date(2024, 1, 1),
            contract_pattern=self.contract_pattern,
        )
        self.contract2 = ClientContract.objects.create(
            client=self.client2,
            contract_name='Contract 2',
            client_contract_type_code='20',
            start_date=datetime.date(2024, 1, 1),
            contract_pattern=self.contract_pattern,
        )
        self.contract3 = ClientContract.objects.create(
            client=self.client1,
            contract_name='Contract 3',
            client_contract_type_code='20',
            start_date=datetime.date(2024, 1, 1),
            contract_pattern=self.contract_pattern,
        )

    def test_filter_by_contract_type(self):
        response = self.client.get(reverse('contract:client_contract_list'), {'contract_type': '20'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.contract2.contract_name)
        self.assertContains(response, self.contract3.contract_name)
        self.assertNotContains(response, self.contract1.contract_name)

        response = self.client.get(reverse('contract:client_contract_list'), {'contract_type': '10'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.contract1.contract_name)
        self.assertNotContains(response, self.contract2.contract_name)
        self.assertNotContains(response, self.contract3.contract_name)

        response = self.client.get(reverse('contract:client_contract_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.contract1.contract_name)
        self.assertContains(response, self.contract2.contract_name)
        self.assertContains(response, self.contract3.contract_name)

    def test_pagination_with_filter(self):
        for i in range(25):
            ClientContract.objects.create(
                client=self.client1,
                contract_name=f'Contract A-{i}',
                client_contract_type_code='10',
                start_date=datetime.date(2024, 1, 1),
                contract_pattern=self.contract_pattern,
            )

        response = self.client.get(reverse('contract:client_contract_list'), {'contract_type': '10'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="?contract_type=10&amp;page=2"')

        response = self.client.get(reverse('contract:client_contract_list'), {'contract_type': '10', 'page': '2'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<li class="page-item active"><a class="page-link" href="#">2</a></li>')
        self.assertNotContains(response, self.contract2.contract_name)
