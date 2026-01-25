from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import Permission
from apps.accounts.models import MyUser
from apps.staff.models import Staff, StaffContactSchedule
from apps.connect.models import ConnectStaff, MynumberRequest
from apps.profile.models import StaffProfile, StaffProfileMynumber
from apps.common.constants import Constants
from django.utils import timezone
from datetime import timedelta, date
from apps.client.models import Client as ClientModel, ClientContactSchedule, ClientDepartment
from apps.contract.models import ClientContract, StaffContract, ContractAssignment, StaffContractTeishokubi, ClientContractHaken
from apps.master.models import ContractPattern


class HomeViewTest(TestCase):
    def setUp(self):
        """
        テストデータのセットアップ
        """
        self.client = Client()
        self.user = MyUser.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='password',
            first_name='Test',
            last_name='User',
        )
        self.home_url = reverse('home:home')

    def test_home_view_redirects_for_anonymous_user(self):
        """
        未ログインユーザーはログインページにリダイレクトされることをテスト
        """
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, f'/accounts/login/?next={self.home_url}')

    def test_home_view_loads_for_logged_in_user(self):
        """
        ログイン済みユーザーでホーム画面が正常に表示されることをテスト
        """
        self.client.login(email='testuser@example.com', password='password')
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home/home.html')

    def test_home_view_context_data(self):
        """
        ホーム画面のコンテキストデータが正しく渡されていることをテスト
        """
        self.client.login(email='testuser@example.com', password='password')
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)

        # コンテキストのキーが存在するかチェック
        self.assertIn('staff_count', response.context)
        self.assertIn('approved_staff_count', response.context)
        self.assertIn('client_count', response.context)
        self.assertIn('approved_client_count', response.context)

    def test_home_view_staff_request_count_with_permission(self):
        """
        Test that staff_request_count is calculated correctly and the link is present for a user with permission.
        """
        # Add permission to user
        permission = Permission.objects.get(codename='view_staff')
        self.user.user_permissions.add(permission)
        self.client.login(email='testuser@example.com', password='password')

        # Create staff user
        staff_user = MyUser.objects.create_user(
            username='staffuser@example.com',
            email='staff@example.com',
            password='password',
        )
        # Create mynumber profile
        staff_mynumber = StaffProfileMynumber.objects.create(
            user=staff_user,
            mynumber='123456789012'
        )

        # Create Staff data
        Staff.objects.create(email='staff@example.com')

        # Create ConnectStaff data
        connect_staff = ConnectStaff.objects.create(
            corporate_number='1234567890123',
            email='staff@example.com',
            status='approved'
        )

        # Create a pending request
        MynumberRequest.objects.create(
            connect_staff=connect_staff,
            profile_mynumber=staff_mynumber,
            status='pending'
        )

        # Create another staff without request
        Staff.objects.create(email='norequest@example.com')

        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('staff_request_count', response.context)
        self.assertEqual(response.context['staff_request_count'], 1)
        self.assertContains(response, f'href="{reverse("staff:staff_list")}?has_request=true"')

    def test_home_view_staff_request_count_no_permission(self):
        """
        Test that the link is not present for a user without permission.
        """
        self.client.login(email='testuser@example.com', password='password')

        # Create staff user
        staff_user = MyUser.objects.create_user(
            username='staffuser@example.com',
            email='staff@example.com',
            password='password',
        )
        # Create mynumber profile
        staff_mynumber = StaffProfileMynumber.objects.create(
            user=staff_user,
            mynumber='123456789012'
        )

        # Create Staff data
        Staff.objects.create(email='staff@example.com')

        # Create ConnectStaff data
        connect_staff = ConnectStaff.objects.create(
            corporate_number='1234567890123',
            email='staff@example.com',
            status='approved'
        )

        # Create a pending request
        MynumberRequest.objects.create(
            connect_staff=connect_staff,
            profile_mynumber=staff_mynumber,
            status='pending'
        )

        # Create another staff without request
        Staff.objects.create(email='norequest@example.com')

        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('staff_request_count', response.context)
        self.assertEqual(response.context['staff_request_count'], 1)
        self.assertNotContains(response, f'href="{reverse("staff:staff_list")}?has_request=true"')

    def test_home_view_staff_request_count_zero(self):
        """
        Test that the link is not present when staff_request_count is 0.
        """
        self.client.login(email='testuser@example.com', password='password')
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('staff_request_count', response.context)
        self.assertEqual(response.context['staff_request_count'], 0)
        self.assertNotContains(response, f'href="{reverse("staff:staff_list")}?has_request=true"')



    def test_home_view_does_not_redirect_for_superuser_staff(self):
        """
        承認済みスタッフであってもスーパーユーザーはリダイレクトされないことをテスト
        """
        # スーパーユーザーとしてログイン
        superuser = MyUser.objects.create_superuser(
            username='super_staff@example.com',
            email='super_staff@example.com',
            password='password'
        )
        self.client.login(email='super_staff@example.com', password='password')
        
        # Staffが存在し、ConnectStaffが承認済み
        Staff.objects.create(email='super_staff@example.com', name_last='Super', name_first='Staff')
        ConnectStaff.objects.create(
            email='super_staff@example.com',
            corporate_number='2222222222222',
            status=Constants.CONNECT_STATUS.APPROVED
        )
        
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200) # リダイレクトされずホーム画面が表示される

    def test_home_view_does_not_redirect_when_staff_model_missing(self):
        """
        ConnectStaffが承認済みでもStaffモデルが存在しない場合はリダイレクトされないことをテスト（無限ループ防止）
        """
        # 一般ユーザーとしてログイン
        user = MyUser.objects.create_user(
            username='missing_staff@example.com',
            email='missing_staff@example.com',
            password='password'
        )
        self.client.login(email='missing_staff@example.com', password='password')
        
        # ConnectStaffは承認済みだが、Staffが存在しない
        ConnectStaff.objects.create(
            email='missing_staff@example.com',
            corporate_number='3333333333333',
            status=Constants.CONNECT_STATUS.APPROVED
        )
        # Staff.objects.create(...) はしない
        
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200) # リダイレクトされない


