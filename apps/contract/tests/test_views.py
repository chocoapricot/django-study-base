from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.messages import get_messages
from ..models import ClientContract, StaffContract, ClientContractHaken, ClientContractTtp, ContractAssignment
from apps.client.models import Client as TestClient, ClientUser, ClientDepartment
from apps.staff.models import Staff
from apps.master.models import ContractPattern, DefaultValue
from apps.common.constants import Constants
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
        from apps.system.settings.models import Dropdowns
        
        # Dropdownsデータを作成
        Dropdowns.objects.create(
            category='contract_status',
            value=Constants.CONTRACT_STATUS.DRAFT,
            name='作成中',
            active=True
        )
        Dropdowns.objects.create(
            category='contract_status',
            value=Constants.CONTRACT_STATUS.APPROVED,
            name='承認済',
            active=True
        )
        Dropdowns.objects.create(
            category='contract_status',
            value=Constants.CONTRACT_STATUS.ISSUED,
            name='発行済',
            active=True
        )
        Dropdowns.objects.create(
            category='contract_status',
            value=Constants.CONTRACT_STATUS.CONFIRMED,
            name='契約済',
            active=True
        )

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

        content_type_assignment = ContentType.objects.get_for_model(ContractAssignment)
        assignment_permissions = Permission.objects.filter(content_type=content_type_assignment)
        all_permissions.extend(assignment_permissions)

        self.user.user_permissions.set(all_permissions)

        self.company = Company.objects.create(name='Test Company', corporate_number='1112223334445')

        self.test_client = TestClient.objects.create(
            name='Test Client',
            corporate_number='6000000000001',
            name_furigana='テストクライアント',
            address='Test Address'
        )
        
        # 就業時間パターン
        from apps.master.models import WorkTimePattern, OvertimePattern
        self.worktime_pattern = WorkTimePattern.objects.create(name='標準勤務', is_active=True)
        self.overtime_pattern = OvertimePattern.objects.create(name='標準時間外')
        
        self.contract_pattern = ContractPattern.objects.create(name='Test Pattern', domain='10', contract_type_code='20')
        self.client_contract = ClientContract.objects.create(
            client=self.test_client,
            contract_name='Test Contract',
            start_date=datetime.date.today(),
            end_date=datetime.date.today() + datetime.timedelta(days=30),
            contract_pattern=self.contract_pattern,
            client_contract_type_code='20',
            corporate_number=self.company.corporate_number,
            worktime_pattern=self.worktime_pattern,
            overtime_pattern=self.overtime_pattern
        )

        # 抵触日ありの派遣先事業所と契約
        self.haken_office_with_teishokubi = ClientDepartment.objects.create(
            client=self.test_client,
            name='本社',
            haken_jigyosho_teishokubi=datetime.date(2025, 12, 31)
        )
        ClientContractHaken.objects.create(
            client_contract=self.client_contract,
            haken_office=self.haken_office_with_teishokubi
        )

        # 抵触日なしの派遣先事業所と契約
        self.contract_without_teishokubi = ClientContract.objects.create(
            client=self.test_client,
            contract_name='No Clash Day Contract',
            start_date=datetime.date.today(),
            contract_pattern=self.contract_pattern,
            client_contract_type_code='20',
            corporate_number=self.company.corporate_number,
            worktime_pattern=self.worktime_pattern,
            overtime_pattern=self.overtime_pattern
        )
        self.haken_office_without_teishokubi = ClientDepartment.objects.create(
            client=self.test_client,
            name='支社'
        )
        ClientContractHaken.objects.create(
            client_contract=self.contract_without_teishokubi,
            haken_office=self.haken_office_without_teishokubi
        )

        # 紹介予定派遣情報を作成
        self.ttp_info = ClientContractTtp.objects.create(
            haken=self.client_contract.haken_info,
            contract_period='最長6ヶ月',
            probation_period='なし',
            business_content='テストTTP業務内容',
        )

        self.non_haken_contract_pattern = ContractPattern.objects.create(name='Non-Haken Pattern', domain='10', contract_type_code='10')
        self.non_haken_contract = ClientContract.objects.create(
            client=self.test_client,
            contract_name='Test Non-Haken Contract',
            start_date=datetime.date.today(),
            end_date=datetime.date.today() + datetime.timedelta(days=30),
            contract_pattern=self.non_haken_contract_pattern,
            client_contract_type_code='10',
            contract_status=Constants.CONTRACT_STATUS.DRAFT, # 編集可能にするためDRAFTに
            corporate_number=self.company.corporate_number,
            worktime_pattern=self.worktime_pattern,
            overtime_pattern=self.overtime_pattern
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
        self.bill_unit_monthly = Dropdowns.objects.create(category='bill_unit', value='10', name='月額', active=True)

        self.client.login(username='testuser', password='testpass123')

    def test_permission_denied(self):
        """権限のないユーザーがアクセスできないことをテスト"""
        # 権限のないユーザーを作成
        no_perm_user = User.objects.create_user(
            username='nopermuser',
            email='noperm@example.com',
            password='testpass123'
        )
        self.client.login(username='nopermuser', password='testpass123')

        # contract_indexビューにアクセス
        response = self.client.get(reverse('contract:contract_index'))
        self.assertEqual(response.status_code, 403)

    def test_issue_teishokubi_notification_updates_contract(self):
        """抵触日通知書を共有した際に、契約の共有日時と共有者が更新されるかテスト"""
        # 契約を承認済みにする
        self.client_contract.contract_status = Constants.CONTRACT_STATUS.APPROVED
        self.client_contract.save()

        # 初期状態では共有日時はNone
        self.assertIsNone(self.client_contract.teishokubi_notification_issued_at)
        self.assertIsNone(self.client_contract.teishokubi_notification_issued_by)

        # 抵触日通知書を共有
        url = reverse('contract:issue_teishokubi_notification', kwargs={'pk': self.client_contract.pk})
        response = self.client.post(url, {})

        # リダイレクトされることを確認
        self.assertEqual(response.status_code, 302)

        # DBから契約を再取得
        self.client_contract.refresh_from_db()

        # 共有日時と共有者が記録されていることを確認
        self.assertIsNotNone(self.client_contract.teishokubi_notification_issued_at)
        self.assertEqual(self.client_contract.teishokubi_notification_issued_by, self.user)

    def test_unapprove_resets_teishokubi_notification(self):
        """承認解除時に抵触日通知書の共有日時と共有者がリセットされるかテスト"""
        from django.utils import timezone

        # 契約を承認済みにし、抵触日通知書を共有済みの状態にする
        self.client_contract.contract_status = Constants.CONTRACT_STATUS.APPROVED
        self.client_contract.teishokubi_notification_issued_at = timezone.now()
        self.client_contract.teishokubi_notification_issued_by = self.user
        self.client_contract.save()

        # 承認解除（is_approvedを送らない）
        url = reverse('contract:client_contract_approve', kwargs={'pk': self.client_contract.pk})
        response = self.client.post(url, {})

        # リダイレクトされることを確認
        self.assertEqual(response.status_code, 302)

        # DBから契約を再取得
        self.client_contract.refresh_from_db()

        # 共有日時と共有者がNoneにリセットされていることを確認
        self.assertIsNone(self.client_contract.teishokubi_notification_issued_at)
        self.assertIsNone(self.client_contract.teishokubi_notification_issued_by)

    def test_client_contract_list_view(self):
        """クライアント契約一覧ビューのテスト"""
        response = self.client.get(reverse('contract:client_contract_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'クライアント契約一覧')

    def test_client_contract_pdf_view(self):
        """クライアント契約PDFビューのテスト"""
        response = self.client.get(reverse('contract:client_contract_pdf', kwargs={'pk': self.client_contract.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response['Content-Disposition'].startswith(f'attachment; filename="client_contract_{self.client_contract.pk}_'))

    def test_client_contract_pdf_approved_to_issued(self):
        """承認済みのクライアント契約書を印刷すると発行済になるテスト"""
        from ..models import ClientContractPrint
        self.client_contract.contract_status = Constants.CONTRACT_STATUS.APPROVED
        self.client_contract.save()

        self.assertEqual(ClientContractPrint.objects.count(), 0)
        response = self.client.get(reverse('contract:client_contract_pdf', kwargs={'pk': self.client_contract.pk}))
        self.assertEqual(response.status_code, 200)

        # ステータスが発行済に変わっていることを確認
        self.client_contract.refresh_from_db()
        self.assertEqual(self.client_contract.contract_status, Constants.CONTRACT_STATUS.ISSUED)

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

        # テストユーザーをClientUserとして登録（セキュリティチェックのため）
        ClientUser.objects.create(
            client=self.test_client,
            email=self.user.email,
            name_last='Test',
            name_first='User'
        )

        # クライアント契約のテスト
        self.client_contract.contract_status = Constants.CONTRACT_STATUS.APPROVED
        self.client_contract.save()
        self.client.get(reverse('contract:client_contract_pdf', kwargs={'pk': self.client_contract.pk}))
        print_history = ClientContractPrint.objects.first()
        self.assertIsNotNone(print_history)

        response = self.client.get(reverse('contract:download_client_contract_pdf', kwargs={'pk': print_history.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response['Content-Disposition'].startswith(f'attachment; filename="'))

    def test_unapprove_resets_notification_status_and_info_on_ui(self):
        """承認解除時に通知書ステータスと発行者情報がUI上リセットされるかテスト"""
        from django.utils import timezone

        # 1. ユーザーに姓名を設定
        self.user.name_last = '山田'
        self.user.name_first = '太郎'
        self.user.save()
        user_full_name = self.user.get_full_name_japanese()

        # 2. 契約を承認済みにし、通知書も共有済みの状態にする
        self.client_contract.contract_status = Constants.CONTRACT_STATUS.APPROVED
        self.client_contract.teishokubi_notification_issued_at = timezone.now()
        self.client_contract.teishokubi_notification_issued_by = self.user
        self.client_contract.save()

        # 3. 詳細ページでスイッチがチェックされ、発行者情報が表示されていることを確認
        detail_url = reverse('contract:client_contract_detail', kwargs={'pk': self.client_contract.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        # スイッチがチェックされているか
        self.assertRegex(response.content.decode('utf-8'), r'<input class="form-check-input" type="checkbox" id="issueClashDayNotificationSwitch"[^>]*checked')
        # 発行者情報が表示されているか
        self.assertContains(response, user_full_name)

        # 4. 契約の承認を解除する
        approve_url = reverse('contract:client_contract_approve', kwargs={'pk': self.client_contract.pk})
        response = self.client.post(approve_url, data={}) # is_approved がないので解除になる
        self.assertEqual(response.status_code, 302) # 詳細ページへリダイレクト
        self.client_contract.refresh_from_db()
        self.assertEqual(self.client_contract.contract_status, Constants.CONTRACT_STATUS.DRAFT)

        # 5. 詳細ページでスイッチがチェックされておらず、発行者情報も表示されていないことを確認
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        # スイッチがチェックされていないか
        self.assertNotRegex(response.content.decode('utf-8'), r'<input class="form-check-input" type="checkbox" id="issueClashDayNotificationSwitch"[^>]*checked')
        # 承認解除により発行者情報が表示されなくなることを確認する。
        # 変更履歴にユーザー名が表示される可能性があるため、より具体的な文字列で検証する。
        self.assertNotContains(response, f'　{user_full_name}）')

    def test_issue_contract_and_dispatch_notification_for_haken(self):
        """派遣契約の契約書発行時に、個別契約書と派遣先通知書が同時に発行されるかテスト"""
        from ..models import ClientContractPrint

        # 派遣契約を承認済みにする
        self.client_contract.contract_status = Constants.CONTRACT_STATUS.APPROVED
        self.client_contract.save()

        initial_print_count = ClientContractPrint.objects.filter(client_contract=self.client_contract).count()

        # 契約書発行のURLをPOST
        issue_url = reverse('contract:client_contract_issue', kwargs={'pk': self.client_contract.pk})
        response = self.client.post(issue_url, {})

        # 詳細ページにリダイレクトされることを確認
        self.assertEqual(response.status_code, 302)
        self.client_contract.refresh_from_db()

        # 契約ステータスが「発行済」になっていることを確認
        self.assertEqual(self.client_contract.contract_status, Constants.CONTRACT_STATUS.ISSUED)

        # 発行履歴が2件増えていることを確認
        final_print_count = ClientContractPrint.objects.filter(client_contract=self.client_contract).count()
        self.assertEqual(final_print_count, initial_print_count + 2)

        # 発行された履歴の種類を確認
        self.assertTrue(ClientContractPrint.objects.filter(
            client_contract=self.client_contract,
            print_type=ClientContractPrint.PrintType.CONTRACT
        ).exists())
        self.assertTrue(ClientContractPrint.objects.filter(
            client_contract=self.client_contract,
            print_type=ClientContractPrint.PrintType.DISPATCH_NOTIFICATION
        ).exists())

        # メッセージの確認
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('契約書を発行しました' in str(m) for m in messages))
        self.assertTrue(any('派遣通知書を同時に発行しました' in str(m) for m in messages))

    def test_issue_contract_for_non_haken(self):
        """非派遣契約の契約書発行時に、個別契約書のみが発行されるかテスト"""
        from ..models import ClientContractPrint

        # このテストケースでは承認済みの契約が必要なため、ステータスを更新
        self.non_haken_contract.contract_status = Constants.CONTRACT_STATUS.APPROVED
        self.non_haken_contract.save()

        initial_print_count = ClientContractPrint.objects.filter(client_contract=self.non_haken_contract).count()

        # 契約書発行のURLをPOST
        issue_url = reverse('contract:client_contract_issue', kwargs={'pk': self.non_haken_contract.pk})
        response = self.client.post(issue_url, {})

        # 詳細ページにリダイレクトされることを確認
        self.assertEqual(response.status_code, 302)
        self.non_haken_contract.refresh_from_db()

        # 契約ステータスが「発行済」になっていることを確認
        self.assertEqual(self.non_haken_contract.contract_status, Constants.CONTRACT_STATUS.ISSUED)

        # 発行履歴が1件増えていることを確認
        final_print_count = ClientContractPrint.objects.filter(client_contract=self.non_haken_contract).count()
        self.assertEqual(final_print_count, initial_print_count + 1)

        # 発行された履歴の種類を確認
        self.assertTrue(ClientContractPrint.objects.filter(
            client_contract=self.non_haken_contract,
            print_type=ClientContractPrint.PrintType.CONTRACT
        ).exists())
        self.assertFalse(ClientContractPrint.objects.filter(
            client_contract=self.non_haken_contract,
            print_type=ClientContractPrint.PrintType.DISPATCH_NOTIFICATION
        ).exists())

        # メッセージの確認
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('契約書を発行しました' in str(m) for m in messages))
        self.assertFalse(any('派遣通知書を同時に発行しました' in str(m) for m in messages))

    def test_ttp_info_displayed_for_ttp_contract(self):
        """紹介予定派遣情報を持つ契約詳細ページで、TTP情報が表示されるかテスト"""
        url = reverse('contract:client_contract_detail', kwargs={'pk': self.client_contract.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '紹介予定派遣情報')
        self.assertContains(response, self.ttp_info.business_content)

    def test_ttp_info_not_displayed_for_haken_without_ttp(self):
        """紹介予定派遣情報を持たない派遣契約詳細ページで、TTP情報が表示されないかテスト"""
        # この契約は派遣だがTTP情報はない
        url = reverse('contract:client_contract_detail', kwargs={'pk': self.contract_without_teishokubi.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # TTP情報のセクションが表示されないことを確認（より具体的なチェック）
        self.assertNotContains(response, '<h6 class="text-muted mb-0">紹介予定派遣情報</h6>')
        # TTP情報の具体的な項目が表示されないことを確認
        self.assertNotContains(response, '雇用しようとする者の名称')
        self.assertNotContains(response, '契約期間')
        self.assertNotContains(response, '試用期間に関する事項')

    def test_contract_assignment_card_display(self):
        """契約詳細ページでの契約アサインカードの表示をテストする"""
        from ..models import ContractAssignment

        # アサイン用のスタッフ契約を作成
        assigned_staff_contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name='Assigned Staff Contract',
            start_date=datetime.date(2025, 1, 1),
            end_date=datetime.date(2025, 12, 31),
            contract_pattern=self.staff_pattern,
        )

        # --- シナリオ1: アサインなし ---
        # クライアント契約詳細ページ
        client_detail_url = reverse('contract:client_contract_detail', kwargs={'pk': self.client_contract.pk})
        response = self.client.get(client_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '契約アサイン')
        self.assertContains(response, 'アサインされているスタッフはいません。')

        # スタッフ契約詳細ページ
        staff_detail_url = reverse('contract:staff_contract_detail', kwargs={'pk': assigned_staff_contract.pk})
        response = self.client.get(staff_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '契約アサイン')
        self.assertContains(response, 'アサインされているクライアントはありません。')

        # --- シナリオ2: アサインあり ---
        # 契約をアサイン
        ContractAssignment.objects.create(
            client_contract=self.client_contract,
            staff_contract=assigned_staff_contract
        )

        # クライアント契約詳細ページ
        response = self.client.get(client_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '契約アサイン')
        self.assertNotContains(response, 'アサインされているスタッフはいません。')
        # スタッフ名と契約期間が表示されていることを確認
        self.assertContains(response, f'{assigned_staff_contract.staff.name_last} {assigned_staff_contract.staff.name_first}')
        self.assertContains(response, '2025/01/01～2025/12/31')
        # 契約アサイン詳細へのリンクがあることを確認
        assignment_detail_url = reverse('contract:contract_assignment_detail', kwargs={'assignment_pk': ContractAssignment.objects.first().pk})
        self.assertContains(response, f'href="{assignment_detail_url}?from=client"')

        # スタッフ契約詳細ページ
        response = self.client.get(staff_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '契約アサイン')
        self.assertNotContains(response, 'アサインされているクライアントはありません。')
        # クライアント名と契約期間が表示されていることを確認
        self.assertContains(response, self.client_contract.client.name)
        expected_end_date = self.client_contract.end_date.strftime("%Y/%m/%d")
        self.assertContains(response, expected_end_date)
        # 契約アサイン詳細へのリンクがあることを確認
        assignment_detail_url = reverse('contract:contract_assignment_detail', kwargs={'assignment_pk': ContractAssignment.objects.first().pk})
        self.assertContains(response, f'href="{assignment_detail_url}?from=staff"')

    def test_ttp_info_not_displayed_for_non_haken_contract(self):
        """非派遣契約詳細ページで、TTP情報が表示されないかテスト"""
        url = reverse('contract:client_contract_detail', kwargs={'pk': self.non_haken_contract.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '紹介予定派遣情報')

    def test_client_contract_business_content_for_non_haken(self):
        """非派遣契約で業務内容が保存されるかテスト"""
        url = reverse('contract:client_contract_update', kwargs={'pk': self.non_haken_contract.pk})
        post_data = {
            'client': self.test_client.pk,
            'contract_name': self.non_haken_contract.contract_name,
            'start_date': self.non_haken_contract.start_date,
            'end_date': self.non_haken_contract.end_date,
            'contract_pattern': self.non_haken_contract_pattern.pk,
            'client_contract_type_code': '10',
            'business_content': 'これは請負契約の業務内容です。',
            'bill_unit': '10', # 月額
            'worktime_pattern': self.worktime_pattern.pk,
            'overtime_pattern': self.overtime_pattern.pk,
        }
        response = self.client.post(url, post_data)

        self.assertEqual(response.status_code, 302, "POSTリクエストがリダイレクトされませんでした。")

        self.non_haken_contract.refresh_from_db()
        self.assertEqual(self.non_haken_contract.business_content, 'これは請負契約の業務内容です。')


class ClientContractConfirmListViewTest(TestCase):
    """クライアント契約確認一覧ビューのテスト"""

    def setUp(self):
        """テストデータの準備"""
        from apps.company.models import Company
        from apps.connect.models import ConnectClient
        from ..models import ClientContractPrint

        # 会社を作成
        self.company = Company.objects.create(name='Test Company', corporate_number='1234567890123', tenant_id=1)

        # クライアントとクライアントユーザーを作成
        self.test_client = TestClient.objects.create(name='Test Client Corp', corporate_number='9876543210987', tenant_id=1)
        self.client_user = User.objects.create_user(
            username='clientuser',
            email='client@example.com',
            password='testpass123',
            tenant_id=1
        )
        self.client_user_profile = ClientUser.objects.create(
            client=self.test_client,
            email=self.client_user.email,
            name_last='Client',
            name_first='User',
            tenant_id=1
        )

        # 会社とクライアントユーザーを接続
        ConnectClient.objects.create(
            email=self.client_user.email,
            corporate_number=self.company.corporate_number,
            status='approved'
        )

        # 契約書パターンを作成
        self.contract_pattern = ContractPattern.objects.create(name='Test Pattern', domain='10')
        
        # 就業時間パターン
        from apps.master.models import WorkTimePattern, OvertimePattern
        self.worktime_pattern = WorkTimePattern.objects.create(name='標準勤務', is_active=True)
        self.overtime_pattern = OvertimePattern.objects.create(name='標準時間外')

        # ①「承認済」の契約を作成
        self.approved_contract = ClientContract.objects.create(
            client=self.test_client,
            contract_name='Approved Contract',
            start_date=datetime.date.today(),
            contract_pattern=self.contract_pattern,
            contract_status=Constants.CONTRACT_STATUS.APPROVED,
            corporate_number=self.company.corporate_number,
            worktime_pattern=self.worktime_pattern,
            overtime_pattern=self.overtime_pattern,
        )

        # ②「発行済」の契約を作成
        self.issued_contract = ClientContract.objects.create(
            client=self.test_client,
            contract_name='Issued Contract',
            start_date=datetime.date.today(),
            contract_pattern=self.contract_pattern,
            contract_status=Constants.CONTRACT_STATUS.ISSUED,
            corporate_number=self.company.corporate_number,
            worktime_pattern=self.worktime_pattern,
            overtime_pattern=self.overtime_pattern,
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
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            corporate_number=self.company.corporate_number,
            worktime_pattern=self.worktime_pattern,
            overtime_pattern=self.overtime_pattern,
        )

    def test_list_contracts_and_button_visibility(self):
        """承認済・発行済契約が表示され、ボタンの可視性が正しいことをテスト"""
        # クライアントユーザーとしてログイン
        self.client.login(username='clientuser', password='testpass123')

        # セッションにテナントIDを設定
        session = self.client.session
        session['current_tenant_id'] = 1
        session.save()

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

        self.client.login(username='testuser', password='testpass123')

        self.company = Company.objects.create(name='Test Company', corporate_number='1112223334445')
        self.test_client_model = TestClient.objects.create(name='Test Client', corporate_number='6000000000001')
        self.contract_pattern = ContractPattern.objects.create(name='Test Pattern', domain='10')
        
        # 就業時間パターン
        from apps.master.models import WorkTimePattern, OvertimePattern
        self.worktime_pattern = WorkTimePattern.objects.create(name='標準勤務', is_active=True)
        self.overtime_pattern = OvertimePattern.objects.create(name='標準時間外')

        # 10件以上の発行履歴を持つ契約
        self.contract_many = ClientContract.objects.create(
            client=self.test_client_model,
            contract_name='Many Prints Contract',
            start_date=datetime.date.today(),
            contract_pattern=self.contract_pattern,
            corporate_number=self.company.corporate_number,
            worktime_pattern=self.worktime_pattern,
            overtime_pattern=self.overtime_pattern,
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
            worktime_pattern=self.worktime_pattern,
            overtime_pattern=self.overtime_pattern,
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

    def test_issue_history_list_view_shows_header(self):
        """発行履歴一覧ページに契約ヘッダーが表示されるかテスト"""
        url = reverse('contract:client_contract_issue_history_list', kwargs={'pk': self.contract_many.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # ヘッダー内の特徴的な文字列で存在を確認
        self.assertContains(response, '契約番号')
        # 契約名が表示されているかも確認
        self.assertContains(response, self.contract_many.contract_name)


class ClientContractTtpViewTest(TestCase):
    """紹介予定派遣情報ビューのテスト"""

    def setUp(self):
        """テストデータの準備"""
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        from apps.company.models import Company

        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')

        # 必要な権限を付与
        content_types = [
            ContentType.objects.get_for_model(ClientContract),
            ContentType.objects.get_for_model(ClientContractHaken),
            ContentType.objects.get_for_model(ClientContractTtp),
        ]
        permissions = Permission.objects.filter(content_type__in=content_types)
        self.user.user_permissions.set(permissions)

        self.company = Company.objects.create(name='Test Company', corporate_number='1112223334445')
        self.test_client_model = TestClient.objects.create(name='Test Client', corporate_number='6000000000001')
        self.contract_pattern = ContractPattern.objects.create(name='Test Pattern', domain='10', contract_type_code='20')
        from apps.master.models import OvertimePattern
        self.overtime_pattern = OvertimePattern.objects.create(name='標準時間外')

        # ステータスが「作成中」の契約
        self.draft_contract = ClientContract.objects.create(
            client=self.test_client_model,
            contract_name='Draft TTP Contract',
            start_date=datetime.date.today(),
            contract_pattern=self.contract_pattern,
            client_contract_type_code='20',
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            overtime_pattern=self.overtime_pattern,
        )
        self.draft_haken = ClientContractHaken.objects.create(client_contract=self.draft_contract)
        self.draft_ttp = ClientContractTtp.objects.create(haken=self.draft_haken, business_content='Draft Content')

        # ステータスが「承認済」の契約
        self.approved_contract = ClientContract.objects.create(
            client=self.test_client_model,
            contract_name='Approved TTP Contract',
            start_date=datetime.date.today(),
            contract_pattern=self.contract_pattern,
            client_contract_type_code='20',
            contract_status=Constants.CONTRACT_STATUS.APPROVED,
            overtime_pattern=self.overtime_pattern,
        )
        self.approved_haken = ClientContractHaken.objects.create(client_contract=self.approved_contract)
        self.approved_ttp = ClientContractTtp.objects.create(haken=self.approved_haken, business_content='Approved Content')

    def test_ttp_buttons_visibility_for_draft_contract(self):
        """「作成中」の契約では、TTP詳細ページに編集・削除ボタンが表示される"""
        url = reverse('contract:client_contract_ttp_detail', kwargs={'pk': self.draft_ttp.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        update_url = reverse('contract:client_contract_ttp_update', kwargs={'pk': self.draft_ttp.pk})
        delete_url = reverse('contract:client_contract_ttp_delete', kwargs={'pk': self.draft_ttp.pk})
        self.assertContains(response, f'href="{update_url}"')
        self.assertContains(response, f'href="{delete_url}"')

    def test_ttp_buttons_hidden_for_approved_contract(self):
        """「作成中」以外の契約では、TTP詳細ページに編集・削除ボタンが表示されない"""
        url = reverse('contract:client_contract_ttp_detail', kwargs={'pk': self.approved_ttp.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        update_url = reverse('contract:client_contract_ttp_update', kwargs={'pk': self.approved_ttp.pk})
        delete_url = reverse('contract:client_contract_ttp_delete', kwargs={'pk': self.approved_ttp.pk})
        self.assertNotContains(response, f'href="{update_url}"')
        self.assertNotContains(response, f'href="{delete_url}"')

    def test_ttp_update_get_allowed_for_draft_contract(self):
        """「作成中」の契約では、TTP編集ページにアクセスできる"""
        url = reverse('contract:client_contract_ttp_update', kwargs={'pk': self.draft_ttp.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_ttp_update_get_denied_for_approved_contract(self):
        """「作成中」以外の契約では、TTP編集ページへのアクセスが拒否される"""
        url = reverse('contract:client_contract_ttp_update', kwargs={'pk': self.approved_ttp.pk})
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('contract:client_contract_detail', kwargs={'pk': self.approved_contract.pk}), status_code=302, target_status_code=200)
        messages = list(response.context['messages'])
        self.assertTrue(any('契約が作成中でないため、紹介予定派遣情報は編集できません。' in str(m) for m in messages))

    def test_ttp_delete_get_allowed_for_draft_contract(self):
        """「作成中」の契約では、TTP削除ページにアクセスできる"""
        url = reverse('contract:client_contract_ttp_delete', kwargs={'pk': self.draft_ttp.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_ttp_delete_get_denied_for_approved_contract(self):
        """「作成中」以外の契約では、TTP削除ページへのアクセスが拒否される"""
        url = reverse('contract:client_contract_ttp_delete', kwargs={'pk': self.approved_ttp.pk})
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse('contract:client_contract_detail', kwargs={'pk': self.approved_contract.pk}), status_code=302, target_status_code=200)
        messages = list(response.context['messages'])
        self.assertTrue(any('契約が作成中でないため、紹介予定派遣情報は削除できません。' in str(m) for m in messages))

    def test_ttp_create_form_initial_values_from_master(self):
        """TTP作成画面で、DefaultValueマスタから初期値が設定されるかテスト"""
        # 1. DefaultValueマスタにテストデータを登録
        DefaultValue.objects.create(key='ClientContractTtp.contract_period', target_item='契約期間', value='デフォルト契約期間')
        DefaultValue.objects.create(key='ClientContractTtp.probation_period', target_item='試用期間', value='デフォルト試用期間')
        # working_hoursは設定しないでおき、キーが存在しない場合もテストする

        # 2. TTP情報を持たない派遣契約を準備
        ttp_less_contract = ClientContract.objects.create(
            client=self.test_client_model,
            contract_name='TTP-less Contract',
            start_date=datetime.date.today(),
            contract_pattern=self.contract_pattern,
            client_contract_type_code='20',
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            overtime_pattern=self.overtime_pattern,
        )
        ttp_less_haken = ClientContractHaken.objects.create(client_contract=ttp_less_contract)

        # 3. TTP作成画面にGETリクエスト
        url = reverse('contract:client_contract_ttp_create', kwargs={'haken_pk': ttp_less_haken.pk})
        response = self.client.get(url)

        # 4. レスポンスを検証
        self.assertEqual(response.status_code, 200)
        form = response.context.get('form')
        self.assertIsNotNone(form)

        # フォームの初期値が正しく設定されていることを確認
        self.assertEqual(form.initial.get('contract_period'), 'デフォルト契約期間')
        self.assertEqual(form.initial.get('probation_period'), 'デフォルト試用期間')
        # マスタに存在しないキーは設定されていないことを確認
        self.assertIsNone(form.initial.get('working_hours'))

    def test_ttp_create_form_initial_values_from_haken(self):
        """TTP作成画面で、派遣情報から初期値が設定されるかテスト"""
        # 1. TTP情報を持たない派遣契約を準備
        haken_contract = ClientContract.objects.create(
            client=self.test_client_model, # client.name is 'Test Client'
            contract_name='Haken Initial Value Test',
            start_date=datetime.date.today(),
            contract_pattern=self.contract_pattern,
            client_contract_type_code='20',
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            business_content='派遣元の業務内容',
            overtime_pattern=self.overtime_pattern,
        )
        haken_info = ClientContractHaken.objects.create(
            client_contract=haken_contract,
            work_location='派遣元の就業場所',
        )

        # 2. TTP作成画面にGETリクエスト
        url = reverse('contract:client_contract_ttp_create', kwargs={'haken_pk': haken_info.pk})
        response = self.client.get(url)

        # 3. レスポンスを検証
        self.assertEqual(response.status_code, 200)
        form = response.context.get('form')
        self.assertIsNotNone(form)

        # フォームの初期値が正しく設定されていることを確認
        self.assertEqual(form.initial.get('employer_name'), self.test_client_model.name)
        self.assertEqual(form.initial.get('business_content'), haken_info.client_contract.business_content)
        self.assertEqual(form.initial.get('work_location'), haken_info.work_location)


class ContractAssignmentViewTest(TestCase):
    """契約アサイン関連ビューのテスト"""

    def setUp(self):
        """テストデータの準備"""
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        from apps.company.models import Company
        from ..models import ContractAssignment

        # ユーザーと権限
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        content_types = [
            ContentType.objects.get_for_model(ClientContract),
            ContentType.objects.get_for_model(StaffContract),
            ContentType.objects.get_for_model(ContractAssignment),
        ]
        permissions = Permission.objects.filter(content_type__in=content_types)
        self.user.user_permissions.set(permissions)
        self.client.login(username='testuser', password='testpassword')

        # 会社、クライアント、スタッフ
        self.company = Company.objects.create(name='Test Company', corporate_number='1112223334445')
        self.test_client_model = TestClient.objects.create(name='Test Client', corporate_number='6000000000001')
        self.staff1 = Staff.objects.create(name_last='Staff', name_first='One', employee_no='S001', hire_date=datetime.date(2024, 1, 1))
        self.staff2 = Staff.objects.create(name_last='Staff', name_first='Two', employee_no='S002', hire_date=datetime.date(2024, 1, 1))

        # 契約パターン
        self.client_pattern = ContractPattern.objects.create(name='Client Pattern', domain='10')
        self.staff_pattern = ContractPattern.objects.create(name='Staff Pattern', domain='1')
        from apps.master.models import OvertimePattern
        self.overtime_pattern = OvertimePattern.objects.create(name='標準時間外')

        # --- テストデータ ---
        # 1. ベースとなるクライアント契約（作成中）
        self.client_contract_draft = ClientContract.objects.create(
            client=self.test_client_model, contract_name='Client Draft',
            start_date=datetime.date(2025, 4, 1), end_date=datetime.date(2025, 6, 30),
            contract_pattern=self.client_pattern, contract_status=Constants.CONTRACT_STATUS.DRAFT,
            overtime_pattern=self.overtime_pattern,
        )
        # 2. ベースとなるスタッフ契約（作成中）
        self.staff_contract_draft = StaffContract.objects.create(
            staff=self.staff1, contract_name='Staff Draft',
            start_date=datetime.date(2025, 5, 1), end_date=datetime.date(2025, 7, 31),
            contract_pattern=self.staff_pattern, contract_status=Constants.CONTRACT_STATUS.DRAFT,
            overtime_pattern=self.overtime_pattern,
        )
        # 3. 期間が重複するスタッフ契約（割当可能）
        self.assignable_staff_contract = StaffContract.objects.create(
            staff=self.staff2, contract_name='Assignable Staff',
            start_date=datetime.date(2025, 6, 1), end_date=datetime.date(2025, 8, 31),
            contract_pattern=self.staff_pattern, contract_status=Constants.CONTRACT_STATUS.DRAFT,
            overtime_pattern=self.overtime_pattern,
        )
        # 4. 期間が重複しないスタッフ契約（割当不可）
        self.non_overlapping_staff_contract = StaffContract.objects.create(
            staff=self.staff2, contract_name='Non Overlapping Staff',
            start_date=datetime.date(2026, 1, 1), end_date=datetime.date(2026, 3, 31),
            contract_pattern=self.staff_pattern, contract_status=Constants.CONTRACT_STATUS.DRAFT,
            overtime_pattern=self.overtime_pattern,
        )
        # 5. 承認済のクライアント契約（割当不可）
        self.client_contract_approved = ClientContract.objects.create(
            client=self.test_client_model, contract_name='Client Approved',
            start_date=datetime.date(2025, 4, 1), end_date=datetime.date(2025, 6, 30),
            contract_pattern=self.client_pattern, contract_status=Constants.CONTRACT_STATUS.APPROVED,
            overtime_pattern=self.overtime_pattern,
        )
        # 6. 既に割り当て済みのスタッフ契約
        self.already_assigned_staff_contract = StaffContract.objects.create(
            staff=self.staff1, contract_name='Already Assigned Staff',
            start_date=datetime.date(2025, 4, 15), end_date=datetime.date(2025, 5, 15),
            contract_pattern=self.staff_pattern, contract_status=Constants.CONTRACT_STATUS.DRAFT,
            overtime_pattern=self.overtime_pattern,
        )
        self.assignment = ContractAssignment.objects.create(
            client_contract=self.client_contract_draft, staff_contract=self.already_assigned_staff_contract
        )

        # 承認済み契約とのアサインも作成
        self.assignment_approved = ContractAssignment.objects.create(
            client_contract=self.client_contract_approved, staff_contract=self.staff_contract_draft
        )

    def test_assign_button_visibility(self):
        """詳細ページで「割当」ボタンが正しく表示/非表示になるかテスト"""
        # 作成中の契約詳細ページ -> ボタン表示
        url_draft = reverse('contract:client_contract_detail', kwargs={'pk': self.client_contract_draft.pk})
        response_draft = self.client.get(url_draft)
        self.assertContains(response_draft, '割当')

        # 承認済の契約詳細ページ -> ボタン非表示
        url_approved = reverse('contract:client_contract_detail', kwargs={'pk': self.client_contract_approved.pk})
        response_approved = self.client.get(url_approved)
        self.assertNotContains(response_approved, '割当')

    def test_client_contract_assignment_view(self):
        """クライアント契約への割当一覧ビューのテスト"""
        url = reverse('contract:client_contract_assignment', kwargs={'pk': self.client_contract_draft.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # 割当可能な契約が表示されている
        self.assertContains(response, self.assignable_staff_contract.contract_name)
        # 期間が重複しない契約は表示されない
        self.assertNotContains(response, self.non_overlapping_staff_contract.contract_name)
        # 既に割当済の契約は表示されない
        self.assertNotContains(response, self.already_assigned_staff_contract.contract_name)

    def test_assignment_view_for_non_draft_contract(self):
        """作成中以外の契約で割当一覧ページにアクセスするとリダイレクトされるか"""
        url = reverse('contract:client_contract_assignment', kwargs={'pk': self.client_contract_approved.pk})
        response = self.client.get(url, follow=True)
        # 最終的なURLが詳細ページになっていることを確認
        self.assertRedirects(response, reverse('contract:client_contract_detail', kwargs={'pk': self.client_contract_approved.pk}))
        # エラーメッセージが表示されていることを確認
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'この契約は作成中でないため、割当できません。')

    def test_create_contract_assignment(self):
        """契約アサインの作成テスト"""
        from ..models import ContractAssignment
        from apps.system.logs.models import AppLog

        initial_assignment_count = ContractAssignment.objects.count()
        initial_log_count = AppLog.objects.count()

        url = reverse('contract:create_contract_assignment')
        post_data = {
            'client_contract_id': self.client_contract_draft.pk,
            'staff_contract_id': self.assignable_staff_contract.pk,
            'from': 'client',
        }
        response = self.client.post(url, post_data, follow=True)

        # 詳細ページにリダイレクトされる
        self.assertRedirects(response, reverse('contract:client_contract_detail', kwargs={'pk': self.client_contract_draft.pk}))
        # 成功メッセージ
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), '契約の割当が完了しました。')

        # ContractAssignmentが作成されている
        self.assertEqual(ContractAssignment.objects.count(), initial_assignment_count + 1)
        self.assertTrue(
            ContractAssignment.objects.filter(
                client_contract=self.client_contract_draft,
                staff_contract=self.assignable_staff_contract
            ).exists()
        )
        # AppLogが記録されている（MyModelのシグナルにより自動で1件作成されるはず）
        self.assertEqual(AppLog.objects.count(), initial_log_count + 1)
        log = AppLog.objects.latest('timestamp')
        self.assertEqual(log.model_name, 'ContractAssignment')
        self.assertEqual(log.action, 'create') # 自動作成なのでactionは'create'になる
        self.assertEqual(log.object_id, str(ContractAssignment.objects.latest('pk').pk))

    def test_create_contract_assignment_from_staff(self):
        """スタッフ契約側からの契約アサイン作成テスト"""
        from ..models import ContractAssignment
        from apps.system.logs.models import AppLog

        # アサイン可能なクライアント契約を作成
        assignable_client_contract = ClientContract.objects.create(
            client=self.test_client_model, contract_name='Assignable Client',
            start_date=datetime.date(2025, 7, 1), end_date=datetime.date(2025, 9, 30),
            contract_pattern=self.client_pattern, contract_status=Constants.CONTRACT_STATUS.DRAFT,
            overtime_pattern=self.overtime_pattern,
        )

        initial_assignment_count = ContractAssignment.objects.count()
        initial_log_count = AppLog.objects.count()

        url = reverse('contract:create_contract_assignment')
        post_data = {
            'client_contract_id': assignable_client_contract.pk,
            'staff_contract_id': self.staff_contract_draft.pk,
            'from': 'staff',
        }
        response = self.client.post(url, post_data, follow=True)

        # スタッフ詳細ページにリダイレクトされる
        self.assertRedirects(response, reverse('contract:staff_contract_detail', kwargs={'pk': self.staff_contract_draft.pk}))
        # 成功メッセージ
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), '契約の割当が完了しました。')

        # ContractAssignmentが作成されている
        self.assertEqual(ContractAssignment.objects.count(), initial_assignment_count + 1)
        # AppLogが記録されている
        self.assertEqual(AppLog.objects.count(), initial_log_count + 1)

    def test_delete_contract_assignment_success(self):
        """契約アサインの解除が成功するテスト"""
        from ..models import ContractAssignment
        initial_count = ContractAssignment.objects.count()
        url = reverse('contract:delete_contract_assignment', kwargs={'assignment_pk': self.assignment.pk})
        response = self.client.post(url, follow=True)

        # 詳細ページにリダイレクトされる
        self.assertRedirects(response, reverse('contract:client_contract_detail', kwargs={'pk': self.client_contract_draft.pk}))
        # 成功メッセージ
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), '契約アサインを解除しました。')
        # アサインが削除されている
        self.assertEqual(ContractAssignment.objects.count(), initial_count - 1)

    def test_delete_contract_assignment_fail_for_non_draft(self):
        """作成中以外の契約のアサイン解除が失敗するテスト"""
        from ..models import ContractAssignment
        initial_count = ContractAssignment.objects.count()
        url = reverse('contract:delete_contract_assignment', kwargs={'assignment_pk': self.assignment_approved.pk})
        response = self.client.post(url, follow=True)

        # 詳細ページにリダイレクトされる
        self.assertRedirects(response, reverse('contract:client_contract_detail', kwargs={'pk': self.client_contract_approved.pk}))
        # エラーメッセージ
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertTrue('このアサインは解除できません' in str(messages[0]))
        # アサインは削除されていない
        self.assertEqual(ContractAssignment.objects.count(), initial_count)

    def test_unassign_button_visibility_on_client_detail(self):
        """クライアント契約詳細ページでの解除ボタンの表示テスト"""
        # 作成中の契約 -> ボタン表示
        url_draft = reverse('contract:client_contract_detail', kwargs={'pk': self.client_contract_draft.pk})
        response_draft = self.client.get(url_draft)
        self.assertContains(response_draft, '<button type="submit" class="btn btn-sm btn-dark"')
        self.assertContains(response_draft, '>解除</button>')

        # 承認済みの契約 -> ボタン非表示
        # 承認済み契約に紐づくスタッフ契約のアサインをセットアップ
        self.client_contract_approved.staff_contracts.add(self.staff_contract_draft)
        url_approved = reverse('contract:client_contract_detail', kwargs={'pk': self.client_contract_approved.pk})
        response_approved = self.client.get(url_approved)
        self.assertNotContains(response_approved, '>解除</button>')

    def test_unassign_button_visibility_on_staff_detail(self):
        """スタッフ契約詳細ページでの解除ボタンの表示テスト"""
        # 作成中のクライアント契約に紐づいている -> ボタン表示
        url_draft = reverse('contract:staff_contract_detail', kwargs={'pk': self.already_assigned_staff_contract.pk})
        response_draft = self.client.get(url_draft)
        self.assertContains(response_draft, '<button type="submit" class="btn btn-sm btn-dark"')
        self.assertContains(response_draft, '>解除</button>')

        # 承認済みのクライアント契約に紐づいている -> ボタン非表示
        url_approved = reverse('contract:staff_contract_detail', kwargs={'pk': self.staff_contract_draft.pk})
        response_approved = self.client.get(url_approved)
        self.assertNotContains(response_approved, '>解除</button>')

    def test_create_assignment_business_content_synchronization(self):
        """契約アサイン時に業務内容が同期されるかテスト"""
        # --- シナリオ1: StaffContractからClientContractへ同期 ---
        client_contract_1 = ClientContract.objects.create(
            client=self.test_client_model, contract_name='Client for Sync 1',
            start_date=datetime.date(2025, 1, 1), contract_pattern=self.client_pattern,
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            business_content='', # Empty
            overtime_pattern=self.overtime_pattern,
        )
        staff_contract_1 = StaffContract.objects.create(
            staff=self.staff1, contract_name='Staff for Sync 1',
            start_date=datetime.date(2025, 1, 1), contract_pattern=self.staff_pattern,
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            business_content='Staff content', # Not empty
            overtime_pattern=self.overtime_pattern,
        )

        url = reverse('contract:create_contract_assignment')
        post_data_1 = {
            'client_contract_id': client_contract_1.pk,
            'staff_contract_id': staff_contract_1.pk,
            'from': 'client',
        }
        response_1 = self.client.post(url, post_data_1, follow=True)
        messages_1 = list(response_1.context['messages'])
        self.assertEqual(len(messages_1), 1)
        expected_message_1 = '契約の割当が完了しました。（クライアント契約の業務内容をスタッフ契約の業務内容で更新しました。）'
        self.assertEqual(str(messages_1[0]), expected_message_1)

        client_contract_1.refresh_from_db()
        self.assertEqual(client_contract_1.business_content, 'Staff content')

        # --- シナリオ2: ClientContractからStaffContractへ同期 ---
        client_contract_2 = ClientContract.objects.create(
            client=self.test_client_model, contract_name='Client for Sync 2',
            start_date=datetime.date(2025, 1, 1), contract_pattern=self.client_pattern,
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            business_content='Client content', # Not empty
            overtime_pattern=self.overtime_pattern,
        )
        staff_contract_2 = StaffContract.objects.create(
            staff=self.staff1, contract_name='Staff for Sync 2',
            start_date=datetime.date(2025, 1, 1), contract_pattern=self.staff_pattern,
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            business_content='', # Empty
            overtime_pattern=self.overtime_pattern,
        )

        post_data_2 = {
            'client_contract_id': client_contract_2.pk,
            'staff_contract_id': staff_contract_2.pk,
            'from': 'client',
        }
        response_2 = self.client.post(url, post_data_2, follow=True)
        messages_2 = list(response_2.context['messages'])
        self.assertEqual(len(messages_2), 1)
        expected_message_2 = '契約の割当が完了しました。（スタッフ契約の業務内容をクライアント契約の業務内容で更新しました。）'
        self.assertEqual(str(messages_2[0]), expected_message_2)

        staff_contract_2.refresh_from_db()
        self.assertEqual(staff_contract_2.business_content, 'Client content')

        # --- シナリオ3: 両方入力済みの場合は同期しない ---
        client_contract_3 = ClientContract.objects.create(
            client=self.test_client_model, contract_name='Client for Sync 3',
            start_date=datetime.date(2025, 1, 1), contract_pattern=self.client_pattern,
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            business_content='Original client content',
            overtime_pattern=self.overtime_pattern,
        )
        staff_contract_3 = StaffContract.objects.create(
            staff=self.staff1, contract_name='Staff for Sync 3',
            start_date=datetime.date(2025, 1, 1), contract_pattern=self.staff_pattern,
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            business_content='Original staff content',
            overtime_pattern=self.overtime_pattern,
        )
        post_data_3 = {
            'client_contract_id': client_contract_3.pk,
            'staff_contract_id': staff_contract_3.pk,
            'from': 'client',
        }
        response_3 = self.client.post(url, post_data_3, follow=True)
        messages_3 = list(response_3.context['messages'])
        self.assertEqual(len(messages_3), 1)
        self.assertEqual(str(messages_3[0]), '契約の割当が完了しました。')

        client_contract_3.refresh_from_db()
        staff_contract_3.refresh_from_db()
        self.assertEqual(client_contract_3.business_content, 'Original client content')
        self.assertEqual(staff_contract_3.business_content, 'Original staff content')

        # --- シナリオ4: 両方空の場合は何もしない ---
        client_contract_4 = ClientContract.objects.create(
            client=self.test_client_model, contract_name='Client for Sync 4',
            start_date=datetime.date(2025, 1, 1), contract_pattern=self.client_pattern,
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            business_content='',
            overtime_pattern=self.overtime_pattern,
        )
        staff_contract_4 = StaffContract.objects.create(
            staff=self.staff1, contract_name='Staff for Sync 4',
            start_date=datetime.date(2025, 1, 1), contract_pattern=self.staff_pattern,
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            business_content='',
            overtime_pattern=self.overtime_pattern,
        )
        post_data_4 = {
            'client_contract_id': client_contract_4.pk,
            'staff_contract_id': staff_contract_4.pk,
            'from': 'client',
        }
        response_4 = self.client.post(url, post_data_4, follow=True)
        messages_4 = list(response_4.context['messages'])
        self.assertEqual(len(messages_4), 1)
        self.assertEqual(str(messages_4[0]), '契約の割当が完了しました。')


        client_contract_4.refresh_from_db()
        staff_contract_4.refresh_from_db()
        self.assertEqual(client_contract_4.business_content, '')
        self.assertEqual(staff_contract_4.business_content, '')

    def test_create_assignment_work_location_synchronization(self):
        """契約アサイン時に就業場所が同期されるかテスト"""
        # --- シナリオ1: StaffContractからClientContractHakenへ同期 ---
        client_contract_1 = ClientContract.objects.create(
            client=self.test_client_model, contract_name='Client for Work Location Sync 1',
            start_date=datetime.date(2025, 1, 1), contract_pattern=self.client_pattern,
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            overtime_pattern=self.overtime_pattern,
        )
        haken_info_1 = ClientContractHaken.objects.create(
            client_contract=client_contract_1,
            work_location='' # Empty
        )
        staff_contract_1 = StaffContract.objects.create(
            staff=self.staff1, contract_name='Staff for Work Location Sync 1',
            start_date=datetime.date(2025, 1, 1), contract_pattern=self.staff_pattern,
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            work_location='Staff Work Location', # Not empty
            overtime_pattern=self.overtime_pattern,
        )

        url = reverse('contract:create_contract_assignment')
        post_data_1 = {
            'client_contract_id': client_contract_1.pk,
            'staff_contract_id': staff_contract_1.pk,
            'from': 'client',
        }
        response_1 = self.client.post(url, post_data_1, follow=True)
        messages_1 = list(response_1.context['messages'])
        self.assertEqual(len(messages_1), 1)
        expected_message_1 = '契約の割当が完了しました。（クライアント契約の派遣の就業場所をスタッフ契約の就業場所で更新しました。）'
        self.assertEqual(str(messages_1[0]), expected_message_1)

        haken_info_1.refresh_from_db()
        self.assertEqual(haken_info_1.work_location, 'Staff Work Location')

        # --- シナリオ2: ClientContractHakenからStaffContractへ同期 ---
        client_contract_2 = ClientContract.objects.create(
            client=self.test_client_model, contract_name='Client for Work Location Sync 2',
            start_date=datetime.date(2025, 1, 1), contract_pattern=self.client_pattern,
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            overtime_pattern=self.overtime_pattern,
        )
        haken_info_2 = ClientContractHaken.objects.create(
            client_contract=client_contract_2,
            work_location='Client Work Location' # Not empty
        )
        staff_contract_2 = StaffContract.objects.create(
            staff=self.staff1, contract_name='Staff for Work Location Sync 2',
            start_date=datetime.date(2025, 1, 1), contract_pattern=self.staff_pattern,
            contract_status=Constants.CONTRACT_STATUS.DRAFT,
            work_location='', # Empty
            overtime_pattern=self.overtime_pattern,
        )

        post_data_2 = {
            'client_contract_id': client_contract_2.pk,
            'staff_contract_id': staff_contract_2.pk,
            'from': 'client',
        }
        response_2 = self.client.post(url, post_data_2, follow=True)
        messages_2 = list(response_2.context['messages'])
        self.assertEqual(len(messages_2), 1)
        expected_message_2 = '契約の割当が完了しました。（スタッフ契約の就業場所をクライアント契約の派遣の就業場所で更新しました。）'
        self.assertEqual(str(messages_2[0]), expected_message_2)

        staff_contract_2.refresh_from_db()
        self.assertEqual(staff_contract_2.work_location, 'Client Work Location')

    def test_assignment_permission_denied(self):
        """契約アサイン関連ビューで権限のないユーザーがアクセスできないことをテスト"""
        # 権限のないユーザーを作成
        no_perm_user = User.objects.create_user(
            username='nopermuser_assignment',
            email='noperm_assignment@example.com',
            password='testpass123'
        )
        self.client.login(username='nopermuser_assignment', password='testpass123')

        # --- 割当作成ビュー (add_contractassignment) ---
        create_url = reverse('contract:create_contract_assignment')
        post_data_create = {
            'client_contract_id': self.client_contract_draft.pk,
            'staff_contract_id': self.assignable_staff_contract.pk,
            'from': 'client',
        }
        response_create = self.client.post(create_url, post_data_create)
        self.assertEqual(response_create.status_code, 403)

        # --- 割当確認ビュー (change_contractassignment) ---
        confirm_url_client = reverse('contract:client_assignment_confirm')
        confirm_url_staff = reverse('contract:staff_assignment_confirm')
        post_data_confirm = {
            'client_contract_id': self.client_contract_draft.pk,
            'staff_contract_id': self.assignable_staff_contract.pk,
        }
        response_confirm_client = self.client.post(confirm_url_client, post_data_confirm)
        response_confirm_staff = self.client.post(confirm_url_staff, post_data_confirm)
        self.assertEqual(response_confirm_client.status_code, 403)
        self.assertEqual(response_confirm_staff.status_code, 403)


class ContractAssignmentDisplayTest(TestCase):
    """契約割当状況表示のテスト"""

    def setUp(self):
        """テストデータの準備"""
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        from ..models import ContractAssignment

        # ユーザーと権限
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        content_types = [
            ContentType.objects.get_for_model(ClientContract),
            ContentType.objects.get_for_model(StaffContract),
        ]
        permissions = Permission.objects.filter(content_type__in=content_types)
        self.user.user_permissions.set(permissions)
        self.client.login(username='testuser', password='testpassword')

        # クライアント、スタッフ
        self.test_client_model = TestClient.objects.create(name='Test Client')
        self.staff = Staff.objects.create(name_last='Staff', name_first='One')

        # 契約パターン
        self.client_pattern = ContractPattern.objects.create(name='Client Pattern', domain='10')
        self.staff_pattern = ContractPattern.objects.create(name='Staff Pattern', domain='1')
        from apps.master.models import OvertimePattern
        self.overtime_pattern = OvertimePattern.objects.create(name='標準時間外')

        # --- テストデータ ---
        # 1. 割当済みの契約ペア
        self.assigned_client_contract = ClientContract.objects.create(
            client=self.test_client_model, contract_name='Assigned Client',
            start_date=datetime.date(2025, 1, 1), contract_pattern=self.client_pattern,
            contract_number='C-ASSIGNED',
            overtime_pattern=self.overtime_pattern,
        )
        self.assigned_staff_contract = StaffContract.objects.create(
            staff=self.staff, contract_name='Assigned Staff',
            start_date=datetime.date(2025, 1, 1), contract_pattern=self.staff_pattern,
            contract_number='S-ASSIGNED',
            overtime_pattern=self.overtime_pattern,
        )
        ContractAssignment.objects.create(
            client_contract=self.assigned_client_contract,
            staff_contract=self.assigned_staff_contract
        )

        # 2. 未割当の契約
        self.unassigned_client_contract = ClientContract.objects.create(
            client=self.test_client_model, contract_name='Unassigned Client',
            start_date=datetime.date(2025, 2, 1), contract_pattern=self.client_pattern,
            contract_number='C-UNASSIGNED',
            overtime_pattern=self.overtime_pattern,
        )
        self.unassigned_staff_contract = StaffContract.objects.create(
            staff=self.staff, contract_name='Unassigned Staff',
            start_date=datetime.date(2025, 2, 1), contract_pattern=self.staff_pattern,
            contract_number='S-UNASSIGNED',
            overtime_pattern=self.overtime_pattern,
        )

    def test_client_contract_list_assignment_badge(self):
        """クライアント契約一覧で割当済バッジが正しく表示されるかテスト"""
        url = reverse('contract:client_contract_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # 割当済みの契約にはバッジが表示される
        assigned_row_html = f'<td>\n                                        {self.assigned_client_contract.contract_number}\n                                        \n                                            <span class="badge bg-success ms-1">割当済</span>\n                                        \n                                    </td>'
        self.assertContains(response, '割当済')

        # 未割当の契約にはバッジが表示されない
        unassigned_row_html = f'<td>\n                                        {self.unassigned_client_contract.contract_number}\n                                        \n                                    </td>'
        #レスポンス内容を部分的に確認
        self.assertNotContains(response, f'{self.unassigned_client_contract.contract_number}</span>')


    def test_staff_contract_list_assignment_badge(self):
        """スタッフ契約一覧で割当済バッジが正しく表示されるかテスト"""
        url = reverse('contract:staff_contract_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # 割当済みの契約にはバッジが表示される
        self.assertContains(response, '割当済')

        # 未割当の契約にはバッジが表示されない
        self.assertNotContains(response, f'{self.unassigned_staff_contract.contract_number}</span>')
