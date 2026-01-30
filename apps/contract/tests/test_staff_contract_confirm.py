from datetime import date
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.staff.models import Staff
from apps.company.models import Company
from apps.connect.models import ConnectStaff, ConnectStaffAgree
from apps.master.models import StaffAgreement
from apps.contract.models import StaffContract
from apps.common.middleware import set_current_tenant_id
from apps.common.constants import Constants
from apps.system.settings.models import Dropdowns

class StaffContractConfirmTest(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            name='Test Company',
            corporate_number='1234567890123',
        )
        set_current_tenant_id(self.company.id)

        # Dropdownsデータを作成
        statuses = [
            (Constants.CONTRACT_STATUS.DRAFT, '作成中'),
            (Constants.CONTRACT_STATUS.PENDING, '申請'),
            (Constants.CONTRACT_STATUS.APPROVED, '承認済'),
            (Constants.CONTRACT_STATUS.ISSUED, '発行済'),
            (Constants.CONTRACT_STATUS.CONFIRMED, '確認済'),
        ]
        for value, name in statuses:
            Dropdowns.objects.create(
                category='contract_status',
                value=value,
                name=name,
                active=True
            )
        
        self.user = get_user_model().objects.create_user(
            tenant_id=self.company.id,
            username='testuser@example.com',
            email='testuser@example.com',
            password='password',
            is_staff=True,
            is_active=True,
        )
        self.staff = Staff.objects.create(
            tenant_id=self.company.id,
            email='testuser@example.com',
            name_last='Test',
            name_first='User',
        )
        self.connect_staff = ConnectStaff.objects.create(
            corporate_number=self.company.corporate_number,
            email=self.user.email,
            status='approved',
        )
        self.staff_agreement = StaffAgreement.objects.create(
            tenant_id=self.company.id,
            name='Test Agreement',
            agreement_text='This is a test agreement.',
            corporation_number=self.company.corporate_number,
        )
        from apps.master.models import ContractPattern
        from apps.contract.models import StaffContractPrint
        from django.utils import timezone
        
        self.staff_pattern = ContractPattern.objects.create(tenant_id=self.company.id, name='スタッフ向け雇用契約', domain='1', is_active=True)
        self.contract = StaffContract.objects.create(
            tenant_id=self.company.id,
            staff=self.staff,
            corporate_number=self.company.corporate_number,
            contract_name='Test Contract',
            contract_status=Constants.CONTRACT_STATUS.ISSUED,
            start_date=date(2025, 1, 1),
            contract_pattern=self.staff_pattern,
            issued_at=timezone.now(),
            issued_by=self.user
        )
        
        # 契約書の印刷履歴を作成
        self.print_history = StaffContractPrint.objects.create(
            tenant_id=self.company.id,
            staff_contract=self.contract,
            printed_by=self.user,
            document_title='Test Contract PDF',
            contract_number='SC-2025-001'
        )

    def test_staff_contract_confirm_list_get(self):
        """
        Test GET request to staff_contract_confirm_list view.
        """
        self.client.login(email='testuser@example.com', password='password')
        session = self.client.session
        session['current_tenant_id'] = self.company.id
        session.save()

        response = self.client.get(reverse('contract:staff_contract_confirm_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'スタッフ契約確認')
        self.assertContains(response, 'Test Contract')
        self.assertContains(response, '未確認')  # 確認状況として「未確認」が表示される

    def test_staff_contract_confirm_list_post(self):
        """
        Test POST request to staff_contract_confirm_list view to confirm a contract.
        """
        self.client.login(email='testuser@example.com', password='password')
        session = self.client.session
        session['current_tenant_id'] = self.company.id
        session.save()

        response = self.client.post(reverse('contract:staff_contract_confirm_list'), {'contract_id': self.contract.id, 'action': 'confirm_staff_contract'})
        self.assertEqual(response.status_code, 302) # Should redirect

        # Check if the agreement was created
        self.assertTrue(
            ConnectStaffAgree.objects.filter(
                email=self.user.email,
                corporate_number=self.company.corporate_number,
                staff_agreement=self.staff_agreement,
                is_agreed=True
            ).exists()
        )
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.contract_status, Constants.CONTRACT_STATUS.CONFIRMED)

    def test_staff_contract_unconfirm(self):
        """
        Test POST request to staff_contract_confirm_list view to un-confirm a contract.
        """
        # First, confirm the contract
        self.contract.contract_status = Constants.CONTRACT_STATUS.CONFIRMED
        self.contract.save()

        self.client.login(email='testuser@example.com', password='password')
        session = self.client.session
        session['current_tenant_id'] = self.company.id
        session.save()

        response = self.client.post(reverse('contract:staff_contract_confirm_list'), {'contract_id': self.contract.id, 'action': 'unconfirm_staff_contract'})
        self.assertEqual(response.status_code, 302) # Should redirect

        self.contract.refresh_from_db()
        self.assertEqual(self.contract.contract_status, Constants.CONTRACT_STATUS.ISSUED)
