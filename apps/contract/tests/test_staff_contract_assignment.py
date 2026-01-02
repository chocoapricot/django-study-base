# -*- coding: utf-8 -*-
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from apps.contract.models import ClientContract, StaffContract, ContractAssignment
from apps.client.models import Client
from apps.staff.models import Staff
from apps.master.models import EmploymentType
from apps.master.models_worktime import WorkTimePattern
from apps.master.models import OvertimePattern
from apps.common.constants import Constants
from datetime import date, timedelta

User = get_user_model()


class StaffContractAssignmentTestCase(TestCase):
    """スタッフ契約アサインのテストケース"""

    def setUp(self):
        """テストデータのセットアップ"""
        # テストユーザー作成
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # 必要な権限を追加
        from django.contrib.auth.models import Permission
        permissions = Permission.objects.filter(
            codename__in=[
                'add_staffcontract', 'change_staffcontract', 'view_staffcontract',
                'add_clientcontract', 'change_clientcontract', 'view_clientcontract'
            ]
        )
        self.user.user_permissions.set(permissions)
        
        # 支払単位のドロップダウンを作成
        from apps.system.settings.models import Dropdowns
        Dropdowns.objects.create(
            category='pay_unit',
            value=Constants.PAY_UNIT.HOURLY,
            name='時間給',
            disp_seq=1,
            active=True
        )
        
        # 雇用形態作成
        self.employment_type = EmploymentType.objects.create(
            name='正社員',
            display_order=1,
            is_active=True
        )
        
        # 契約パターン作成（クライアント用とスタッフ用）
        from apps.master.models import ContractPattern
        self.client_contract_pattern = ContractPattern.objects.create(
            name='テストクライアント契約パターン',
            domain=Constants.DOMAIN.CLIENT,
            display_order=1,
            is_active=True
        )
        
        self.staff_contract_pattern = ContractPattern.objects.create(
            name='テストスタッフ契約パターン',
            domain=Constants.DOMAIN.STAFF,
            display_order=1,
            is_active=True,
            employment_type=self.employment_type
        )
        
        # 就業時間パターン作成
        self.worktime_pattern = WorkTimePattern.objects.create(
            name='標準勤務',
            is_active=True
        )
        
        # 時間外算出パターン作成
        self.overtime_pattern = OvertimePattern.objects.create(
            name='標準時間外',
            is_active=True
        )
        
        # クライアント作成
        self.client_obj = Client.objects.create(
            name='テストクライアント',
            corporate_number='1234567890123',
            basic_contract_date=date.today()
        )
        
        # スタッフ作成
        self.staff = Staff.objects.create(
            name_last='テスト',
            name_first='太郎',
            email='staff@example.com',
            employee_no='EMP001',
            hire_date=date.today(),
            employment_type=self.employment_type
        )
        
        # クライアント契約作成
        self.client_contract = ClientContract.objects.create(
            client=self.client_obj,
            contract_name='テストクライアント契約',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=365),
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            client_contract_type_code=Constants.CLIENT_CONTRACT_TYPE.DISPATCH,
            contract_pattern=self.client_contract_pattern,
            created_by=self.user,
            updated_by=self.user
        )
        
        # テストクライアント（Djangoのテストクライアント）
        self.client.login(username='testuser', password='testpass123')

    def test_normal_staff_contract_create(self):
        """通常のスタッフ契約作成テスト"""
        url = reverse('contract:staff_contract_create')
        data = {
            'staff': self.staff.pk,
            'contract_name': 'テストスタッフ契約',
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=365),
            'employment_type': self.employment_type.pk,
            'contract_pattern': self.staff_contract_pattern.pk,
            'pay_unit': Constants.PAY_UNIT.HOURLY,
            'contract_amount': '300000',
            'worktime_pattern': self.worktime_pattern.pk,
            'overtime_pattern': self.overtime_pattern.pk,
        }
        
        response = self.client.post(url, data)
        
        # スタッフ契約が作成されることを確認
        self.assertTrue(StaffContract.objects.filter(contract_name='テストスタッフ契約').exists())
        
        # スタッフ契約詳細にリダイレクトされることを確認
        staff_contract = StaffContract.objects.get(contract_name='テストスタッフ契約')
        self.assertRedirects(response, reverse('contract:staff_contract_detail', kwargs={'pk': staff_contract.pk}))

    def test_staff_contract_create_from_client_contract(self):
        """クライアント契約からのスタッフ契約作成テスト"""
        url = reverse('contract:staff_contract_create') + f'?client_contract={self.client_contract.pk}'
        data = {
            'staff': self.staff.pk,
            'contract_name': 'テストスタッフ契約（クライアント契約から）',
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=365),
            'employment_type': self.employment_type.pk,
            'contract_pattern': self.staff_contract_pattern.pk,
            'pay_unit': Constants.PAY_UNIT.HOURLY,
            'contract_amount': '300000',
            'worktime_pattern': self.worktime_pattern.pk,
            'overtime_pattern': self.overtime_pattern.pk,
        }
        
        response = self.client.post(url, data)
        
        # この時点ではスタッフ契約は作成されていないことを確認
        self.assertFalse(StaffContract.objects.filter(contract_name='テストスタッフ契約（クライアント契約から）').exists())
        
        # アサイン確認画面にリダイレクトされることを確認
        self.assertRedirects(response, reverse('contract:staff_assignment_confirm_from_create'), fetch_redirect_response=False)
        
        # セッションにデータが保存されていることを確認
        session = self.client.session
        self.assertIn('pending_staff_contract', session)
        self.assertEqual(session['pending_staff_contract']['client_contract_id'], str(self.client_contract.pk))

    def test_staff_assignment_confirm_from_create_get(self):
        """アサイン確認画面の表示テスト"""
        # セッションにデータを設定
        session = self.client.session
        session['pending_staff_contract'] = {
            'client_contract_id': self.client_contract.pk,
            'form_data': {
                'staff': str(self.staff.pk),
                'contract_name': 'テストスタッフ契約（確認画面）',
                'start_date': date.today().isoformat(),
                'end_date': (date.today() + timedelta(days=365)).isoformat(),
                'employment_type': str(self.employment_type.pk),
                'contract_pattern': str(self.staff_contract_pattern.pk),
                'pay_unit': Constants.PAY_UNIT.HOURLY,
                'contract_amount': '300000',
                'worktime_pattern': str(self.worktime_pattern.pk),
                'overtime_pattern': str(self.overtime_pattern.pk),
            },
            'from_view': 'client'
        }
        session.save()
        
        url = reverse('contract:staff_assignment_confirm_from_create')
        response = self.client.get(url)
        
        # 確認画面が表示されることを確認
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'スタッフ割当確認')
        self.assertContains(response, 'テストスタッフ契約（確認画面）')

    def test_create_assignment_from_create(self):
        """新規作成からのアサイン実行テスト"""
        # セッションにデータを設定
        session = self.client.session
        session['pending_staff_contract'] = {
            'client_contract_id': self.client_contract.pk,
            'form_data': {
                'staff': str(self.staff.pk),
                'contract_name': 'テストスタッフ契約（アサイン実行）',
                'start_date': date.today().isoformat(),
                'end_date': (date.today() + timedelta(days=365)).isoformat(),
                'employment_type': str(self.employment_type.pk),
                'contract_pattern': str(self.staff_contract_pattern.pk),
                'pay_unit': Constants.PAY_UNIT.HOURLY,
                'contract_amount': '300000',
                'worktime_pattern': str(self.worktime_pattern.pk),
                'overtime_pattern': str(self.overtime_pattern.pk),
            },
            'from_view': 'client'
        }
        session.save()
        
        url = reverse('contract:create_contract_assignment')
        data = {
            'client_contract_id': self.client_contract.pk,
            'staff_contract_id': 0,  # 新規作成の場合は無視される
            'from': 'client',
            'from_create': 'true'
        }
        
        response = self.client.post(url, data)
        
        # スタッフ契約が作成されることを確認
        self.assertTrue(StaffContract.objects.filter(contract_name='テストスタッフ契約（アサイン実行）').exists())
        
        # アサインが作成されることを確認
        staff_contract = StaffContract.objects.get(contract_name='テストスタッフ契約（アサイン実行）')
        self.assertTrue(ContractAssignment.objects.filter(
            client_contract=self.client_contract,
            staff_contract=staff_contract
        ).exists())
        
        # セッションがクリアされることを確認
        session = self.client.session
        self.assertNotIn('pending_staff_contract', session)
        
        # クライアント契約詳細にリダイレクトされることを確認
        self.assertRedirects(response, reverse('contract:client_contract_detail', kwargs={'pk': self.client_contract.pk}))

    def test_clear_assignment_session(self):
        """セッションクリアテスト"""
        # セッションにデータを設定
        session = self.client.session
        session['pending_staff_contract'] = {
            'client_contract_id': self.client_contract.pk,
            'form_data': {},
            'from_view': 'client'
        }
        session.save()
        
        url = reverse('contract:clear_assignment_session')
        data = {
            'redirect_to': reverse('contract:client_contract_assignment', kwargs={'pk': self.client_contract.pk})
        }
        
        response = self.client.post(url, data)
        
        # セッションがクリアされることを確認
        session = self.client.session
        self.assertNotIn('pending_staff_contract', session)
        
        # 指定されたURLにリダイレクトされることを確認
        self.assertRedirects(response, reverse('contract:client_contract_assignment', kwargs={'pk': self.client_contract.pk}))

    def test_staff_assignment_confirm_without_session(self):
        """セッションデータなしでアサイン確認画面にアクセスするテスト"""
        url = reverse('contract:staff_assignment_confirm_from_create')
        response = self.client.get(url)
        
        # エラーメッセージが表示されてトップページにリダイレクトされることを確認
        self.assertRedirects(response, reverse('contract:contract_index'))
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('スタッフ契約情報が見つかりません' in str(message) for message in messages))