class HomeScheduleSummaryTest(TestCase):
    def setUp(self):
        self.client_http = Client()
        self.user = MyUser.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='password'
        )
        self.client_http.login(email='testuser@example.com', password='password')
        self.home_url = reverse('home:home')

        # Create test data
        today = timezone.localdate()
        yesterday = today - timedelta(days=1)

        staff = Staff.objects.create(name_last='Staff', name_first='Test')
        client_obj = ClientModel.objects.create(name='Client Test')

        # Create schedules
        StaffContactSchedule.objects.create(staff=staff, contact_date=today, content='today staff')
        StaffContactSchedule.objects.create(staff=staff, contact_date=yesterday, content='yesterday staff 1')
        StaffContactSchedule.objects.create(staff=staff, contact_date=yesterday, content='yesterday staff 2')

        ClientContactSchedule.objects.create(client=client_obj, contact_date=today, content='today client 1')
        ClientContactSchedule.objects.create(client=client_obj, contact_date=today, content='today client 2')
        ClientContactSchedule.objects.create(client=client_obj, contact_date=today, content='today client 3')
        ClientContactSchedule.objects.create(client=client_obj, contact_date=yesterday, content='yesterday client')

    def test_schedule_summary_no_permission(self):
        """
        Test that the schedule summary is not visible without permissions.
        """
        response = self.client_http.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '業務サマリ')
        self.assertEqual(response.context['staff_schedules_today'], 0)
        self.assertEqual(response.context['client_schedules_today'], 0)

    def test_schedule_summary_with_staff_permission(self):
        """
        Test that the staff schedule summary is visible with staff permission.
        """
        permission = Permission.objects.get(codename='view_staffcontactschedule')
        self.user.user_permissions.add(permission)

        response = self.client_http.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '業務サマリ')
        self.assertContains(response, 'スタッフ連絡予定')
        self.assertNotContains(response, 'クライアント連絡予定')

        self.assertEqual(response.context['staff_schedules_today'], 1)
        self.assertEqual(response.context['staff_schedules_yesterday'], 2)
        self.assertEqual(response.context['client_schedules_today'], 0)
        self.assertEqual(response.context['client_schedules_yesterday'], 0)

    def test_schedule_summary_with_client_permission(self):
        """
        Test that the client schedule summary is visible with client permission.
        """
        permission = Permission.objects.get(codename='view_clientcontactschedule')
        self.user.user_permissions.add(permission)

        response = self.client_http.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '業務サマリ')
        self.assertNotContains(response, 'スタッフ連絡予定')
        self.assertContains(response, 'クライアント連絡予定')

        self.assertEqual(response.context['staff_schedules_today'], 0)
        self.assertEqual(response.context['staff_schedules_yesterday'], 0)
        self.assertEqual(response.context['client_schedules_today'], 3)
        self.assertEqual(response.context['client_schedules_yesterday'], 1)


