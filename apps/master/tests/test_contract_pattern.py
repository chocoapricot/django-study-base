from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.master.models import ContractPattern, ContractTerms

User = get_user_model()

class ContractPatternCopyTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser(username='testuser', password='password', email='test@test.com')
        self.client.login(username='testuser', password='password')

        self.pattern = ContractPattern.objects.create(
            name='Original Pattern',
            contract_type='staff',
        )
        self.term1 = ContractTerms.objects.create(
            contract_pattern=self.pattern,
            contract_clause='Clause 1',
            contract_terms='Terms 1',
            display_order=1,
        )
        self.term2 = ContractTerms.objects.create(
            contract_pattern=self.pattern,
            contract_clause='Clause 2',
            contract_terms='Terms 2',
            display_order=2,
        )
        self.copy_url = reverse('master:contract_pattern_copy', kwargs={'pk': self.pattern.pk})
        self.list_url = reverse('master:contract_pattern_list')

    def test_list_view_with_copy_dropdown(self):
        """
        Test that the list view contains the dropdown and the copy button is initially disabled.
        """
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="copyButton"')
        self.assertContains(response, 'class="dropdown-item disabled"')

    def test_copy_view_get(self):
        """
        Test the GET request for the copy view.
        """
        response = self.client.get(self.copy_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'master/contract_pattern_form.html')
        self.assertContains(response, '契約パターンコピー作成')
        self.assertContains(response, '契約文言もコピーされます')
        self.assertContains(response, 'value="Original Patternのコピー"')

    def test_copy_view_post(self):
        """
        Test the POST request for the copy view.
        """
        new_pattern_name = 'Copied Pattern'
        post_data = {
            'name': new_pattern_name,
            'contract_type': 'staff',
            'display_order': '10',
            'is_active': 'on',
        }
        response = self.client.post(self.copy_url, post_data, follow=True)

        # Check if it redirects to the list view and shows a success message
        self.assertRedirects(response, reverse('master:contract_pattern_list'))
        self.assertContains(response, "をコピーして")

        # Check if the new pattern was created
        self.assertTrue(ContractPattern.objects.filter(name=new_pattern_name).exists())
        new_pattern = ContractPattern.objects.get(name=new_pattern_name)

        # Check if the terms were copied
        self.assertEqual(new_pattern.terms.count(), 2)
        self.assertTrue(new_pattern.terms.filter(contract_clause='Clause 1').exists())
        self.assertTrue(new_pattern.terms.filter(contract_clause='Clause 2').exists())

        # Check that the original pattern still exists and has its terms
        self.pattern.refresh_from_db()
        self.assertEqual(self.pattern.terms.count(), 2)
