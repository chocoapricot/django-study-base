from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.profile.models import StaffBankProfile
from apps.connect.models import ConnectStaff, BankRequest

User = get_user_model()

class BankRequestSignalTest(TestCase):
    def setUp(self):
        # テスト用のユーザーを作成
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='testuser1@example.com',
            password='password'
        )
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='testuser2@example.com',
            password='password'
        )

        # 承認済みの接続を作成
        self.connect_staff1 = ConnectStaff.objects.create(
            corporate_number='1234567890123',
            email=self.user1.email,
            status='approved'
        )
        # 別のユーザーの承認済み接続
        self.connect_staff2 = ConnectStaff.objects.create(
            corporate_number='1234567890124',
            email=self.user2.email,
            status='approved'
        )
        # 未承認の接続
        self.connect_staff_pending = ConnectStaff.objects.create(
            corporate_number='1234567890125',
            email=self.user1.email,
            status='pending'
        )

    def test_request_creation_on_bank_profile_create(self):
        """
        StaffBankProfile作成時にBankRequestが作成されることをテスト
        """
        # StaffBankProfileを作成
        bank_profile = StaffBankProfile.objects.create(
            user=self.user1,
            bank_code='1234',
            branch_code='567',
            account_type='1',
            account_number='1234567',
            account_holder='テスト タロウ'
        )

        # BankRequestが1つ作成されていることを確認
        self.assertEqual(BankRequest.objects.count(), 1)
        request = BankRequest.objects.first()
        self.assertEqual(request.connect_staff, self.connect_staff1)
        self.assertEqual(request.staff_bank_profile, bank_profile)
        self.assertEqual(request.status, 'pending')

    def test_request_recreation_on_bank_profile_update(self):
        """
        StaffBankProfile更新時にBankRequestが再作成されることをテスト
        """
        # 最初にStaffBankProfileを作成
        bank_profile = StaffBankProfile.objects.create(
            user=self.user1,
            bank_code='1234',
            branch_code='567',
            account_type='1',
            account_number='1234567',
            account_holder='テスト タロウ'
        )
        self.assertEqual(BankRequest.objects.count(), 1)
        original_request = BankRequest.objects.first()
        original_request_id = original_request.id

        # StaffBankProfileを更新
        bank_profile.account_number = '7654321'
        bank_profile.save()

        # 古いリクエストが削除され、新しいリクエストが作成されたことを確認
        self.assertFalse(BankRequest.objects.filter(id=original_request_id).exists())
        self.assertEqual(BankRequest.objects.count(), 1)
        updated_request = BankRequest.objects.first()
        self.assertEqual(updated_request.connect_staff, self.connect_staff1)
        self.assertEqual(updated_request.staff_bank_profile, bank_profile)

    def test_no_request_if_no_approved_connection(self):
        """
        承認済みの接続がない場合、BankRequestが作成されないことをテスト
        """
        # 承認済みの接続がないユーザーでStaffBankProfileを作成
        user_no_connection = User.objects.create_user(
            username='nouser', email='nouser@example.com', password='password'
        )
        StaffBankProfile.objects.create(
            user=user_no_connection,
            bank_code='1234',
            branch_code='567',
            account_type='1',
            account_number='1234567',
            account_holder='テスト タロウ'
        )

        # BankRequestが作成されていないことを確認
        self.assertEqual(BankRequest.objects.count(), 0)

    def test_multiple_connections(self):
        """
        一人のユーザーに複数の承認済み接続がある場合のテスト
        """
        # 同じユーザーにもう一つ承認済み接続を追加
        ConnectStaff.objects.create(
            corporate_number='9998887776665',
            email=self.user1.email,
            status='approved'
        )

        # StaffBankProfileを作成
        StaffBankProfile.objects.create(
            user=self.user1,
            bank_code='1234',
            branch_code='567',
            account_type='1',
            account_number='1234567',
            account_holder='テスト タロウ'
        )

        # 2つのBankRequestが作成されていることを確認
        self.assertEqual(BankRequest.objects.count(), 2)
        self.assertEqual(BankRequest.objects.filter(staff_bank_profile__user=self.user1).count(), 2)
