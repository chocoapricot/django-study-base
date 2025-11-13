from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.messages import get_messages
from ..models import ClientContract, StaffContract, ClientContractHaken, ClientContractTtp
from apps.client.models import Client as TestClient, ClientUser, ClientDepartment
from apps.staff.models import Staff
from apps.master.models import ContractPattern, DefaultValue
from apps.master.models_worktime import WorkTimePattern
from apps.common.constants import Constants
import datetime
from unittest.mock import patch


User = get_user_model()


class StaffContractViewTest(TestCase):
    """スタッフ契約ビューのテスト"""

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
        content_type_staff = ContentType.objects.get_for_model(StaffContract)
        staff_permissions = Permission.objects.filter(content_type=content_type_staff)
        all_permissions.extend(staff_permissions)

        self.user.user_permissions.set(all_permissions)

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
        
        # 就業時間パターン作成
        self.worktime_pattern = WorkTimePattern.objects.create(
            name='標準勤務',
            is_active=True
        )
        
        # 時間外算出パターン作成
        from apps.master.models import OvertimePattern
        self.overtime_pattern = OvertimePattern.objects.create(
            name='標準時間外',
            is_active=True
        )

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

    def test_staff_contract_list_view(self):
        """スタッフ契約一覧ビューのテスト"""
        response = self.client.get(reverse('contract:staff_contract_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'スタッフ契約一覧')

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
            contract_status=Constants.CONTRACT_STATUS.APPROVED,
            contract_pattern=staff_pattern
        )
        self.assertEqual(StaffContractPrint.objects.count(), 0)
        response = self.client.get(reverse('contract:staff_contract_pdf', kwargs={'pk': staff_contract.pk}))
        self.assertEqual(response.status_code, 200)

        # ステータスが発行済に変わっていることを確認
        staff_contract.refresh_from_db()
        self.assertEqual(staff_contract.contract_status, Constants.CONTRACT_STATUS.ISSUED)

        # 発行履歴が作成されていることを確認
        self.assertEqual(StaffContractPrint.objects.count(), 1)
        print_history = StaffContractPrint.objects.first()
        self.assertEqual(print_history.staff_contract, staff_contract)
        self.assertEqual(print_history.printed_by, self.user)

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

    def test_staff_contract_create_initial_name_from_master(self):
        """スタッフ契約作成画面で、契約名がマスタから初期設定されるかテスト"""
        # 1. DefaultValueマスタにテストデータを登録
        default_name = '雇用契約'
        DefaultValue.objects.create(
            pk='StaffContract.contract_name',
            target_item='スタッフ契約＞契約名',
            value=default_name
        )

        # 2. スタッフ契約作成画面にGETリクエスト
        url = reverse('contract:staff_contract_create')
        response = self.client.get(url)

        # 3. レスポンスを検証
        self.assertEqual(response.status_code, 200)
        form = response.context.get('form')
        self.assertIsNotNone(form)

        # フォームの初期値が正しく設定されていることを確認
        self.assertEqual(form.initial.get('contract_name'), default_name)

    def test_staff_contract_create_copy_does_not_use_master_default(self):
        """スタッフ契約コピー作成画面では、契約名がマスタの初期値で上書きされないことをテスト"""
        # 1. DefaultValueマスタにテストデータを登録
        default_name = '雇用契約'
        DefaultValue.objects.create(
            pk='StaffContract.contract_name',
            target_item='スタッフ契約＞契約名',
            value=default_name
        )

        # 2. コピー元の契約を作成
        original_contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name='Original Name',
            start_date=datetime.date.today(),
            contract_pattern=self.staff_pattern,
        )

        # 3. スタッフ契約作成画面にコピー用のGETリクエスト
        url = reverse('contract:staff_contract_create') + f'?copy_from={original_contract.pk}'
        response = self.client.get(url)

        # 4. レスポンスを検証
        self.assertEqual(response.status_code, 200)
        form = response.context.get('form')
        self.assertIsNotNone(form)

        # フォームの初期値がコピー元の情報になっていることを確認
        self.assertEqual(form.initial.get('contract_name'), 'Original Nameのコピー')
        self.assertNotEqual(form.initial.get('contract_name'), default_name)

    def test_staff_contract_create_view_with_new_fields(self):
        """スタッフ契約作成ビューで新しいフィールドが保存されるかテスト"""
        url = reverse('contract:staff_contract_create')
        post_data = {
            'staff': self.staff.pk,
            'contract_name': 'Create View Test Contract',
            'start_date': datetime.date(2024, 4, 1),
            'end_date': datetime.date(2024, 12, 31),
            'contract_pattern': self.staff_pattern.pk,
            'pay_unit': self.pay_unit_daily.value,
            'work_location': '本社ビル',
            'business_content': 'プログラミング業務',
            'worktime_pattern': self.worktime_pattern.pk,
            'overtime_pattern': self.overtime_pattern.pk,
        }
        response = self.client.post(url, post_data)

        # リダイレクトを確認
        self.assertEqual(response.status_code, 302)

        # 契約が作成され、値が正しいか確認
        new_contract = StaffContract.objects.get(contract_name='Create View Test Contract')
        self.assertEqual(new_contract.work_location, '本社ビル')
        self.assertEqual(new_contract.business_content, 'プログラミング業務')

    def test_staff_contract_update_view_with_new_fields(self):
        """スタッフ契約更新ビューで新しいフィールドが保存されるかテスト"""
        # テスト用の契約を作成
        staff_contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name='Update View Test Contract',
            start_date=datetime.date(2024, 4, 1),
            contract_pattern=self.staff_pattern,
            work_location='旧就業場所',
            business_content='旧業務内容',
            worktime_pattern=self.worktime_pattern,
            overtime_pattern=self.overtime_pattern,
        )

        url = reverse('contract:staff_contract_update', kwargs={'pk': staff_contract.pk})
        post_data = {
            'staff': self.staff.pk,
            'contract_name': 'Update View Test Contract', # 必須フィールド
            'start_date': datetime.date(2024, 4, 1), # 必須フィールド
            'end_date': datetime.date(2024, 12, 31), # 必須フィールド
            'contract_pattern': self.staff_pattern.pk, # 必須フィールド
            'pay_unit': self.pay_unit_daily.value, # 必須フィールド
            'work_location': '新就業場所',
            'business_content': '新業務内容',
            'worktime_pattern': self.worktime_pattern.pk,
            'overtime_pattern': self.overtime_pattern.pk,
        }

        response = self.client.post(url, post_data)

        # リダイレクトを確認
        self.assertEqual(response.status_code, 302)

        # 契約が更新され、値が正しいか確認
        staff_contract.refresh_from_db()
        self.assertEqual(staff_contract.work_location, '新就業場所')
        self.assertEqual(staff_contract.business_content, '新業務内容')

