# -*- coding: utf-8 -*-
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from apps.contract.models import ClientContract, StaffContract
from apps.client.models import Client as ClientModel
from apps.staff.models import Staff
from apps.master.models import EmploymentType, JobCategory, ContractPattern
from apps.common.constants import Constants
from apps.system.settings.models import Dropdowns
from datetime import date, timedelta

User = get_user_model()


class DailyDispatchWarningTestCase(TestCase):
    """日雇派遣警告メッセージのテストケース"""

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
        Dropdowns.objects.create(
            category='pay_unit',
            value=Constants.PAY_UNIT.HOURLY,
            name='時間給',
            disp_seq=1,
            active=True
        )
        
        # 派遣政令業務のドロップダウンを作成
        self.seirei_dropdown = Dropdowns.objects.create(
            category='jobs_seirei',
            value='01',
            name='テスト派遣政令業務',
            disp_seq=1,
            active=True
        )
        
        # 雇用形態作成（有期・無期）
        self.fixed_term_employment = EmploymentType.objects.create(
            name='有期雇用',
            display_order=1,
            is_fixed_term=True,
            is_active=True
        )
        
        self.indefinite_employment = EmploymentType.objects.create(
            name='無期雇用',
            display_order=2,
            is_fixed_term=False,
            is_active=True
        )
        
        # 職種作成（派遣政令業務あり・なし）
        self.job_category_with_seirei = JobCategory.objects.create(
            name='派遣政令業務職種',
            display_order=1,
            is_active=True,
            jobs_seirei=self.seirei_dropdown
        )
        
        self.job_category_without_seirei = JobCategory.objects.create(
            name='一般職種',
            display_order=2,
            is_active=True,
            jobs_seirei=None
        )
        
        # 契約パターン作成
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
            employment_type=self.fixed_term_employment
        )
        
        # クライアント作成
        self.client_obj = ClientModel.objects.create(
            name='テストクライアント',
            corporate_number='1234567890123',
            basic_contract_date=date.today(),
            basic_contract_date_haken=date.today()
        )
        
        # スタッフ作成（60歳未満）
        self.young_staff = Staff.objects.create(
            name_last='若手',
            name_first='太郎',
            email='young@example.com',
            employee_no='EMP001',
            hire_date=date.today(),
            birth_date=date.today() - timedelta(days=30*365),  # 30歳
            employment_type=self.fixed_term_employment
        )
        
        # スタッフ作成（60歳以上）
        self.senior_staff = Staff.objects.create(
            name_last='ベテラン',
            name_first='花子',
            email='senior@example.com',
            employee_no='EMP002',
            hire_date=date.today(),
            birth_date=date.today() - timedelta(days=65*365),  # 65歳
            employment_type=self.fixed_term_employment
        )
        
        # テストクライアント（Djangoのテストクライアント）
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    def create_client_contract(self, duration_days=25, job_category=None, contract_type=Constants.CLIENT_CONTRACT_TYPE.DISPATCH):
        """クライアント契約を作成するヘルパーメソッド"""
        start_date = date.today()
        end_date = start_date + timedelta(days=duration_days)
        
        return ClientContract.objects.create(
            client=self.client_obj,
            contract_name='テスト派遣契約',
            start_date=start_date,
            end_date=end_date,
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            client_contract_type_code=contract_type,
            contract_pattern=self.client_contract_pattern,
            job_category=job_category,
            created_by=self.user,
            updated_by=self.user
        )

    def create_staff_contract(self, staff, employment_type=None):
        """スタッフ契約を作成するヘルパーメソッド"""
        if employment_type is None:
            employment_type = staff.employment_type
            
        return StaffContract.objects.create(
            staff=staff,
            contract_name='テストスタッフ契約',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            employment_type=employment_type,
            contract_pattern=self.staff_contract_pattern,
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            pay_unit=Constants.PAY_UNIT.HOURLY,
            contract_amount=1500,
            created_by=self.user,
            updated_by=self.user
        )

    def test_daily_dispatch_warning_shown_for_young_staff_without_seirei(self):
        """60歳未満スタッフ・派遣政令業務なし・30日以内の場合に警告が表示される"""
        # 30日以内の派遣契約（派遣政令業務なし）
        client_contract = self.create_client_contract(
            duration_days=25,
            job_category=self.job_category_without_seirei
        )
        
        # 60歳未満・有期雇用のスタッフ契約
        staff_contract = self.create_staff_contract(
            staff=self.young_staff,
            employment_type=self.fixed_term_employment
        )
        
        # 割当確認画面にアクセス
        url = reverse('contract:staff_assignment_confirm')
        data = {
            'client_contract_id': client_contract.pk,
            'staff_contract_id': staff_contract.pk
        }
        
        response = self.client.post(url, data)
        
        # 警告メッセージが表示されることを確認
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '日雇派遣（30日以内または週20時間未満の派遣）となり、就業するスタッフの条件に制約があります。')
        self.assertContains(response, 'alert-danger')

    def test_daily_dispatch_warning_not_shown_for_senior_staff(self):
        """60歳以上スタッフの場合は警告が表示されない"""
        # 30日以内の派遣契約（派遣政令業務なし）
        client_contract = self.create_client_contract(
            duration_days=25,
            job_category=self.job_category_without_seirei
        )
        
        # 60歳以上・有期雇用のスタッフ契約
        staff_contract = self.create_staff_contract(
            staff=self.senior_staff,
            employment_type=self.fixed_term_employment
        )
        
        # 割当確認画面にアクセス
        url = reverse('contract:staff_assignment_confirm')
        data = {
            'client_contract_id': client_contract.pk,
            'staff_contract_id': staff_contract.pk
        }
        
        response = self.client.post(url, data)
        
        # 警告メッセージが表示されないことを確認
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '日雇派遣（30日以内または週20時間未満の派遣）となり、就業するスタッフの条件に制約があります。')

    def test_daily_dispatch_warning_not_shown_for_indefinite_employment(self):
        """無期雇用スタッフの場合は警告が表示されない"""
        # 30日以内の派遣契約（派遣政令業務なし）
        client_contract = self.create_client_contract(
            duration_days=25,
            job_category=self.job_category_without_seirei
        )
        
        # 60歳未満・無期雇用のスタッフ契約
        staff_contract = self.create_staff_contract(
            staff=self.young_staff,
            employment_type=self.indefinite_employment
        )
        
        # 割当確認画面にアクセス
        url = reverse('contract:staff_assignment_confirm')
        data = {
            'client_contract_id': client_contract.pk,
            'staff_contract_id': staff_contract.pk
        }
        
        response = self.client.post(url, data)
        
        # 警告メッセージが表示されないことを確認
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '日雇派遣（30日以内または週20時間未満の派遣）となり、就業するスタッフの条件に制約があります。')

    def test_daily_dispatch_warning_not_shown_for_seirei_job(self):
        """派遣政令業務の職種の場合は警告が表示されない"""
        # 30日以内の派遣契約（派遣政令業務あり）
        client_contract = self.create_client_contract(
            duration_days=25,
            job_category=self.job_category_with_seirei
        )
        
        # 60歳未満・有期雇用のスタッフ契約
        staff_contract = self.create_staff_contract(
            staff=self.young_staff,
            employment_type=self.fixed_term_employment
        )
        
        # 割当確認画面にアクセス
        url = reverse('contract:staff_assignment_confirm')
        data = {
            'client_contract_id': client_contract.pk,
            'staff_contract_id': staff_contract.pk
        }
        
        response = self.client.post(url, data)
        
        # 警告メッセージが表示されないことを確認
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '日雇派遣（30日以内または週20時間未満の派遣）となり、就業するスタッフの条件に制約があります。')

    def test_daily_dispatch_warning_not_shown_for_long_term_contract(self):
        """31日以上の契約の場合は警告が表示されない"""
        # 31日以上の派遣契約（派遣政令業務なし）
        client_contract = self.create_client_contract(
            duration_days=35,
            job_category=self.job_category_without_seirei
        )
        
        # 60歳未満・有期雇用のスタッフ契約
        staff_contract = self.create_staff_contract(
            staff=self.young_staff,
            employment_type=self.fixed_term_employment
        )
        
        # 割当確認画面にアクセス
        url = reverse('contract:staff_assignment_confirm')
        data = {
            'client_contract_id': client_contract.pk,
            'staff_contract_id': staff_contract.pk
        }
        
        response = self.client.post(url, data)
        
        # 警告メッセージが表示されないことを確認
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '日雇派遣（30日以内または週20時間未満の派遣）となり、就業するスタッフの条件に制約があります。')

    def test_daily_dispatch_warning_not_shown_for_non_dispatch_contract(self):
        """派遣以外の契約の場合は警告が表示されない"""
        # 業務委託契約（派遣以外の契約種別）
        client_contract = self.create_client_contract(
            duration_days=25,
            job_category=self.job_category_without_seirei,
            contract_type='10'  # 派遣以外の契約種別
        )
        
        # 60歳未満・有期雇用のスタッフ契約
        staff_contract = self.create_staff_contract(
            staff=self.young_staff,
            employment_type=self.fixed_term_employment
        )
        
        # 割当確認画面にアクセス
        url = reverse('contract:staff_assignment_confirm')
        data = {
            'client_contract_id': client_contract.pk,
            'staff_contract_id': staff_contract.pk
        }
        
        response = self.client.post(url, data)
        
        # 警告メッセージが表示されないことを確認
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '日雇派遣（30日以内または週20時間未満の派遣）となり、就業するスタッフの条件に制約があります。')

    def test_daily_dispatch_warning_from_create_view(self):
        """新規作成からの割当確認でも警告が表示される"""
        # 30日以内の派遣契約（派遣政令業務なし）
        client_contract = self.create_client_contract(
            duration_days=25,
            job_category=self.job_category_without_seirei
        )
        
        # セッションにスタッフ契約データを設定
        session = self.client.session
        session['pending_staff_contract'] = {
            'client_contract_id': client_contract.pk,
            'form_data': {
                'staff': self.young_staff.pk,
                'contract_name': 'テストスタッフ契約（新規作成）',
                'start_date': date.today().isoformat(),
                'end_date': (date.today() + timedelta(days=30)).isoformat(),
                'employment_type': self.fixed_term_employment.pk,
                'contract_pattern': self.staff_contract_pattern.pk,
                'pay_unit': Constants.PAY_UNIT.HOURLY,
                'contract_amount': '1500',
            },
            'from_view': 'client'
        }
        session.save()
        
        # 新規作成からの割当確認画面にアクセス
        url = reverse('contract:staff_assignment_confirm_from_create')
        response = self.client.get(url)
        
        # 警告メッセージが表示されることを確認
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '日雇派遣（30日以内または週20時間未満の派遣）となり、就業するスタッフの条件に制約があります。')
        self.assertContains(response, 'alert-danger')

    def test_daily_dispatch_warning_with_no_birth_date(self):
        """生年月日が未設定のスタッフの場合は60歳未満として扱われる"""
        # 生年月日なしのスタッフを作成
        staff_no_birth = Staff.objects.create(
            name_last='生年月日',
            name_first='なし',
            email='nobirth@example.com',
            employee_no='EMP003',
            hire_date=date.today(),
            birth_date=None,  # 生年月日なし
            employment_type=self.fixed_term_employment
        )
        
        # 30日以内の派遣契約（派遣政令業務なし）
        client_contract = self.create_client_contract(
            duration_days=25,
            job_category=self.job_category_without_seirei
        )
        
        # 生年月日なし・有期雇用のスタッフ契約
        staff_contract = self.create_staff_contract(
            staff=staff_no_birth,
            employment_type=self.fixed_term_employment
        )
        
        # 割当確認画面にアクセス
        url = reverse('contract:staff_assignment_confirm')
        data = {
            'client_contract_id': client_contract.pk,
            'staff_contract_id': staff_contract.pk
        }
        
        response = self.client.post(url, data)
        
        # 警告メッセージが表示されることを確認（60歳未満として扱われる）
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '日雇派遣（30日以内または週20時間未満の派遣）となり、就業するスタッフの条件に制約があります。')

    def test_daily_dispatch_warning_with_no_job_category(self):
        """職種が未設定の場合は派遣政令業務なしとして扱われる"""
        # 30日以内の派遣契約（職種なし）
        client_contract = self.create_client_contract(
            duration_days=25,
            job_category=None
        )
        
        # 60歳未満・有期雇用のスタッフ契約
        staff_contract = self.create_staff_contract(
            staff=self.young_staff,
            employment_type=self.fixed_term_employment
        )
        
        # 割当確認画面にアクセス
        url = reverse('contract:staff_assignment_confirm')
        data = {
            'client_contract_id': client_contract.pk,
            'staff_contract_id': staff_contract.pk
        }
        
        response = self.client.post(url, data)
        
        # 警告メッセージが表示されることを確認
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '日雇派遣（30日以内または週20時間未満の派遣）となり、就業するスタッフの条件に制約があります。')