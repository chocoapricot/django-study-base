from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.connect.models import ConnectStaff, ProfileRequest
from apps.staff.models import Staff
from apps.profile.models import StaffProfile

User = get_user_model()


class ConnectStaffProfileRequestTest(TestCase):
    """ConnectStaffモデルのプロフィール申請ロジックのテスト"""

    def setUp(self):
        self.approver = User.objects.create_user(
            username='approver',
            email='approver@example.com',
            password='TestPass123!'
        )
        self.staff_user = User.objects.create_user(
            username='staffuser',
            email='staff@example.com',
            password='TestPass123!'
        )
        self.staff = Staff.objects.create(
            email='staff@example.com',
            name_last='山田',
            name_first='太郎',
            name_kana_last='ヤマダ',
            name_kana_first='タロウ',
            birth_date=date(1990, 1, 1),
            sex=1, # IntegerField
            postal_code='1000001',
            address1='東京都',
            address2='千代田区',
            address3='丸の内1-1',
            phone='09012345678',
        )
        self.connection = ConnectStaff.objects.create(
            corporate_number='1234567890123',
            email='staff@example.com',
        )

    def test_profile_request_not_created_if_profile_does_not_exist(self):
        """プロフィールが存在しない場合にプロフィール申請が作成されないこと"""
        self.connection.approve(self.approver)
        self.assertFalse(
            ProfileRequest.objects.filter(connect_staff=self.connection).exists()
        )

    def test_profile_request_created_if_profile_is_different(self):
        """プロフィールが異なる場合にプロフィール申請が作成されること"""
        StaffProfile.objects.create(
            user=self.staff_user,
            name_last='山田',
            name_first='太郎',
            name_kana_last='ヤマダ',
            name_kana_first='タロウ',
            birth_date=date(1990, 1, 1),
            sex='1', # CharField
            postal_code='1000001',
            address1='東京都',
            address2='千代田区',
            address3='丸の内1-2',  # 住所が異なる
            phone='09012345678',
        )
        self.connection.approve(self.approver)
        self.assertTrue(
            ProfileRequest.objects.filter(connect_staff=self.connection).exists()
        )

    def test_profile_request_not_created_if_profile_is_same(self):
        """プロフィールが一致する場合にプロフィール申請が作成されないこと"""
        StaffProfile.objects.create(
            user=self.staff_user,
            name_last='山田',
            name_first='太郎',
            name_kana_last='ヤマダ',
            name_kana_first='タロウ',
            birth_date=date(1990, 1, 1),
            sex='1', # CharField
            postal_code='1000001',
            address1='東京都',
            address2='千代田区',
            address3='丸の内1-1',
            phone='09012345678',
        )
        self.connection.approve(self.approver)
        self.assertFalse(
            ProfileRequest.objects.filter(connect_staff=self.connection).exists()
        )

    def test_profile_request_deleted_on_unapprove(self):
        """未承認に戻した際にプロフィール申請が削除されること"""
        # プロフィールに差分がある状態で承認し、申請が作成されることを確認
        StaffProfile.objects.create(
            user=self.staff_user,
            name_last='山田',
            name_first='次郎',  # Staffと名前が違う
            name_kana_last='ヤマダ',
            name_kana_first='ジロウ',
            birth_date=date(1990, 1, 1),
            sex='1', # CharField
            postal_code='1000001',
            address1='東京都',
            address2='千代田区',
            address3='丸の内1-1',
            phone='09012345678',
        )
        self.connection.approve(self.approver)
        self.assertTrue(
            ProfileRequest.objects.filter(connect_staff=self.connection).exists()
        )

        # 未承認に戻す
        self.connection.unapprove()
        self.assertFalse(
            ProfileRequest.objects.filter(connect_staff=self.connection).exists()
        )