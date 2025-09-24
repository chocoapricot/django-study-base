from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from ..models import ClientContract, StaffContract
from apps.client.models import Client as TestClient
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

        content_type_staff = ContentType.objects.get_for_model(StaffContract)
        staff_permissions = Permission.objects.filter(content_type=content_type_staff)
        all_permissions.extend(staff_permissions)

        self.user.user_permissions.set(all_permissions)

        self.test_client = TestClient.objects.create(
            name='Test Client',
            corporate_number='6000000000001',
            name_furigana='テストクライアント',
            address='Test Address'
        )
        self.contract_pattern = ContractPattern.objects.create(name='Test Pattern', domain='10')
        self.client_contract = ClientContract.objects.create(
            client=self.test_client,
            contract_name='Test Contract',
            start_date=datetime.date.today(),
            contract_pattern=self.contract_pattern
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

    def test_client_contract_haken_form_initial_state(self):
        """派遣契約作成時、派遣先担当者フィールドが空であることを確認"""
        from apps.client.models import ClientUser
        ClientUser.objects.create(client=self.test_client, name_last='ShouldNot', name_first='Appear')

        # 派遣契約(type_code=20)の作成画面URL
        url = reverse('contract:client_contract_create') + '?client_contract_type_code=20'

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # haken_formがコンテキストに含まれていることを確認
        self.assertIn('haken_form', response.context)
        haken_form = response.context['haken_form']

        # 各フィールドのquerysetが空であることを確認
        self.assertEqual(haken_form.fields['commander'].queryset.count(), 0)
        self.assertEqual(haken_form.fields['complaint_officer_client'].queryset.count(), 0)
        self.assertEqual(haken_form.fields['responsible_person_client'].queryset.count(), 0)

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
