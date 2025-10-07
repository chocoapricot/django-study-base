from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.master.models import JobCategory, ContractPattern
from django.utils import timezone
from datetime import timedelta
from apps.client.models import Client as ClientModel
from apps.staff.models import Staff
from ..models import ClientContract, StaffContract

User = get_user_model()

class ContractModelTest(TestCase):
    """契約モデルのテスト"""

    def setUp(self):
        """テストデータの準備"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # テスト用クライアント
        self.client_obj = ClientModel.objects.create(
            name='テストクライアント',
            created_by=self.user,
            updated_by=self.user
        )

        # テスト用スタッフ
        self.staff = Staff.objects.create(
            name_last='田中',
            name_first='太郎',
            created_by=self.user,
            updated_by=self.user
        )

        self.job_category = JobCategory.objects.create(name='エンジニア', is_active=True)
        self.client_pattern = ContractPattern.objects.create(name='クライアント向け基本契約', domain='10', is_active=True)
        self.staff_pattern = ContractPattern.objects.create(name='スタッフ向け雇用契約', domain='1', is_active=True)

    def test_client_contract_with_new_fields(self):
        """クライアント契約モデル（新しいフィールドあり）のテスト"""
        contract = ClientContract.objects.create(
            client=self.client_obj,
            contract_name='新機能テスト契約',
            job_category=self.job_category,
            contract_pattern=self.client_pattern,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=365),
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(contract.job_category, self.job_category)
        self.assertEqual(contract.contract_pattern, self.client_pattern)

    def test_staff_contract_with_new_fields(self):
        """スタッフ契約モデル（新しいフィールドあり）のテスト"""
        contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name='新機能テスト雇用契約',
            job_category=self.job_category,
            contract_pattern=self.staff_pattern,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=365),
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(contract.job_category, self.job_category)
        self.assertEqual(contract.contract_pattern, self.staff_pattern)

    def test_client_contract_creation(self):
        """クライアント契約の作成テスト"""
        contract = ClientContract.objects.create(
            client=self.client_obj,
            contract_name='テスト契約',
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=365),
            contract_amount=1000000,
            created_by=self.user,
            updated_by=self.user,
            contract_pattern=self.client_pattern
        )

        self.assertEqual(contract.client, self.client_obj)
        self.assertEqual(contract.contract_name, 'テスト契約')

    def test_staff_contract_creation(self):
        """スタッフ契約の作成テスト"""
        contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name='雇用契約',
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=365),
            contract_amount=300000,
            created_by=self.user,
            updated_by=self.user
        )

        self.assertEqual(contract.staff, self.staff)
        self.assertEqual(contract.contract_name, '雇用契約')


from django.core.exceptions import ValidationError
from datetime import date
from apps.company.models import Company
from ..models import ClientContract, ClientContractHaken, ClientContractTtp
from apps.system.settings.models import Dropdowns

class ClientContractModelPropertyTests(TestCase):
    def setUp(self):
        # 必要なオブジェクトを作成
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='password')
        self.company = Company.objects.create(name='Test Company', corporate_number='1234567890123')
        self.client = ClientModel.objects.create(
            name='Test Client',
            created_by=self.user,
            corporate_number=self.company.corporate_number
        )
        self.contract_pattern = ContractPattern.objects.create(
            domain='10', name='Test Pattern', contract_type_code='20'
        )
        Dropdowns.objects.create(category='client_contract_type', value='20', name='派遣')
        Dropdowns.objects.create(category='client_contract_type', value='10', name='準委任')

    def test_contract_type_display_name(self):
        """TTP情報に基づいて契約種別の表示名が正しく変わることをテストする"""
        # 1. 派遣契約（TTPなし）
        contract_haken = ClientContract.objects.create(
            client=self.client,
            contract_name='Haken Contract',
            client_contract_type_code='20',
            contract_pattern=self.contract_pattern,
            start_date=date(2023, 1, 1),
            created_by=self.user,
        )
        self.assertEqual(contract_haken.contract_type_display_name, '派遣')

        # 2. 派遣契約（TTPあり）
        haken_info = ClientContractHaken.objects.create(client_contract=contract_haken)
        ClientContractTtp.objects.create(haken=haken_info)
        # refresh_from_dbは関連オブジェクトのキャッシュを更新しないため、再度オブジェクトを取得
        contract_haken_with_ttp = ClientContract.objects.get(pk=contract_haken.pk)
        self.assertEqual(contract_haken_with_ttp.contract_type_display_name, '派遣（TTP）')

        # 3. 派遣以外の契約
        contract_other = ClientContract.objects.create(
            client=self.client,
            contract_name='Other Contract',
            client_contract_type_code='10',  # 準委任
            contract_pattern=self.contract_pattern,
            start_date=date(2023, 1, 1),
            created_by=self.user,
        )
        self.assertEqual(contract_other.contract_type_display_name, '準委任')
