from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission
import datetime

from ..models import ClientContract, ClientContractHaken
from apps.client.models import Client, ClientUser, ClientDepartment
from apps.company.models import Company, CompanyUser
from apps.master.models import ContractPattern
from apps.system.logs.models import AppLog
from apps.system.settings.models import Dropdowns
from apps.common.constants import Constants

User = get_user_model()

class ClientContractHakenLogTest(TestCase):
    """
    ClientContractHaken（クライアント契約派遣情報）の変更が
    正しくログに記録され、詳細画面に表示されるかをテストする。
    """

    @classmethod
    def setUpTestData(cls):
        """テスト全体の準備"""
        # ユーザーと権限の設定
        cls.user = User.objects.create_user(username='logtestuser', password='password')
        content_type = ContentType.objects.get_for_model(ClientContract)
        permissions = Permission.objects.filter(content_type=content_type)
        cls.user.user_permissions.set(permissions)

        # 会社とクライアント
        cls.company = Company.objects.create(name='Test Company', corporate_number='1234567890123')
        cls.client_model = Client.objects.create(
            name='Test Client',
            corporate_number='9876543210987',
            basic_contract_date=datetime.date(2000, 1, 1),
            basic_contract_date_haken=datetime.date(2000, 1, 1)
        )

        # 派遣契約種別をDropdownに作成
        Dropdowns.objects.create(category='client_contract_type', name='派遣', value='20')
        cls.bill_unit = Dropdowns.objects.create(category='bill_unit', value='10', name='月額', active=True)

        # 契約書パターン
        cls.pattern = ContractPattern.objects.create(name='Haken Pattern', domain='10', contract_type_code='20')
        cls.non_haken_pattern = ContractPattern.objects.create(name='Non-Haken Pattern', domain='10', contract_type_code='10')

        # 派遣先・派遣元の担当者・部署
        cls.haken_office = ClientDepartment.objects.create(client=cls.client_model, name='Test Office', is_haken_office=True)
        cls.haken_unit = ClientDepartment.objects.create(client=cls.client_model, name='Test Unit', is_haken_unit=True)
        cls.client_user = ClientUser.objects.create(client=cls.client_model, name_last='Rep', name_first='Client', email='client@test.com')
        cls.company_user = CompanyUser.objects.create(name_last='Rep', name_first='Company', email='company@test.com')

    def setUp(self):
        """各テストの準備"""
        # 各テストの前に契約を再作成して独立性を保つ
        self.contract = ClientContract.objects.create(
            client=self.client_model,
            contract_name='Haken Contract Logging Test',
            contract_pattern=self.pattern,
            client_contract_type_code='20', # 派遣
            start_date=datetime.date.today(),
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
        )
        self.client.login(username='logtestuser', password='password')
        self.update_url = reverse('contract:client_contract_update', kwargs={'pk': self.contract.pk})
        AppLog.objects.all().delete()

    def test_haken_info_creation_log_and_display(self):
        """派遣情報の新規作成がログに記録され、詳細画面に表示されること。"""
        self.assertEqual(AppLog.objects.count(), 0)
        self.assertFalse(hasattr(self.contract, 'haken_info'))

        post_data = {
            'client': self.client_model.pk,
            'client_contract_type_code': '20',
            'contract_name': self.contract.contract_name,
            'contract_pattern': self.pattern.pk,
            'contract_number': self.contract.contract_number or '',
            'start_date': self.contract.start_date.strftime('%Y-%m-%d'),
            'end_date': (self.contract.start_date + datetime.timedelta(days=365)).strftime('%Y-%m-%d'),
            'bill_unit': self.bill_unit.value,
            'haken_office': self.haken_office.pk,
            'haken_unit': self.haken_unit.pk,
            'commander': self.client_user.pk,
            'complaint_officer_client': self.client_user.pk,
            'responsible_person_client': self.client_user.pk,
            'complaint_officer_company': self.company_user.pk,
            'responsible_person_company': self.company_user.pk,
            'limit_by_agreement': '0',
            'limit_indefinite_or_senior': '0',
        }

        response = self.client.post(self.update_url, data=post_data)
        self.assertEqual(response.status_code, 302, "Form submission should be successful and redirect.")

        # 自動ログが1件作成されていることを確認
        self.assertEqual(AppLog.objects.filter(model_name='ClientContractHaken', action='create').count(), 1)

        # 詳細ビューを取得
        detail_url = reverse('contract:client_contract_detail', kwargs={'pk': self.contract.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)

        # ログが表示されていることを確認 (verbose_nameで判定)
        self.assertContains(response, '派遣情報', msg_prefix="Change history should display the verbose name for Haken info.")
        # Adding a related object in an update view is considered an 'update' action by the automatic logger
        self.assertContains(response, '編集', msg_prefix="Change history should contain the 'Update' action.")

    def test_haken_info_update_log_and_display(self):
        """派遣情報の更新がログに記録され、詳細画面に表示されること。"""
        haken_info = ClientContractHaken.objects.create(
            client_contract=self.contract,
            haken_office=self.haken_office,
            haken_unit=self.haken_unit,
            commander=self.client_user,
            complaint_officer_client=self.client_user,
            responsible_person_client=self.client_user,
            complaint_officer_company=self.company_user,
            responsible_person_company=self.company_user,
            limit_by_agreement='0',
            limit_indefinite_or_senior='0',
        )
        AppLog.objects.all().delete()
        new_client_user = ClientUser.objects.create(client=self.client_model, name_last='New', name_first='Rep', email='new@test.com')

        post_data = {
            'client': self.client_model.pk,
            'client_contract_type_code': '20',
            'contract_name': self.contract.contract_name,
            'contract_pattern': self.pattern.pk,
            'contract_number': self.contract.contract_number or '',
            'start_date': self.contract.start_date.strftime('%Y-%m-%d'),
            'end_date': (self.contract.start_date + datetime.timedelta(days=365)).strftime('%Y-%m-%d'),
            'bill_unit': self.bill_unit.value,
            'haken_office': self.haken_office.pk,
            'haken_unit': self.haken_unit.pk,
            'commander': new_client_user.pk, # 更新
            'complaint_officer_client': self.client_user.pk,
            'responsible_person_client': self.client_user.pk,
            'complaint_officer_company': self.company_user.pk,
            'responsible_person_company': self.company_user.pk,
            'limit_by_agreement': '1', # 更新
            'limit_indefinite_or_senior': '0',
        }

        response = self.client.post(self.update_url, data=post_data)
        self.assertEqual(response.status_code, 302, "Form submission should be successful and redirect.")

        self.assertEqual(AppLog.objects.filter(model_name='ClientContractHaken', action='update').count(), 1)

        detail_url = reverse('contract:client_contract_detail', kwargs={'pk': self.contract.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, '派遣情報', msg_prefix="Change history should display the verbose name for Haken info.")
        self.assertContains(response, '編集', msg_prefix="Change history should contain the 'Update' action.")

