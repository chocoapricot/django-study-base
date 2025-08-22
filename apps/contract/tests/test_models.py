from django.test import TestCase
from django.contrib.auth import get_user_model
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

    def test_client_contract_creation(self):
        """クライアント契約の作成テスト"""
        contract = ClientContract.objects.create(
            client=self.client_obj,
            contract_name='テスト契約',
            contract_type='service',
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=365),
            contract_amount=1000000,
            created_by=self.user,
            updated_by=self.user
        )

        self.assertEqual(contract.client, self.client_obj)
        self.assertEqual(contract.contract_name, 'テスト契約')
        self.assertTrue(contract.is_active)
        self.assertTrue(contract.is_current)

    def test_staff_contract_creation(self):
        """スタッフ契約の作成テスト"""
        contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name='雇用契約',
            contract_type='full_time',
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=365),
            contract_amount=300000,
            created_by=self.user,
            updated_by=self.user
        )

        self.assertEqual(contract.staff, self.staff)
        self.assertEqual(contract.contract_name, '雇用契約')
        self.assertTrue(contract.is_active)
        self.assertTrue(contract.is_current)
