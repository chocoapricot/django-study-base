import os
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.auth.models import Permission

from apps.client.models import Client
from apps.contract.models import ClientContract, ClientContractPrint
from apps.master.models import ContractPattern

User = get_user_model()

class ClientContractStatusUITest(TestCase):
    """クライアント契約のステータスとUIに関するテスト"""

    def setUp(self):
        """テストデータの準備"""
        self.user = User.objects.create_user(username='testuser', password='password', is_staff=True)
        permissions = Permission.objects.filter(
            codename__in=['change_clientcontract', 'view_clientcontract']
        )
        self.user.user_permissions.add(*permissions)
        self.client.force_login(self.user)

        self.client_obj = Client.objects.create(name='テストクライアント', created_by=self.user, updated_by=self.user)
        self.pattern = ContractPattern.objects.create(name='テストパターン', domain='10')
        self.base_data = {
            'client': self.client_obj,
            'contract_name': 'テスト契約',
            'contract_pattern': self.pattern,
            'start_date': timezone.now().date(),
            'created_by': self.user,
            'updated_by': self.user,
        }
