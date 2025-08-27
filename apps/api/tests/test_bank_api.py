from django.test import TestCase, Client
from django.urls import reverse
from apps.master.models import Bank, BankBranch
from apps.accounts.models import MyUser

class BankAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = MyUser.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')

        self.bank1 = Bank.objects.create(name='Test Bank 1', bank_code='0001')
        self.bank2 = Bank.objects.create(name='Another Bank', bank_code='0002')
        self.branch1 = BankBranch.objects.create(bank=self.bank1, name='Main Branch', branch_code='001')
        self.branch2 = BankBranch.objects.create(bank=self.bank1, name='Sub Branch', branch_code='002')

    def test_search_banks(self):
        """Test the search_banks API endpoint."""
        url = reverse('search_banks')
        response = self.client.get(url, {'q': 'Test'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]['name'], 'Test Bank 1')

        response = self.client.get(url, {'q': 'Bank'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)

        response = self.client.get(url, {'q': '0001'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

        response = self.client.get(url, {'q': 'NonExistent'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)

    def test_search_bank_branches(self):
        """Test the search_bank_branches API endpoint."""
        url = reverse('search_bank_branches')

        # Search for branches of bank1
        response = self.client.get(url, {'bank_code': '0001', 'q': 'Main'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]['name'], 'Main Branch')

        response = self.client.get(url, {'bank_code': '0001', 'q': 'Branch'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)

        response = self.client.get(url, {'bank_code': '0001', 'q': '001'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

        # Search for non-existent branch
        response = self.client.get(url, {'bank_code': '0001', 'q': 'NonExistent'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)

        # Search with non-existent bank code
        response = self.client.get(url, {'bank_code': '9999', 'q': 'Main'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)