class StaffContractIssueHistoryViewTest(TestCase):
    """スタッフ契約発行履歴ビューのテスト"""

    def setUp(self):
        """テストデータの準備"""
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        from apps.company.models import Company
        from ..models import StaffContractPrint

        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='testuser@example.com'
        )
        content_type = ContentType.objects.get_for_model(StaffContract)
        permissions = Permission.objects.filter(content_type=content_type)
        self.user.user_permissions.set(permissions)

        self.client.login(username='testuser', password='testpass123')

        self.company = Company.objects.create(name='Test Company', corporate_number='1112223334445')
        self.staff = Staff.objects.create(name_last='Test', name_first='Staff')
        self.contract_pattern = ContractPattern.objects.create(name='Test Pattern', domain='1')

        # 10件以上の発行履歴を持つ契約
        self.contract_many = StaffContract.objects.create(
            staff=self.staff,
            contract_name='Many Prints Contract',
            start_date=datetime.date.today(),
            contract_pattern=self.contract_pattern,
        )
        for i in range(12):
            StaffContractPrint.objects.create(
                staff_contract=self.contract_many,
                printed_by=self.user,
                document_title=f'Document {i+1}'
            )

        # 10件未満の発行履歴を持つ契約
        self.contract_few = StaffContract.objects.create(
            staff=self.staff,
            contract_name='Few Prints Contract',
            start_date=datetime.date.today(),
            contract_pattern=self.contract_pattern,
        )
        for i in range(5):
            StaffContractPrint.objects.create(
                staff_contract=self.contract_few,
                printed_by=self.user,
                document_title=f'Doc {i+1}'
            )

        # 発行履歴が0件の契約
        self.contract_zero = StaffContract.objects.create(
            staff=self.staff,
            contract_name='Zero Prints Contract',
            start_date=datetime.date.today(),
            contract_pattern=self.contract_pattern,
        )

    def test_detail_view_history_limit(self):
        """詳細ページで発行履歴が10件に制限されることをテスト"""
        url = reverse('contract:staff_contract_detail', kwargs={'pk': self.contract_many.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['issue_history_for_display']), 10)
        self.assertEqual(response.context['issue_history_count'], 12)
        self.assertContains(response, '全て表示')

    def test_detail_view_history_less_than_limit(self):
        """詳細ページで発行履歴が10件未満の場合のテスト"""
        url = reverse('contract:staff_contract_detail', kwargs={'pk': self.contract_few.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['issue_history_for_display']), 5)
        self.assertEqual(response.context['issue_history_count'], 5)
        self.assertContains(response, '全て表示')

    def test_detail_view_no_history_hides_card(self):
        """詳細ページで発行履歴が0件の場合、発行履歴カードが表示されないことをテスト"""
        url = reverse('contract:staff_contract_detail', kwargs={'pk': self.contract_zero.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['issue_history_count'], 0)
        # 発行履歴が0件なので、カードのテーブルヘッダが表示されないことを確認
        # コメントに「発行履歴」が含まれているため、より具体的な要素でチェック
        self.assertNotContains(response, '<th>発行日時</th>', html=True)

    def test_issue_history_list_view_and_pagination(self):
        """発行履歴一覧ページとページネーションをテスト"""
        from ..models import StaffContractPrint
        from django.utils import timezone
        from datetime import timedelta

        StaffContractPrint.objects.filter(staff_contract=self.contract_many).delete()

        base_time = timezone.now()
        for i in range(25):
            StaffContractPrint.objects.create(
                staff_contract=self.contract_many,
                printed_by=self.user,
                document_title=f'Document {i + 1}',
                printed_at=base_time - timedelta(days=i)
            )

        url = reverse('contract:staff_contract_issue_history_list', kwargs={'pk': self.contract_many.pk})

        # 1ページ目
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['page_obj'].object_list), 20)
        self.assertContains(response, 'Document 25')
        self.assertNotContains(response, 'Document 5')

        # 2ページ目
        response = self.client.get(url, {'page': 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['page_obj'].object_list), 5)
        self.assertContains(response, 'Document 5')
        self.assertContains(response, 'Document 1')
        self.assertNotContains(response, 'Document 6')


