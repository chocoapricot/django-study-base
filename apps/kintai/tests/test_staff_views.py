from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from datetime import date, datetime
from apps.staff.models import Staff
from apps.contract.models import StaffContract
from apps.kintai.models import StaffTimesheet, StaffTimecard
from apps.master.models import EmploymentType, ContractPattern
from apps.common.constants import Constants

User = get_user_model()


class StaffViewsTest(TestCase):
    """スタッフ向けビューのテストケース"""
    
    def setUp(self):
        """テストデータのセットアップ"""
        # ユーザーを作成
        self.user = User.objects.create_user(
            username='test_staff',
            email='test@staff.jp',
            password='testpass123'
        )
        
        # スタッフを作成
        self.staff = Staff.objects.create(
            name_last='テスト',
            name_first='太郎',
            name_kana_last='テスト',
            name_kana_first='タロウ',
            email='test@staff.jp',
            hire_date=date(2024, 1, 1),
            employee_no='TEST001'
        )
        
        # 雇用形態を作成
        self.employment_type = EmploymentType.objects.create(
            name='正社員',
            display_order=1
        )
        
        # 契約パターンを作成
        self.contract_pattern = ContractPattern.objects.create(
            name='標準契約',
            domain=Constants.DOMAIN.STAFF
        )
        
        # スタッフ契約を作成
        self.staff_contract = StaffContract.objects.create(
            staff=self.staff,
            employment_type=self.employment_type,
            contract_name='テスト契約',
            contract_pattern=self.contract_pattern,
            start_date=date(2020, 1, 1),  # 長期間有効な契約
            end_date=date(2030, 12, 31),   # 長期間有効な契約
            contract_status=Constants.CONTRACT_STATUS.CONFIRMED
        )
        
        # テスト用クライアントを作成
        self.test_client = Client()
        

        

        

        
    def test_staff_timecard_register_requires_login(self):
        """タイムカード登録はログインが必要"""
        response = self.test_client.get(reverse('kintai:staff_timecard_register'))
        self.assertEqual(response.status_code, 302)  # リダイレクト
        
    def test_staff_timecard_register_with_valid_staff(self):
        """有効なスタッフでタイムカード登録画面にアクセス"""
        self.test_client.login(username='test_staff', password='testpass123')
        response = self.test_client.get(reverse('kintai:staff_timecard_register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'タイムカード登録')
        self.assertContains(response, 'テスト契約')
        
    def test_staff_timecard_register_with_target_month(self):
        """特定の年月でタイムカード登録画面にアクセス"""
        self.test_client.login(username='test_staff', password='testpass123')
        response = self.test_client.get(
            reverse('kintai:staff_timecard_register') + '?target_month=2024-06'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '2024年6月')
        
    def test_staff_timecard_register_detail_creates_timesheet(self):
        """詳細登録画面で月次勤怠が作成される"""
        self.test_client.login(username='test_staff', password='testpass123')
        
        # 月次勤怠が存在しないことを確認
        self.assertFalse(
            StaffTimesheet.objects.filter(
                staff_contract=self.staff_contract,
                target_month=date(2024, 6, 1)
            ).exists()
        )
        
        # 詳細登録画面にアクセス
        response = self.test_client.get(
            reverse('kintai:staff_timecard_register_detail', 
                   kwargs={'contract_pk': self.staff_contract.pk, 'target_month': '2024-06'})
        )
        
        # カレンダー画面にリダイレクトされることを確認
        self.assertEqual(response.status_code, 302)
        
        # 月次勤怠が作成されたことを確認
        timesheet = StaffTimesheet.objects.get(
            staff_contract=self.staff_contract,
            target_month=date(2024, 6, 1)
        )
        self.assertEqual(timesheet.staff, self.staff)
        
    def test_staff_timecard_register_detail_invalid_contract(self):
        """他人の契約にはアクセスできない"""
        # 別のスタッフと契約を作成
        other_staff = Staff.objects.create(
            name_last='他の',
            name_first='スタッフ',
            name_kana_last='ホカノ',
            name_kana_first='スタッフ',
            email='other@staff.jp',
            employee_no='OTHER001'
        )
        other_contract = StaffContract.objects.create(
            staff=other_staff,
            employment_type=self.employment_type,
            contract_name='他の契約',
            contract_pattern=self.contract_pattern,
            start_date=date(2024, 1, 1)
        )
        
        self.test_client.login(username='test_staff', password='testpass123')
        response = self.test_client.get(
            reverse('kintai:staff_timecard_register_detail', 
                   kwargs={'contract_pk': other_contract.pk, 'target_month': '2024-06'})
        )
        
        # 404エラーになることを確認
        self.assertEqual(response.status_code, 404)
        
    def test_staff_timecard_register_detail_invalid_month_format(self):
        """無効な年月形式の場合はリダイレクト"""
        self.test_client.login(username='test_staff', password='testpass123')
        response = self.test_client.get(
            reverse('kintai:staff_timecard_register_detail', 
                   kwargs={'contract_pk': self.staff_contract.pk, 'target_month': 'invalid'})
        )
        
        # タイムカード登録画面にリダイレクトされることを確認
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith(reverse('kintai:staff_timecard_register')))
        
    def test_contract_status_display(self):
        """契約の入力状況が正しく表示される"""
        self.test_client.login(username='test_staff', password='testpass123')
        
        # 月次勤怠を作成
        timesheet = StaffTimesheet.objects.create(
            staff_contract=self.staff_contract,
            staff=self.staff,
            target_month=date(2024, 6, 1)
        )
        
        # 日次勤怠を一部作成（入力中状態）
        StaffTimecard.objects.create(
            timesheet=timesheet,
            staff_contract=self.staff_contract,
            work_date=date(2024, 6, 1),
            work_type='10'  # 出勤
        )
        
        response = self.test_client.get(
            reverse('kintai:staff_timecard_register') + '?target_month=2024-06'
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '入力中')  # ステータスが表示される