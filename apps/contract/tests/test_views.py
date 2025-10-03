from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.messages import get_messages
from ..models import ClientContract, StaffContract, ClientContractHaken
from apps.client.models import Client as TestClient, ClientUser, ClientDepartment
from apps.staff.models import Staff
from apps.master.models import ContractPattern
import datetime

User = get_user_model()

class ContractViewTest(TestCase):
    """契約ビューのテスト"""

    def setUp(self):
        """テストデータの準備"""
        from django.conf import settings
        settings.DROPDOWN_CLIENT_CONTRACT_TYPE = []
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        from apps.company.models import Company

        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # 契約関連の権限を追加
        all_permissions = []
        content_type_client = ContentType.objects.get_for_model(ClientContract)
        client_permissions = Permission.objects.filter(content_type=content_type_client)
        all_permissions.extend(client_permissions)

        content_type_haken = ContentType.objects.get_for_model(ClientContractHaken)
        haken_permissions = Permission.objects.filter(content_type=content_type_haken)
        all_permissions.extend(haken_permissions)

        content_type_staff = ContentType.objects.get_for_model(StaffContract)
        staff_permissions = Permission.objects.filter(content_type=content_type_staff)
        all_permissions.extend(staff_permissions)

        self.user.user_permissions.set(all_permissions)

        self.company = Company.objects.create(name='Test Company', corporate_number='1112223334445')

        self.test_client = TestClient.objects.create(
            name='Test Client',
            corporate_number='6000000000001',
            name_furigana='テストクライアント',
            address='Test Address'
        )
        self.contract_pattern = ContractPattern.objects.create(name='Test Pattern', domain='10', contract_type_code='20')
        self.client_contract = ClientContract.objects.create(
            client=self.test_client,
            contract_name='Test Contract',
            start_date=datetime.date.today(),
            end_date=datetime.date.today() + datetime.timedelta(days=30),
            contract_pattern=self.contract_pattern,
            client_contract_type_code='20',
            corporate_number=self.company.corporate_number
        )
        self.non_haken_contract_pattern = ContractPattern.objects.create(name='Non-Haken Pattern', domain='10', contract_type_code='10')
        self.non_haken_contract = ClientContract.objects.create(
            client=self.test_client,
            contract_name='Test Non-Haken Contract',
            start_date=datetime.date.today(),
            end_date=datetime.date.today() + datetime.timedelta(days=30),
            contract_pattern=self.non_haken_contract_pattern,
            client_contract_type_code='10',
            contract_status=ClientContract.ContractStatus.APPROVED,
            corporate_number=self.company.corporate_number
        )

        self.staff = Staff.objects.create(
            name_last='Test',
            name_first='Staff',
            employee_no='S001',
            hire_date=datetime.date(2024, 1, 1),
        )
        self.staff_pattern = ContractPattern.objects.create(name='Staff Pattern', domain='1', is_active=True)

        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    def test_staff_contract_create_post_invalid_retains_staff_display(self):
        """POSTリクエストでフォームが無効な場合に、スタッフの表示が維持されるかテスト"""
        # 無効なデータを作成（契約名が空）
        invalid_data = {
            'staff': self.staff.pk,
            'contract_name': '', # Invalid
            'start_date': datetime.date(2024, 4, 1),
            'end_date': datetime.date(2024, 12, 31),
            'contract_pattern': self.staff_pattern.pk,
        }

        response = self.client.post(reverse('contract:staff_contract_create'), data=invalid_data)

        # フォームが再表示されることを確認
        self.assertEqual(response.status_code, 200)

        # スタッフ名がHTMLに含まれていることを確認
        expected_text = f'{self.staff.name_last} {self.staff.name_first}'
        self.assertContains(response, expected_text)

    def test_client_contract_list_view(self):
        """クライアント契約一覧ビューのテスト"""
        response = self.client.get(reverse('contract:client_contract_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'クライアント契約一覧')

    def test_staff_contract_list_view(self):
        """スタッフ契約一覧ビューのテスト"""
        response = self.client.get(reverse('contract:staff_contract_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'スタッフ契約一覧')

    def test_client_contract_pdf_view(self):
        """クライアント契約PDFビューのテスト"""
        response = self.client.get(reverse('contract:client_contract_pdf', kwargs={'pk': self.client_contract.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response['Content-Disposition'].startswith(f'attachment; filename="client_contract_{self.client_contract.pk}_'))

    def test_staff_contract_pdf_view(self):
        """スタッフ契約PDFビューのテスト"""
        from apps.staff.models import Staff
        staff = Staff.objects.create(name_last='Test', name_first='Staff')
        staff_pattern = ContractPattern.objects.create(name='Staff Pattern', domain='1')
        staff_contract = StaffContract.objects.create(
            staff=staff,
            contract_name='Test Staff Contract',
            start_date=datetime.date.today(),
            contract_pattern=staff_pattern
        )
        response = self.client.get(reverse('contract:staff_contract_pdf', kwargs={'pk': staff_contract.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response['Content-Disposition'].startswith(f'attachment; filename="staff_contract_{staff_contract.pk}_'))

    def test_staff_contract_pdf_approved_to_issued(self):
        """承認済みのスタッフ契約書を印刷すると発行済になるテスト"""
        from apps.staff.models import Staff
        from ..models import StaffContractPrint
        staff = Staff.objects.create(name_last='Test', name_first='Staff')
        staff_pattern = ContractPattern.objects.create(name='Staff Pattern', domain='1')
        staff_contract = StaffContract.objects.create(
            staff=staff,
            contract_name='Test Staff Contract',
            start_date=datetime.date.today(),
            contract_status=StaffContract.ContractStatus.APPROVED,
            contract_pattern=staff_pattern
        )
        self.assertEqual(StaffContractPrint.objects.count(), 0)
        response = self.client.get(reverse('contract:staff_contract_pdf', kwargs={'pk': staff_contract.pk}))
        self.assertEqual(response.status_code, 200)

        # ステータスが発行済に変わっていることを確認
        staff_contract.refresh_from_db()
        self.assertEqual(staff_contract.contract_status, StaffContract.ContractStatus.ISSUED)

        # 発行履歴が作成されていることを確認
        self.assertEqual(StaffContractPrint.objects.count(), 1)
        print_history = StaffContractPrint.objects.first()
        self.assertEqual(print_history.staff_contract, staff_contract)
        self.assertEqual(print_history.printed_by, self.user)

    def test_client_contract_pdf_approved_to_issued(self):
        """承認済みのクライアント契約書を印刷すると発行済になるテスト"""
        from ..models import ClientContractPrint
        self.client_contract.contract_status = ClientContract.ContractStatus.APPROVED
        self.client_contract.save()

        self.assertEqual(ClientContractPrint.objects.count(), 0)
        response = self.client.get(reverse('contract:client_contract_pdf', kwargs={'pk': self.client_contract.pk}))
        self.assertEqual(response.status_code, 200)

        # ステータスが発行済に変わっていることを確認
        self.client_contract.refresh_from_db()
        self.assertEqual(self.client_contract.contract_status, ClientContract.ContractStatus.ISSUED)

        # 発行履歴が作成されていることを確認
        self.assertEqual(ClientContractPrint.objects.count(), 1)
        print_history = ClientContractPrint.objects.first()
        self.assertEqual(print_history.client_contract, self.client_contract)
        self.assertEqual(print_history.printed_by, self.user)

    def test_download_pdf_views(self):
        """PDFダウンロードビューのテスト"""
        from ..models import ClientContractPrint
        import os
        from django.conf import settings

        # クライアント契約のテスト
        self.client_contract.contract_status = ClientContract.ContractStatus.APPROVED
        self.client_contract.save()
        self.client.get(reverse('contract:client_contract_pdf', kwargs={'pk': self.client_contract.pk}))
        print_history = ClientContractPrint.objects.first()
        self.assertIsNotNone(print_history)

        response = self.client.get(reverse('contract:download_client_contract_pdf', kwargs={'pk': print_history.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response['Content-Disposition'].startswith(f'attachment; filename="'))

    def test_client_contract_copy_view(self):
        """クライアント契約のコピー機能が正しく動作することをテスト"""
        from apps.company.models import CompanyUser
        # 1. 派遣情報を含む完全な契約データを作成
        self.client_contract.contract_status = ClientContract.ContractStatus.APPROVED
        self.client_contract.contract_number = 'C-001'
        self.client_contract.contract_amount = 500000
        self.client_contract.save()

        haken_office = ClientDepartment.objects.create(client=self.test_client, name='Copy Test Office', is_haken_office=True)
        haken_unit = ClientDepartment.objects.create(client=self.test_client, name='Copy Test Unit', is_haken_unit=True)
        commander = ClientUser.objects.create(client=self.test_client, name_last='CopyCommander', name_first='Test')
        company_user = CompanyUser.objects.create(name_last='CopyCompany', name_first='User')

        original_haken_info = ClientContractHaken.objects.create(
            client_contract=self.client_contract,
            haken_office=haken_office,
            haken_unit=haken_unit,
            commander=commander,
            complaint_officer_client=commander,
            responsible_person_client=commander,
            complaint_officer_company=company_user,
            responsible_person_company=company_user,
            limit_by_agreement='0',
            limit_indefinite_or_senior='0',
            business_content='Original business content'
        )

        # 2. コピー用URLにGETリクエストを送信
        copy_url = reverse('contract:client_contract_create') + f'?copy_from={self.client_contract.pk}'
        response = self.client.get(copy_url)

        # 3. レスポンスとフォームの初期データを確認
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'contract/client_contract_form.html')
        form = response.context['form']
        haken_form = response.context['haken_form']

        self.assertEqual(form.initial['contract_name'], f"{self.client_contract.contract_name}のコピー")
        self.assertEqual(form.initial['client'], self.client_contract.client.id)
        self.assertEqual(form.initial['contract_amount'], 500000)
        self.assertEqual(haken_form.initial['haken_office'], haken_office.id)
        self.assertEqual(haken_form.initial['commander'], commander.id)
        self.assertEqual(haken_form.initial['business_content'], 'Original business content')

        # 4. POSTリクエストでフォームを送信してコピーを作成
        post_data = form.initial.copy()
        post_data.update(haken_form.initial)

        # `model_to_dict`がForeignKeyをIDに変換するので、ChoiceFieldも手動でpkに変換
        post_data['contract_pattern'] = self.contract_pattern.pk
        post_data['complaint_officer_company'] = company_user.pk
        post_data['responsible_person_company'] = company_user.pk

        # Noneの値を空文字列に変換して、TypeErrorを回避
        for key, value in post_data.items():
            if value is None:
                post_data[key] = ''

        initial_client_contract_count = ClientContract.objects.count()
        initial_haken_count = ClientContractHaken.objects.count()

        response = self.client.post(reverse('contract:client_contract_create'), data=post_data)

        # リダイレクトをチェック
        if response.status_code != 302:
            form_errors = response.context.get('form').errors if response.context and response.context.get('form') else {}
            haken_form_errors = response.context.get('haken_form').errors if response.context and response.context.get('haken_form') else {}
            self.fail(f"POST failed with status {response.status_code}. Form errors: {form_errors}, Haken form errors: {haken_form_errors}")
        self.assertEqual(response.status_code, 302)

        # 5. 新しい契約が作成されたことを確認
        self.assertEqual(ClientContract.objects.count(), initial_client_contract_count + 1)
        self.assertEqual(ClientContractHaken.objects.count(), initial_haken_count + 1)

        new_contract = ClientContract.objects.latest('id')

        # 6. 新しい契約のステータスと契約番号を確認
        self.assertEqual(new_contract.contract_status, ClientContract.ContractStatus.DRAFT)
        self.assertIsNone(new_contract.contract_number)
        self.assertNotEqual(new_contract.pk, self.client_contract.pk)

        # 7. 新しい契約の他のフィールドを確認
        self.assertEqual(new_contract.contract_name, f"{self.client_contract.contract_name}のコピー")
        self.assertEqual(new_contract.client, self.client_contract.client)
        self.assertEqual(new_contract.contract_amount, 500000)

        # 8. 新しい派遣情報が作成されたことを確認
        self.assertTrue(hasattr(new_contract, 'haken_info'))
        self.assertNotEqual(new_contract.haken_info.pk, original_haken_info.pk)
        self.assertEqual(new_contract.haken_info.haken_office, haken_office)
        self.assertEqual(new_contract.haken_info.business_content, 'Original business content')

    def test_issue_clash_day_notification_for_non_haken_contract(self):
        """
        派遣契約でない契約に対して抵触日通知書を発行しようとするとエラーになることをテスト
        """
        url = reverse('contract:issue_clash_day_notification', kwargs={'pk': self.non_haken_contract.pk})
        response = self.client.post(url)

        # 詳細ページにリダイレクトされることを確認
        self.assertRedirects(response, reverse('contract:client_contract_detail', kwargs={'pk': self.non_haken_contract.pk}))

        # エラーメッセージが表示されることを確認
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'この契約の抵触日通知書は発行できません。')

    def test_draft_clash_day_notification_for_non_haken_contract(self):
        """
        派遣契約でない契約に対してドラフトの抵触日通知書を発行しようとするとエラーになることをテスト
        """
        url = reverse('contract:client_contract_draft_clash_day_notification', kwargs={'pk': self.non_haken_contract.pk})
        response = self.client.get(url)

        # 詳細ページにリダイレクトされることを確認
        self.assertRedirects(response, reverse('contract:client_contract_detail', kwargs={'pk': self.non_haken_contract.pk}))

        # エラーメッセージが表示されることを確認
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'この契約の抵触日通知書は発行できません。')



    def test_client_contract_create_haken_successful_post(self):
        """派遣契約の新規作成が正常に成功することを確認"""
        from apps.company.models import CompanyUser
        haken_office = ClientDepartment.objects.create(client=self.test_client, name='Test Office', is_haken_office=True)
        haken_unit = ClientDepartment.objects.create(client=self.test_client, name='Test Unit', is_haken_unit=True)
        commander = ClientUser.objects.create(client=self.test_client, name_last='Commander', name_first='Test')
        company_user = CompanyUser.objects.create(name_last='Company', name_first='User')

        create_url = reverse('contract:client_contract_create')

        post_data = {
            'client': self.test_client.pk,
            'client_contract_type_code': '20',
            'contract_name': 'New Haken Contract',
            'contract_pattern': self.contract_pattern.pk,
            'start_date': datetime.date.today(),
            'end_date': datetime.date.today() + datetime.timedelta(days=30),
            'contract_status': ClientContract.ContractStatus.DRAFT,
            # Haken form data
            'haken_office': haken_office.pk,
            'haken_unit': haken_unit.pk,
            'commander': commander.pk,
            'complaint_officer_client': commander.pk,
            'responsible_person_client': commander.pk,
            'complaint_officer_company': company_user.pk,
            'responsible_person_company': company_user.pk,
            'limit_by_agreement': '0',
            'limit_indefinite_or_senior': '0',
        }

        response = self.client.post(create_url, data=post_data)

        if response.status_code != 302:
            form_errors = response.context.get('form', {}).errors
            haken_form_errors = response.context.get('haken_form', {}).errors
            self.fail(f"POST failed with status {response.status_code}. Form errors: {form_errors}, Haken form errors: {haken_form_errors}")

        self.assertEqual(ClientContract.objects.count(), 3)
        self.assertEqual(ClientContractHaken.objects.count(), 1)
        new_contract = ClientContract.objects.latest('id')
        self.assertEqual(new_contract.contract_name, 'New Haken Contract')
        self.assertTrue(hasattr(new_contract, 'haken_info'))
        self.assertEqual(new_contract.haken_info.commander, commander)
        self.assertEqual(new_contract.haken_info.haken_office, haken_office)
        self.assertEqual(new_contract.haken_info.haken_unit, haken_unit)

    def test_client_contract_update_haken_successful_post(self):
        """派遣契約の更新が正常に成功することを確認"""
        from apps.company.models import CompanyUser
        # Haken Info と関連オブジェクトを作成
        haken_office = ClientDepartment.objects.create(client=self.test_client, name='Test Office', is_haken_office=True)
        haken_unit = ClientDepartment.objects.create(client=self.test_client, name='Test Unit', is_haken_unit=True)
        commander = ClientUser.objects.create(client=self.test_client, name_last='Commander', name_first='Test')
        complaint_officer = ClientUser.objects.create(client=self.test_client, name_last='Complaint', name_first='Officer')
        responsible_person = ClientUser.objects.create(client=self.test_client, name_last='Responsible', name_first='Person')

        company_user = CompanyUser.objects.create(name_last='Company', name_first='User')

        haken_info = ClientContractHaken.objects.create(
            client_contract=self.client_contract,
            haken_office=haken_office,
            haken_unit=haken_unit,
            commander=commander,
            complaint_officer_client=complaint_officer,
            responsible_person_client=responsible_person,
            complaint_officer_company=company_user,
            responsible_person_company=company_user,
            limit_by_agreement='0',
            limit_indefinite_or_senior='0'
        )

        # 更新用の新しい担当者・部署
        new_haken_office = ClientDepartment.objects.create(client=self.test_client, name='New Test Office', is_haken_office=True)
        new_haken_unit = ClientDepartment.objects.create(client=self.test_client, name='New Test Unit', is_haken_unit=True)
        new_commander = ClientUser.objects.create(client=self.test_client, name_last='NewCommander', name_first='Test')

        update_url = reverse('contract:client_contract_update', kwargs={'pk': self.client_contract.pk})

        post_data = {
            'client': self.test_client.pk,
            'client_contract_type_code': '20',
            'contract_name': 'Updated Haken Contract',
            'contract_pattern': self.contract_pattern.pk,
            'start_date': self.client_contract.start_date,
            'end_date': self.client_contract.end_date,
            'contract_status': ClientContract.ContractStatus.DRAFT,
            # Haken form data
            'haken_office': new_haken_office.pk,
            'haken_unit': new_haken_unit.pk,
            'commander': new_commander.pk,
            'complaint_officer_client': complaint_officer.pk,
            'responsible_person_client': responsible_person.pk,
            'complaint_officer_company': company_user.pk,
            'responsible_person_company': company_user.pk,
            'limit_by_agreement': '1',
            'limit_indefinite_or_senior': '1',
        }

        response = self.client.post(update_url, data=post_data)

        # 最初にステータスコードをチェックし、失敗した場合のみエラー詳細を出力
        if response.status_code != 302:
            form_errors = response.context.get('form', {}).errors
            haken_form_errors = response.context.get('haken_form', {}).errors
            self.fail(f"POST failed with status {response.status_code}. Form errors: {form_errors}, Haken form errors: {haken_form_errors}")

        self.assertRedirects(response, reverse('contract:client_contract_detail', kwargs={'pk': self.client_contract.pk}))

        # 契約が更新されていることを確認
        updated_contract = ClientContract.objects.get(pk=self.client_contract.pk)
        self.assertEqual(updated_contract.contract_name, 'Updated Haken Contract')

        # 派遣情報が更新されていることを確認
        haken_info.refresh_from_db()
        self.assertEqual(haken_info.haken_office, new_haken_office)
        self.assertEqual(haken_info.haken_unit, new_haken_unit)
        self.assertEqual(haken_info.commander, new_commander)
        self.assertEqual(haken_info.limit_by_agreement, '1')

    def test_client_contract_update_preserves_contract_type(self):
        """契約更新時に契約種別が維持されることをテスト"""
        from apps.system.settings.models import Dropdowns
        from apps.master.models import ContractPattern

        # 契約種別を作成
        contract_type = Dropdowns.objects.create(
            category='client_contract_type',
            name='テスト契約種別',
            value='TS',
            disp_seq=1,
        )

        self.contract_pattern.contract_type_code = contract_type.value
        self.contract_pattern.save()

        self.test_client.basic_contract_date = '2025-01-01'
        self.test_client.save()

        # クライアント契約を作成
        contract = ClientContract.objects.create(
            client=self.test_client,
            contract_name='Initial Contract',
            client_contract_type_code=contract_type.value,
            contract_pattern=self.contract_pattern,
            start_date='2025-01-01',
            end_date='2025-12-31',
        )

        self.client.login(username='testuser', password='testpass123')

        update_url = reverse('contract:client_contract_update', kwargs={'pk': contract.pk})

        post_data = {
            'client': self.test_client.pk,
            'client_contract_type_code': contract_type.value,
            'contract_name': 'Updated Contract Name',
            'job_category': '',
            'contract_pattern': self.contract_pattern.pk,
            'contract_number': '',
            'contract_status': ClientContract.ContractStatus.DRAFT,
            'start_date': '2025-01-01',
            'end_date': '2025-12-31',
            'contract_amount': '',
            'payment_site': '',
            'description': '',
            'notes': '',
        }

        response = self.client.post(update_url, data=post_data)

        # リダイレクトを検証
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('contract:client_contract_detail', kwargs={'pk': contract.pk}))

        # 契約が更新されていることを確認
        updated_contract = ClientContract.objects.get(pk=contract.pk)
        self.assertEqual(updated_contract.contract_name, 'Updated Contract Name')

        # 契約種別が維持されていることを確認
        self.assertEqual(updated_contract.client_contract_type_code, contract_type.value)

        # staff契約のテスト
        from apps.staff.models import Staff
        from ..models import StaffContractPrint
        staff = Staff.objects.create(name_last='Test', name_first='Staff')
        staff_pattern = ContractPattern.objects.create(name='Staff Pattern', domain='1')
        staff_contract = StaffContract.objects.create(
            staff=staff,
            contract_name='Test Staff Contract',
            start_date=datetime.date.today(),
            contract_status=StaffContract.ContractStatus.APPROVED,
            contract_pattern=staff_pattern
        )
        self.client.get(reverse('contract:staff_contract_pdf', kwargs={'pk': staff_contract.pk}))
        print_history = StaffContractPrint.objects.filter(staff_contract=staff_contract).first()
        self.assertIsNotNone(print_history)

        response = self.client.get(reverse('contract:download_staff_contract_pdf', kwargs={'pk': print_history.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response['Content-Disposition'].startswith(f'attachment; filename="'))