class StaffContractApproveViewTest(TestCase):
    """スタッフ契約承認ビューのテスト"""

    def setUp(self):
        """テストデータの準備"""
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        from apps.master.models import MinimumPay
        from apps.system.settings.models import Dropdowns

        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='testuser@example.com'
        )
        content_type = ContentType.objects.get_for_model(StaffContract)
        permissions = Permission.objects.filter(content_type=content_type)
        self.user.user_permissions.set(permissions)

        self.client.login(username='testuser', password='testpass123')

        self.staff = Staff.objects.create(name_last='Test', name_first='Staff', employee_no='S001', hire_date=datetime.date(2023, 1, 1))
        self.contract_pattern = ContractPattern.objects.create(name='Test Pattern', domain='1')

        # 最低賃金と都道府県のマスターデータ
        self.tokyo_pref = Dropdowns.objects.create(category='pref', value='13', name='東京都', active=True)
        self.pay_unit_hourly = Dropdowns.objects.create(category='pay_unit', value='10', name='時給', active=True)
        MinimumPay.objects.create(pref='13', start_date=datetime.date(2023, 10, 1), hourly_wage=1113, is_active=True)

        # 最低賃金以上の契約（申請中）
        self.valid_contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name='Valid Wage Contract',
            start_date=datetime.date(2024, 1, 1),
            contract_pattern=self.contract_pattern,
            contract_status=Constants.CONTRACT_STATUS.PENDING,
            pay_unit='10',
            contract_amount=1200,
            work_location='東京都'
        )

        # 最低賃金未満の契約（申請中）
        self.invalid_contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name='Invalid Wage Contract',
            start_date=datetime.date(2024, 1, 1),
            contract_pattern=self.contract_pattern,
            contract_status=Constants.CONTRACT_STATUS.PENDING,
            pay_unit='10',
            contract_amount=1000,
            work_location='東京都'
        )

    @patch('apps.contract.views.generate_staff_contract_number', return_value='SC-TEST-001')
    def test_approve_success_with_valid_wage(self, mock_generate_number):
        """最低賃金以上の契約が正常に承認されるかテスト"""
        url = reverse('contract:staff_contract_approve', kwargs={'pk': self.valid_contract.pk})
        response = self.client.post(url, {'is_approved': 'true'}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.valid_contract.refresh_from_db()
        self.assertEqual(self.valid_contract.contract_status, Constants.CONTRACT_STATUS.APPROVED)

        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertIn('承認済にしました', str(messages[0]))

    def test_approve_failure_with_invalid_wage(self):
        """最低賃金未満の契約が承認されないかテスト"""
        url = reverse('contract:staff_contract_approve', kwargs={'pk': self.invalid_contract.pk})
        response = self.client.post(url, {'is_approved': 'true'}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.invalid_contract.refresh_from_db()
        self.assertEqual(self.invalid_contract.contract_status, Constants.CONTRACT_STATUS.PENDING)

        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertIn('承認できませんでした', str(messages[0]))
        self.assertIn('最低賃金（1113円）を下回っています', str(messages[0]))