class HomeTeishokubiSummaryTest(TestCase):
    def setUp(self):
        self.client_http = Client()
        self.user = MyUser.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='password'
        )
        self.client_http.login(email='testuser@example.com', password='password')
        self.home_url = reverse('home:home')
        permission = Permission.objects.get(codename='view_clientcontract')
        self.user.user_permissions.add(permission)

        today = timezone.localdate()

        # Common objects
        self.staff1 = Staff.objects.create(email='staff1@example.com', name_last='Staff', name_first='One')
        self.client_model = ClientModel.objects.create(name='Test Client', corporate_number='111')
        self.org_unit = ClientDepartment.objects.create(client=self.client_model, name='Org Unit 1')

        # Dummy ContractPattern
        self.client_pattern = ContractPattern.objects.create(name="Client Pattern", domain=Constants.DOMAIN.CLIENT)
        self.staff_pattern = ContractPattern.objects.create(name="Staff Pattern", domain=Constants.DOMAIN.STAFF)

        # Scenario 1: Expiring and Active
        client_contract1 = ClientContract.objects.create(
            client=self.client_model,
            contract_name="Contract 1",
            start_date=today,
            end_date=today + timedelta(days=90),
            client_contract_type_code=Constants.CLIENT_CONTRACT_TYPE.DISPATCH,
            contract_pattern=self.client_pattern,
        )
        ClientContractHaken.objects.create(client_contract=client_contract1, haken_unit=self.org_unit)
        staff_contract1 = StaffContract.objects.create(
            staff=self.staff1,
            contract_name="Staff Contract 1",
            start_date=today,
            end_date=today + timedelta(days=90),
            contract_pattern=self.staff_pattern,
        )
        ContractAssignment.objects.create(
            client_contract=client_contract1,
            staff_contract=staff_contract1,
            staff_email=self.staff1.email,
            client_corporate_number=self.client_model.corporate_number,
            assignment_end_date=today + timedelta(days=90)
        )
        StaffContractTeishokubi.objects.create(
            staff_email=self.staff1.email,
            client_corporate_number=self.client_model.corporate_number,
            organization_name=self.org_unit.name,
            dispatch_start_date=today,
            conflict_date=today + timedelta(days=30)
        )

        # Scenario 2: Expiring but Inactive
        self.staff2 = Staff.objects.create(email='staff2@example.com', name_last='Staff', name_first='Two')
        client_contract2 = ClientContract.objects.create(
            client=self.client_model,
            contract_name="Contract 2",
            start_date=today - timedelta(days=90),
            end_date=today - timedelta(days=1),
            client_contract_type_code=Constants.CLIENT_CONTRACT_TYPE.DISPATCH,
            contract_pattern=self.client_pattern,
        )
        ClientContractHaken.objects.create(client_contract=client_contract2, haken_unit=self.org_unit)
        staff_contract2 = StaffContract.objects.create(
            staff=self.staff2,
            contract_name="Staff Contract 2",
            start_date=today - timedelta(days=90),
            end_date=today - timedelta(days=1),
            contract_pattern=self.staff_pattern,
        )
        ContractAssignment.objects.create(
            client_contract=client_contract2,
            staff_contract=staff_contract2,
            staff_email=self.staff2.email,
            client_corporate_number=self.client_model.corporate_number,
            assignment_end_date=today - timedelta(days=1)
        )
        StaffContractTeishokubi.objects.create(
            staff_email=self.staff2.email,
            client_corporate_number=self.client_model.corporate_number,
            organization_name=self.org_unit.name,
            dispatch_start_date=today - timedelta(days=90),
            conflict_date=today + timedelta(days=40)
        )

        # Scenario 3: Active but Not Expiring
        self.staff3 = Staff.objects.create(email='staff3@example.com', name_last='Staff', name_first='Three')
        client_contract3 = ClientContract.objects.create(
            client=self.client_model,
            contract_name="Contract 3",
            start_date=today,
            end_date=today + timedelta(days=120),
            client_contract_type_code=Constants.CLIENT_CONTRACT_TYPE.DISPATCH,
            contract_pattern=self.client_pattern,
        )
        ClientContractHaken.objects.create(client_contract=client_contract3, haken_unit=self.org_unit)
        staff_contract3 = StaffContract.objects.create(
            staff=self.staff3,
            contract_name="Staff Contract 3",
            start_date=today,
            end_date=today + timedelta(days=120),
            contract_pattern=self.staff_pattern,
        )
        ContractAssignment.objects.create(
            client_contract=client_contract3,
            staff_contract=staff_contract3,
            staff_email=self.staff3.email,
            client_corporate_number=self.client_model.corporate_number,
            assignment_end_date=today + timedelta(days=120)
        )
        StaffContractTeishokubi.objects.create(
            staff_email=self.staff3.email,
            client_corporate_number=self.client_model.corporate_number,
            organization_name=self.org_unit.name,
            dispatch_start_date=today,
            conflict_date=today + timedelta(days=90)
        )

    def test_personal_teishokubi_deadline_count(self):
        """
        個人抵触日期限の件数が正しく計算されることをテスト
        """
        response = self.client_http.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('personal_teishokubi_deadline_count', response.context)
        self.assertEqual(response.context['personal_teishokubi_deadline_count'], 1)
