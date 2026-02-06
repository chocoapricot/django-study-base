from django.test import TestCase, Client
from apps.company.models import Company, CompanyDepartment
from apps.company.forms import CompanyDepartmentForm
from django.contrib.auth import get_user_model
from django.urls import reverse
from datetime import date

class CompanyDepartmentFormErrorTest(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.admin_user = self.User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='password'
        )
        self.company = Company.objects.create(
            name="テスト会社",
            corporate_number="8011101011499",
            tenant_id=1
        )
        self.admin_user.tenant_id = 1
        self.admin_user.save()

        self.dept1 = CompanyDepartment.objects.create(
            name="部署1",
            corporate_number="8011101011499",
            department_code="DEP001",
            valid_from=date(2024, 1, 1),
            valid_to=date(2024, 12, 31),
            tenant_id=1
        )
        self.client = Client()
        self.client.login(username='admin', password='password')

    def test_overlapping_period_form_error(self):
        """部署コードが重複し、期間が重なる場合のフォームエラー確認"""
        url = reverse('company:department_create')
        data = {
            'name': '部署2',
            'corporate_number': '8011101011499',
            'department_code': 'DEP001', # 同じ部署コード
            'valid_from': '2024-06-01',   # 期間が重なる
            'valid_to': '2025-05-31',
            'display_order': 0,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200) # バリデーションエラーで画面に戻る

        form = response.context['form']
        self.assertFalse(form.is_valid())
        self.assertTrue(len(form.non_field_errors()) > 0)
        self.assertIn('重複しています', form.non_field_errors()[0])

        # テンプレートに表示されているか確認
        self.assertContains(response, '重複しています')
