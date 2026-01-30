from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.staff.models import Staff
from apps.contract.models import StaffContract
from apps.company.models import Company
from apps.connect.models import ConnectStaff, ConnectStaffAgree
from apps.master.models import StaffAgreement, ContractPattern, OvertimePattern
from apps.common.middleware import set_current_tenant_id
from datetime import date

User = get_user_model()

class KintaiAgreementRedirectTest(TestCase):
    """勤怠画面での同意チェックリダイレクトのテスト"""

    def setUp(self):
        # 会社情報
        self.corporate_number = '1234567890123'
        self.company = Company.objects.create(
            corporate_number=self.corporate_number,
            name='Test Company',
        )
        set_current_tenant_id(self.company.id)

        self.client = Client()
        self.email = 'staff@example.com'
        self.password = 'TestPass123!'
        self.user = User.objects.create_user(
            tenant_id=self.company.id,
            username='staff',
            email=self.email,
            password=self.password,
            is_staff=False,
        )
        
        # スタッフ情報
        self.staff = Staff.objects.create(
            tenant_id=self.company.id,
            name_last='Test',
            name_first='Staff',
            email=self.email,
        )
        
        # 必要マスタ
        self.pattern = ContractPattern.objects.create(
            tenant_id=self.company.id,
            name='Test Pattern',
            domain='1', # スタッフ
        )
        self.overtime = OvertimePattern.objects.create(
            tenant_id=self.company.id,
            name='Test Overtime',
        )
        
        # 契約情報
        self.contract = StaffContract.objects.create(
            tenant_id=self.company.id,
            staff=self.staff,
            corporate_number=self.corporate_number,
            start_date=date(2025, 1, 1),
            contract_pattern=self.pattern,
            overtime_pattern=self.overtime,
            contract_name='Test Contract',
        )
        
        # 規約
        self.agreement = StaffAgreement.objects.create(
            tenant_id=self.company.id,
            name='Test Agreement',
            agreement_text='Please agree.',
            corporation_number=self.corporate_number,
            is_active=True,
        )
        
        # 接続申請（承認済み）
        self.connection = ConnectStaff.objects.create(
            email=self.email,
            corporate_number=self.corporate_number,
            status='approved',
        )

    def test_only_confirmed_contracts_are_listed(self):
        """確認済み契約のみがリストに表示されるか"""
        # 同意済み状態にする
        ConnectStaffAgree.objects.create(
            email=self.email,
            corporate_number=self.corporate_number,
            staff_agreement=self.agreement,
            is_agreed=True,
        )
        
        # 承認済み（未確認）の契約を追加
        unconfirmed_contract = StaffContract.objects.create(
            tenant_id=self.company.id,
            staff=self.staff,
            corporate_number=self.corporate_number,
            start_date=date(2025, 1, 1),
            contract_pattern=self.pattern,
            overtime_pattern=self.overtime,
            contract_name='Unconfirmed Contract',
            contract_status='10', # 承認済み (Constants.CONTRACT_STATUS.APPROVED)
        )
        
        # 確認済みの契約を明示的に設定
        self.contract.contract_status = '30' # Constants.CONTRACT_STATUS.CONFIRMED
        self.contract.save()
        
        self.client.login(email=self.email, password=self.password)
        session = self.client.session
        session['current_tenant_id'] = self.company.id
        session.save()
        
        url = reverse('kintai:staff_timecard_register')
        response = self.client.get(url)
        
        # 確認済みの契約のみが含まれていることを確認
        self.assertContains(response, 'Test Contract')
        self.assertNotContains(response, 'Unconfirmed Contract')

    def test_cannot_access_unconfirmed_contract_detail(self):
        """未確認の契約詳細（登録開始）にアクセスした際に404になるか"""
        # 同意済み状態にする
        ConnectStaffAgree.objects.create(
            email=self.email,
            corporate_number=self.corporate_number,
            staff_agreement=self.agreement,
            is_agreed=True,
        )

        unconfirmed_contract = StaffContract.objects.create(
            tenant_id=self.company.id,
            staff=self.staff,
            corporate_number=self.corporate_number,
            start_date=date(2025, 1, 1),
            contract_pattern=self.pattern,
            overtime_pattern=self.overtime,
            contract_name='Unconfirmed Contract',
            contract_status='10',
        )
        
        self.client.login(email=self.email, password=self.password)
        session = self.client.session
        session['current_tenant_id'] = self.company.id
        session.save()
        
        url = reverse('kintai:staff_timecard_register_detail', kwargs={
            'contract_pk': unconfirmed_contract.pk,
            'target_month': '2025-01'
        })
        response = self.client.get(url)
        
        # 404 Not Found (get_object_or_404で落ちるはず)
        self.assertEqual(response.status_code, 404)

    def test_redirect_to_agree_page_from_register_list(self):
        """契約選択画面にアクセスした際に同意画面にリダイレクトされるか"""
        self.client.login(email=self.email, password=self.password)
        session = self.client.session
        session['current_tenant_id'] = self.company.id
        session.save()
        
        url = reverse('kintai:staff_timecard_register')
        response = self.client.get(url)
        
        # 同意画面へのリダイレクトを確認
        agree_url = reverse('connect:staff_agree', kwargs={'pk': self.connection.pk})
        self.assertRedirects(response, f'{agree_url}?next={url}')

    def test_no_redirect_after_agreement(self):
        """同意済みの場合、リダイレクトされないか"""
        # 同意を記録
        ConnectStaffAgree.objects.create(
            email=self.email,
            corporate_number=self.corporate_number,
            staff_agreement=self.agreement,
            is_agreed=True,
        )
        
        self.client.login(email=self.email, password=self.password)
        session = self.client.session
        session['current_tenant_id'] = self.company.id
        session.save()
        
        url = reverse('kintai:staff_timecard_register')
        response = self.client.get(url)
        
        # リダイレクトされず200 OK
        self.assertEqual(response.status_code, 200)

    def test_admin_is_exempt(self):
        """管理者はリダイレクトされないか"""
        admin_email = 'admin@example.com'
        admin_user = User.objects.create_user(
            tenant_id=self.company.id,
            username='admin',
            email=admin_email,
            password=self.password,
            is_staff=True,
        )
        # 権限を付与
        from django.contrib.auth.models import Permission
        permissions = Permission.objects.filter(
            content_type__app_label='kintai',
            content_type__model__in=['stafftimesheet', 'stafftimecard']
        )
        admin_user.user_permissions.set(permissions)
        self.client.login(email=admin_email, password=self.password)
        session = self.client.session
        session['current_tenant_id'] = self.company.id
        session.save()
        
        # 管理者がスタッフ検索画面にアクセス（この画面にはデコレータをつけていないが、念のため）
        url = reverse('kintai:staff_search')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # 管理者がカレンダー入力画面（デコレータあり）にアクセス
        # タイムシートを作成
        from apps.kintai.models import StaffTimesheet
        timesheet = StaffTimesheet.objects.create(
            staff=self.staff,
            staff_contract=self.contract,
            target_month=date(2025, 1, 1),
        )
        url = reverse('kintai:timecard_calendar', kwargs={'timesheet_pk': timesheet.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
