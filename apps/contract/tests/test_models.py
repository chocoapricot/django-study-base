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
