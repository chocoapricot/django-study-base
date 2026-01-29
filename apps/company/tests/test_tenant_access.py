from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.http import Http404
from ..models import Company

User = get_user_model()

class CompanyTenantAccessTest(TestCase):
    """会社情報のテナントアクセス制限テスト"""

    def setUp(self):
        self.client = Client()
        
        # 会社A
        self.company_a = Company.objects.create(
            name="会社A",
            corporate_number="1111111111111",
            tenant_id=100
        )
        # 会社B
        self.company_b = Company.objects.create(
            name="会社B",
            corporate_number="2222222222222",
            tenant_id=200
        )

        # 会社Aに所属する一般ユーザー
        self.user_a = User.objects.create_user(
            username='user_a',
            email='user_a@example.com',
            password='password',
            tenant_id=100
        )
        self.user_a.user_permissions.add(Permission.objects.get(codename='view_company'))

        # テナントIDを持たない一般ユーザー
        self.user_no_tenant = User.objects.create_user(
            username='user_no_tenant',
            email='no_tenant@example.com',
            password='password'
        )
        self.user_no_tenant.user_permissions.add(Permission.objects.get(codename='view_company'))

        # テナントIDを持たない管理者（スーパーユーザー）
        self.admin_user = User.objects.create_superuser(
            username='admin_user',
            email='admin@example.com',
            password='password'
        )

    def test_user_with_tenant_id_sees_only_own_company(self):
        """テナントIDを持つユーザーは、自分の会社情報のみ表示される"""
        self.client.login(username='user_a', password='password')
        response = self.client.get(reverse('company:company_detail'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "会社A")
        self.assertNotContains(response, "会社B")

    def test_admin_without_tenant_id_sees_first_company(self):
        """テナントIDを持たない管理者は、最初の会社情報が表示される"""
        self.client.login(username='admin_user', password='password')
        response = self.client.get(reverse('company:company_detail'))
        self.assertEqual(response.status_code, 200)
        # 最初に作成されたのは会社A
        self.assertContains(response, "会社A")

    def test_user_without_tenant_id_gets_error(self):
        """テナントIDを持たない非管理者は、会社詳細アクセス時にエラー（404）となる"""
        self.client.login(username='user_no_tenant', password='password')
        response = self.client.get(reverse('company:company_detail'))
        self.assertEqual(response.status_code, 404)

    def test_admin_can_switch_companies(self):
        """管理者はGETパラメータで会社を切り替えることができ、セッションに保存される"""
        self.client.login(username='admin_user', password='password')
        
        # 最初は会社A（最初の会社）が表示される
        response = self.client.get(reverse('company:company_detail'))
        self.assertContains(response, "会社A")
        
        # 会社Bに切り替える
        response = self.client.get(reverse('company:company_detail') + f'?company_id={self.company_b.pk}')
        self.assertContains(response, "会社B")
        self.assertEqual(self.client.session['current_tenant_id'], self.company_b.tenant_id)
        
        # パラメータなしで再度アクセスしても、セッションから会社Bが維持される
        response = self.client.get(reverse('company:company_detail'))
        self.assertContains(response, "会社B")
