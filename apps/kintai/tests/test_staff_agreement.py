from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date
from apps.kintai.models import StaffTimerecord
from apps.contract.models import StaffContract
from apps.staff.models import Staff
from apps.master.models import EmploymentType, ContractPattern, StaffAgreement
from apps.connect.models import ConnectStaff, ConnectStaffAgree
from apps.common.constants import Constants

User = get_user_model()

class StaffAgreementKintaiTest(TestCase):
    """勤怠機能でのスタッフ同意チェックのテスト"""

    def setUp(self):
        """テストデータの準備"""
        # ユーザー作成
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # スタッフ作成
        self.staff = Staff.objects.create(
            email='test@example.com',
            name_last='テスト',
            name_first='太郎',
            employee_no='EMP001',
            hire_date=date.today()
        )
        
        # 雇用形態作成
        self.employment_type = EmploymentType.objects.create(
            name='正社員'
        )
        
        # 契約パターン作成
        self.contract_pattern = ContractPattern.objects.create(
            name='標準契約',
            employment_type=self.employment_type
        )
        
        # スタッフ契約作成
        self.staff_contract = StaffContract.objects.create(
            staff=self.staff,
            contract_name="テスト契約",
            start_date=timezone.localtime().date(),
            contract_pattern=self.contract_pattern,
            contract_status=Constants.CONTRACT_STATUS.CONFIRMED
        )
        
        # 接続作成
        self.connection = ConnectStaff.objects.create(
            email='test@example.com',
            corporate_number='1234567890123',
            status='approved'
        )
        
        # 同意文言作成
        self.agreement = StaffAgreement.objects.create(
            name='個人情報取得の同意',
            agreement_text='個人情報の取得に同意します。',
            corporation_number='1234567890123',
            is_active=True
        )
        
        self.client = Client()
        self.punch_url = reverse('kintai:timerecord_punch')
        self.list_url = reverse('kintai:timerecord_list')

    def test_punch_with_unagreed_agreement_redirects_to_agreement(self):
        """未同意文言がある場合、打刻画面が同意画面にリダイレクトされることをテスト"""
        self.client.login(username='testuser', password='testpass123')
        
        # 打刻画面にアクセス
        response = self.client.get(self.punch_url)
        
        # 同意画面にリダイレクトされることを確認
        self.assertEqual(response.status_code, 302)
        expected_url = reverse('connect:staff_agree', kwargs={'pk': self.connection.pk})
        self.assertTrue(response.url.startswith(expected_url))
        self.assertIn('next=', response.url)

    def test_punch_with_agreed_agreement_shows_punch_page(self):
        """同意済みの場合、打刻画面が正常に表示されることをテスト"""
        # 同意を記録
        ConnectStaffAgree.objects.create(
            email='test@example.com',
            corporate_number='1234567890123',
            staff_agreement=self.agreement,
            is_agreed=True
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        # 打刻画面にアクセス
        response = self.client.get(self.punch_url)
        
        # 正常に表示されることを確認
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '勤怠打刻')
        # 打刻ボタンが表示されることを確認
        self.assertContains(response, '出勤')
        self.assertContains(response, '退勤')
        # 時計表示が表示されることを確認
        self.assertContains(response, 'id="current-time"')
        self.assertContains(response, 'clock-date')

    def test_no_contract_hides_punch_buttons(self):
        """契約がない場合、打刻ボタンが非表示になることをテスト"""
        # 同意を記録
        ConnectStaffAgree.objects.create(
            email='test@example.com',
            corporate_number='1234567890123',
            staff_agreement=self.agreement,
            is_agreed=True
        )
        
        # 契約を削除
        self.staff_contract.delete()
        
        self.client.login(username='testuser', password='testpass123')
        
        # 打刻画面にアクセス
        response = self.client.get(self.punch_url)
        
        # 正常に表示されることを確認
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '勤怠打刻')
        # 契約がない旨のメッセージが表示されることを確認
        self.assertContains(response, '有効で確認済みのスタッフ契約がありません')
        # 打刻ボタンが非表示になることを確認
        self.assertNotContains(response, 'name="action" value="start"')
        self.assertNotContains(response, 'name="action" value="end"')
        # 時計表示が非表示になることを確認（実際のHTML要素をチェック）
        self.assertNotContains(response, 'id="current-time"')
        self.assertNotContains(response, 'class="clock-date mb-1"')

    def test_timerecord_list_with_unagreed_agreement_redirects(self):
        """未同意文言がある場合、勤怠一覧画面が同意画面にリダイレクトされることをテスト"""
        self.client.login(username='testuser', password='testpass123')
        
        # 勤怠一覧画面にアクセス
        response = self.client.get(self.list_url)
        
        # 同意画面にリダイレクトされることを確認
        self.assertEqual(response.status_code, 302)
        expected_url = reverse('connect:staff_agree', kwargs={'pk': self.connection.pk})
        self.assertTrue(response.url.startswith(expected_url))

    def test_timerecord_list_with_agreed_agreement_shows_list(self):
        """同意済みの場合、勤怠一覧画面が正常に表示されることをテスト"""
        # 同意を記録
        ConnectStaffAgree.objects.create(
            email='test@example.com',
            corporate_number='1234567890123',
            staff_agreement=self.agreement,
            is_agreed=True
        )
        
        self.client.login(username='testuser', password='testpass123')
        
        # 勤怠一覧画面にアクセス
        response = self.client.get(self.list_url)
        
        # 正常に表示されることを確認
        self.assertEqual(response.status_code, 200)

    def test_no_connection_allows_access(self):
        """接続がない場合はアクセスが許可されることをテスト"""
        # 接続を削除
        self.connection.delete()
        
        self.client.login(username='testuser', password='testpass123')
        
        # 打刻画面にアクセス
        response = self.client.get(self.punch_url)
        
        # 正常に表示されることを確認（接続がないため同意チェックはスキップ）
        self.assertEqual(response.status_code, 200)

    def test_staff_user_bypasses_agreement_check(self):
        """is_staffユーザーは同意チェックをバイパスすることをテスト"""
        # ユーザーをスタッフに設定
        self.user.is_staff = True
        self.user.save()
        
        self.client.login(username='testuser', password='testpass123')
        
        # 打刻画面にアクセス
        response = self.client.get(self.punch_url)
        
        # 正常に表示されることを確認（スタッフユーザーは同意チェックをバイパス）
        self.assertEqual(response.status_code, 200)

    def test_inactive_agreement_does_not_block_access(self):
        """非アクティブな同意文言はアクセスをブロックしないことをテスト"""
        # 同意文言を非アクティブに設定
        self.agreement.is_active = False
        self.agreement.save()
        
        self.client.login(username='testuser', password='testpass123')
        
        # 打刻画面にアクセス
        response = self.client.get(self.punch_url)
        
        # 正常に表示されることを確認（非アクティブな同意文言は無視される）
        self.assertEqual(response.status_code, 200)