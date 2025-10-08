from django.urls import reverse
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.accounts.models import MyUser
from apps.client.models import Client, ClientDepartment
from apps.company.models import Company
from apps.contract.models import ClientContract, ClientContractHaken, ClientContractTtp
from apps.master.models import ContractPattern, Dropdowns


class ClientContractTtpViewsTest(TestCase):
    def setUp(self):
        # 会社情報
        self.company = Company.objects.create(
            name='テスト会社',
            corporate_number='1234567890123',
        )
        # ログインユーザー
        self.user = MyUser.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='password'
        )
        # 必要な権限をユーザーに付与
        content_type = ContentType.objects.get_for_model(ClientContract)
        permissions = Permission.objects.filter(
            content_type=content_type,
            codename__in=['view_clientcontract', 'add_clientcontract', 'change_clientcontract', 'delete_clientcontract']
        )
        self.user.user_permissions.set(permissions)

        self.client.login(email='testuser@example.com', password='password')
        # クライアント
        self.client_obj = Client.objects.create(
            name='テストクライアント',
            corporate_number='9876543210987',
            created_by=self.user,
        )
        # 契約種別マスタ
        Dropdowns.objects.create(category='client_contract_type', value='20', name='派遣')
        # 契約書パターン
        self.pattern = ContractPattern.objects.create(
            name='テスト派遣パターン',
            domain='10', # クライアント契約
            contract_type_code='20', # 派遣
        )
        # クライアント契約
        self.contract = ClientContract.objects.create(
            client=self.client_obj,
            contract_name='テスト派遣契約',
            client_contract_type_code='20',
            contract_pattern=self.pattern,
            start_date=timezone.now().date(),
            created_by=self.user,
        )
        # 派遣情報
        self.haken = ClientContractHaken.objects.create(
            client_contract=self.contract,
            created_by=self.user,
        )

    def test_client_contract_ttp_view_redirects_to_create(self):
        """TTP情報がない場合、作成画面にリダイレクトされることをテスト"""
        response = self.client.get(reverse('contract:client_contract_ttp_view', kwargs={'haken_pk': self.haken.pk}))
        self.assertRedirects(response, reverse('contract:client_contract_ttp_create', kwargs={'haken_pk': self.haken.pk}))

    def test_client_contract_ttp_view_redirects_to_detail(self):
        """TTP情報がある場合、詳細画面にリダイレクトされることをテスト"""
        ttp_info = ClientContractTtp.objects.create(haken=self.haken, created_by=self.user)
        response = self.client.get(reverse('contract:client_contract_ttp_view', kwargs={'haken_pk': self.haken.pk}))
        self.assertRedirects(response, reverse('contract:client_contract_ttp_detail', kwargs={'pk': ttp_info.pk}))

    def test_client_contract_ttp_create_view(self):
        """TTP情報作成ビューのテスト"""
        # GET
        response = self.client.get(reverse('contract:client_contract_ttp_create', kwargs={'haken_pk': self.haken.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'contract/client_contract_ttp_form.html')
        # ヘッダーが表示されていることを確認
        self.assertContains(response, '契約番号')
        self.assertContains(response, self.contract.contract_name)

        # POST
        post_data = {
            'contract_period': '2025年1月1日～2025年6月30日',
            'business_content': 'テスト業務',
        }
        response = self.client.post(reverse('contract:client_contract_ttp_create', kwargs={'haken_pk': self.haken.pk}), post_data)
        self.assertEqual(ClientContractTtp.objects.count(), 1)
        ttp_info = ClientContractTtp.objects.first()
        self.assertEqual(ttp_info.haken, self.haken)
        self.assertEqual(ttp_info.contract_period, '2025年1月1日～2025年6月30日')
        self.assertRedirects(response, reverse('contract:client_contract_ttp_detail', kwargs={'pk': ttp_info.pk}))

    def test_client_contract_ttp_detail_view(self):
        """TTP情報詳細ビューのテスト"""
        ttp_info = ClientContractTtp.objects.create(
            haken=self.haken,
            contract_period='テスト期間',
            created_by=self.user,
        )
        response = self.client.get(reverse('contract:client_contract_ttp_detail', kwargs={'pk': ttp_info.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'テスト期間')
        self.assertTemplateUsed(response, 'contract/client_contract_ttp_detail.html')
        # ヘッダーが表示されていることを確認
        self.assertContains(response, '契約番号')
        self.assertContains(response, self.contract.contract_name)

    def test_client_contract_ttp_update_view(self):
        """TTP情報更新ビューのテスト"""
        ttp_info = ClientContractTtp.objects.create(haken=self.haken, created_by=self.user)
        # GET
        response = self.client.get(reverse('contract:client_contract_ttp_update', kwargs={'pk': ttp_info.pk}))
        self.assertEqual(response.status_code, 200)
        # ヘッダーが表示されていることを確認
        self.assertContains(response, '契約番号')
        self.assertContains(response, self.contract.contract_name)

        # POST
        post_data = {
            'contract_period': '更新された期間',
        }
        response = self.client.post(reverse('contract:client_contract_ttp_update', kwargs={'pk': ttp_info.pk}), post_data)
        ttp_info.refresh_from_db()
        self.assertEqual(ttp_info.contract_period, '更新された期間')
        self.assertRedirects(response, reverse('contract:client_contract_ttp_detail', kwargs={'pk': ttp_info.pk}))

    def test_client_contract_ttp_delete_view(self):
        """TTP情報削除ビューのテスト"""
        ttp_info = ClientContractTtp.objects.create(haken=self.haken, created_by=self.user)
        # GET
        response = self.client.get(reverse('contract:client_contract_ttp_delete', kwargs={'pk': ttp_info.pk}))
        self.assertEqual(response.status_code, 200)
        # ヘッダーが表示されていることを確認
        self.assertContains(response, '契約番号')
        self.assertContains(response, self.contract.contract_name)

        # POST
        response = self.client.post(reverse('contract:client_contract_ttp_delete', kwargs={'pk': ttp_info.pk}))
        self.assertEqual(ClientContractTtp.objects.count(), 0)
        self.assertRedirects(response, reverse('contract:client_contract_detail', kwargs={'pk': self.contract.pk}))

    def test_ttp_menu_in_contract_detail(self):
        """契約詳細画面にTTPメニューが表示されるかテスト"""
        # 派遣契約の場合、表示される
        response = self.client.get(reverse('contract:client_contract_detail', kwargs={'pk': self.contract.pk}))
        self.assertContains(response, 'TTP')
        self.assertContains(response, reverse('contract:client_contract_ttp_view', kwargs={'haken_pk': self.haken.pk}))

        # 派遣契約でない場合、表示されない
        self.contract.client_contract_type_code = '10' # 業務委託
        self.contract.save()
        self.haken.delete()
        response = self.client.get(reverse('contract:client_contract_detail', kwargs={'pk': self.contract.pk}))
        self.assertNotContains(response, 'TTP')