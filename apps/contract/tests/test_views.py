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

        from apps.system.settings.models import Dropdowns
        self.pay_unit_daily = Dropdowns.objects.create(category='pay_unit', value='20', name='日給', active=True)

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

    def test_staff_contract_list_view_with_pay_unit(self):
        """スタッフ契約一覧画面で支払単位が表示されるかテスト"""
        staff_contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name='Test Staff Contract with Pay Unit',
            start_date=datetime.date.today(),
            contract_pattern=self.staff_pattern,
            contract_amount=20000,
            pay_unit=self.pay_unit_daily.value
        )
        response = self.client.get(reverse('contract:staff_contract_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '日給&nbsp;20,000円')

    def test_staff_contract_detail_view_with_pay_unit(self):
        """スタッフ契約詳細画面で支払単位が表示されるかテスト"""
        staff_contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name='Test Staff Contract with Pay Unit',
            start_date=datetime.date.today(),
            contract_pattern=self.staff_pattern,
            contract_amount=20000,
            pay_unit=self.pay_unit_daily.value
        )
        response = self.client.get(reverse('contract:staff_contract_detail', kwargs={'pk': staff_contract.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '日給&nbsp;20,000円')

    def test_unapprove_resets_notification_status_and_info_on_ui(self):
        """承認解除時に通知書ステータスと発行者情報がUI上リセットされるかテスト"""
        from ..models import ClientContractPrint
        from django.utils import timezone

        # 1. ユーザーに姓名を設定
        self.user.name_last = '山田'
        self.user.name_first = '太郎'
        self.user.save()
        user_full_name = self.user.get_full_name_japanese()

        # 2. 契約を承認済みにする
        self.client_contract.contract_status = ClientContract.ContractStatus.APPROVED
        self.client_contract.save()

        # 3. 抵触日通知書と派遣通知書を発行する
        ClientContractPrint.objects.create(
            client_contract=self.client_contract,
            print_type=ClientContractPrint.PrintType.CLASH_DAY_NOTIFICATION,
            printed_by=self.user,
            printed_at=timezone.now()
        )
        ClientContractPrint.objects.create(
            client_contract=self.client_contract,
            print_type=ClientContractPrint.PrintType.DISPATCH_NOTIFICATION,
            printed_by=self.user,
            printed_at=timezone.now()
        )
        self.assertEqual(ClientContractPrint.objects.filter(client_contract=self.client_contract).count(), 2)

        # 4. 詳細ページでスイッチがチェックされ、発行者情報が表示されていることを確認
        detail_url = reverse('contract:client_contract_detail', kwargs={'pk': self.client_contract.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        # スイッチがチェックされているか
        self.assertRegex(response.content.decode('utf-8'), r'<input class="form-check-input" type="checkbox" id="issueClashDayNotificationSwitch"[^>]*checked')
        self.assertRegex(response.content.decode('utf-8'), r'<input class="form-check-input" type="checkbox" id="issueDispatchNotificationSwitch"[^>]*checked')
        # 発行者情報が表示されているか
        self.assertContains(response, user_full_name)

        # 5. 契約の承認を解除する
        approve_url = reverse('contract:client_contract_approve', kwargs={'pk': self.client_contract.pk})
        response = self.client.post(approve_url, data={}) # is_approved がないので解除になる
        self.assertEqual(response.status_code, 302) # 詳細ページへリダイレクト
        self.client_contract.refresh_from_db()
        self.assertEqual(self.client_contract.contract_status, ClientContract.ContractStatus.DRAFT)

        # 6. 発行履歴レコードが削除されていないことを確認
        self.assertEqual(ClientContractPrint.objects.filter(client_contract=self.client_contract).count(), 2)

        # 7. 詳細ページでスイッチがチェックされておらず、発行者情報も表示されていないことを確認
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        # スイッチがチェックされていないか
        self.assertNotRegex(response.content.decode('utf-8'), r'<input class="form-check-input" type="checkbox" id="issueClashDayNotificationSwitch"[^>]*checked')
        self.assertNotRegex(response.content.decode('utf-8'), r'<input class="form-check-input" type="checkbox" id="issueDispatchNotificationSwitch"[^>]*checked')

        # 承認解除により発行者情報が表示されなくなることを確認する。
        # 変更履歴にユーザー名が表示される可能性があるため、より具体的な文字列で検証する。
        self.assertNotContains(response, f'　{user_full_name}）')


class ClientContractConfirmListViewTest(TestCase):
    """クライアント契約確認一覧ビューのテスト"""

    def setUp(self):
        """テストデータの準備"""
        from apps.company.models import Company
        from apps.connect.models import ConnectClient
        from ..models import ClientContractPrint

        # 会社を作成
        self.company = Company.objects.create(name='Test Company', corporate_number='1234567890123')

        # クライアントとクライアントユーザーを作成
        self.test_client = TestClient.objects.create(name='Test Client Corp', corporate_number='9876543210987')
        self.client_user = User.objects.create_user(
            username='clientuser',
            email='client@example.com',
            password='testpass123'
        )
        self.client_user_profile = ClientUser.objects.create(
            client=self.test_client,
            email=self.client_user.email,
            name_last='Client',
            name_first='User'
        )

        # 会社とクライアントユーザーを接続
        ConnectClient.objects.create(
            email=self.client_user.email,
            corporate_number=self.company.corporate_number,
            status='approved'
        )

        # 契約書パターンを作成
        self.contract_pattern = ContractPattern.objects.create(name='Test Pattern', domain='10')

        # ①「承認済」の契約を作成
        self.approved_contract = ClientContract.objects.create(
            client=self.test_client,
            contract_name='Approved Contract',
            start_date=datetime.date.today(),
            contract_pattern=self.contract_pattern,
            contract_status=ClientContract.ContractStatus.APPROVED,
            corporate_number=self.company.corporate_number,
        )

        # ②「発行済」の契約を作成
        self.issued_contract = ClientContract.objects.create(
            client=self.test_client,
            contract_name='Issued Contract',
            start_date=datetime.date.today(),
            contract_pattern=self.contract_pattern,
            contract_status=ClientContract.ContractStatus.ISSUED,
            corporate_number=self.company.corporate_number,
        )
        # 発行済契約には、確認ボタンの表示条件である発行済みPDFが必要
        ClientContractPrint.objects.create(
            client_contract=self.issued_contract,
            print_type=ClientContractPrint.PrintType.CONTRACT,
            document_title='契約書'
        )

        # ③「下書き」の契約を作成（これはリストに表示されないはず）
        self.draft_contract = ClientContract.objects.create(
            client=self.test_client,
            contract_name='Draft Contract',
            start_date=datetime.date.today(),
            contract_pattern=self.contract_pattern,
            contract_status=ClientContract.ContractStatus.DRAFT,
            corporate_number=self.company.corporate_number,
        )

        # テスト用のクライアント（ブラウザ）を準備
        self.client = Client()

    def test_list_contracts_and_button_visibility(self):
        """承認済・発行済契約が表示され、ボタンの可視性が正しいことをテスト"""
        # クライアントユーザーとしてログイン
        self.client.login(username='clientuser', password='testpass123')

        # 契約確認一覧ページにアクセス
        url = reverse('contract:client_contract_confirm_list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        # 「承認済」と「発行済」の契約がリストに含まれていることを確認
        self.assertContains(response, self.approved_contract.contract_name)
        self.assertContains(response, self.issued_contract.contract_name)

        # 「下書き」の契約がリストに含まれていないことを確認
        self.assertNotContains(response, self.draft_contract.contract_name)

        # 「承認済」契約の行に「確認」ボタンがないことを確認（- が表示される）
        # ボタンのform action自体が存在しないことで確認する
        confirm_form_action_url_approved = f'<form method="post" action="{url}" class="d-inline">'
        self.assertNotContains(response, f'<input type="hidden" name="contract_id" value="{self.approved_contract.pk}">')

        # 「発行済」契約の行に「確認」ボタンがあることを確認
        self.assertContains(response, f'<input type="hidden" name="contract_id" value="{self.issued_contract.pk}">')
        self.assertContains(response, '<button type="submit" class="btn btn-sm btn-primary">確認</button>')


class ClientContractIssueHistoryViewTest(TestCase):
    """クライアント契約発行履歴ビューのテスト"""

    def setUp(self):
        """テストデータの準備"""
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        from apps.company.models import Company
        from ..models import ClientContractPrint

        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='testuser@example.com'
        )
        # 必要な権限を付与
        content_type = ContentType.objects.get_for_model(ClientContract)
        permissions = Permission.objects.filter(content_type=content_type)
        self.user.user_permissions.set(permissions)

        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

        self.company = Company.objects.create(name='Test Company', corporate_number='1112223334445')
        self.test_client_model = TestClient.objects.create(name='Test Client', corporate_number='6000000000001')
        self.contract_pattern = ContractPattern.objects.create(name='Test Pattern', domain='10')

        # 10件以上の発行履歴を持つ契約
        self.contract_many = ClientContract.objects.create(
            client=self.test_client_model,
            contract_name='Many Prints Contract',
            start_date=datetime.date.today(),
            contract_pattern=self.contract_pattern,
            corporate_number=self.company.corporate_number,
        )
        for i in range(12):
            ClientContractPrint.objects.create(
                client_contract=self.contract_many,
                printed_by=self.user,
                document_title=f'Document {i+1}'
            )

        # 10件未満の発行履歴を持つ契約
        self.contract_few = ClientContract.objects.create(
            client=self.test_client_model,
            contract_name='Few Prints Contract',
            start_date=datetime.date.today(),
            contract_pattern=self.contract_pattern,
            corporate_number=self.company.corporate_number,
        )
        for i in range(5):
            ClientContractPrint.objects.create(
                client_contract=self.contract_few,
                printed_by=self.user,
                document_title=f'Doc {i+1}'
            )

    def test_detail_view_history_limit(self):
        """詳細ページで発行履歴が10件に制限されることをテスト"""
        url = reverse('contract:client_contract_detail', kwargs={'pk': self.contract_many.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['issue_history_for_display']), 10)
        self.assertEqual(response.context['issue_history_count'], 12)
        self.assertContains(response, '全て表示')

    def test_detail_view_history_less_than_limit(self):
        """詳細ページで発行履歴が10件未満の場合のテスト"""
        url = reverse('contract:client_contract_detail', kwargs={'pk': self.contract_few.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['issue_history_for_display']), 5)
        self.assertEqual(response.context['issue_history_count'], 5)
        self.assertContains(response, '全て表示')

    def test_issue_history_list_view_and_pagination(self):
        """発行履歴一覧ページとページネーションをテスト"""
        from ..models import ClientContractPrint
        from django.utils import timezone
        from datetime import timedelta

        # 既存の履歴をクリアして、テストごとに状態をリセット
        ClientContractPrint.objects.filter(client_contract=self.contract_many).delete()

        # タイムスタンプが明確に異なる25件の履歴を作成
        base_time = timezone.now()
        for i in range(25):
            ClientContractPrint.objects.create(
                client_contract=self.contract_many,
                printed_by=self.user,
                document_title=f'Document {i + 1}',
                printed_at=base_time - timedelta(days=i)  # 新しいものが若く、古いものが古くなるように
            )

        url = reverse('contract:client_contract_issue_history_list', kwargs={'pk': self.contract_many.pk})

        # 1ページ目
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        page1_docs = [item.document_title for item in response.context['page_obj'].object_list]
        self.assertEqual(len(page1_docs), 20)
        self.assertIn('Document 25', page1_docs)  # Highest PK, so it should be first
        self.assertNotIn('Document 5', page1_docs) # Should be on page 2

        # 2ページ目
        response = self.client.get(url, {'page': 2})
        self.assertEqual(response.status_code, 200)
        page2_docs = [item.document_title for item in response.context['page_obj'].object_list]
        self.assertEqual(len(page2_docs), 5)
        self.assertIn('Document 5', page2_docs)
        self.assertIn('Document 1', page2_docs)   # Lowest PK
        self.assertNotIn('Document 6', page2_docs) # Should be on page 1