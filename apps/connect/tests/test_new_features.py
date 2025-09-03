from datetime import date
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.company.models import Company
from apps.connect.models import (
    ConnectStaff,
    ConnectStaffAgree,
    ProfileRequest,
    BankRequest,
    DisabilityRequest,
    ConnectInternationalRequest,
)
from apps.staff.models import Staff, StaffBank, StaffDisability, StaffInternational
from apps.master.models import StaffAgreement
from apps.profile.models import (
    StaffProfile,
    StaffProfileBank,
    StaffProfileDisability,
    StaffProfileInternational,
)

User = get_user_model()


class ConnectFeaturesTest(TestCase):
    """
    ConnectStaffモデルの申請ロジックのテスト
    """

    def setUp(self):
        self.approver = User.objects.create_user(
            username="approver", email="approver@example.com", password="TestPass123!"
        )
        self.staff_user = User.objects.create_user(
            username="staffuser", email="staff@example.com", password="TestPass123!"
        )
        self.company = Company.objects.create(
            corporate_number="1234567890123", name="Test Company"
        )
        self.staff = Staff.objects.create(
            email="staff@example.com",
            name_last="山田",
            name_first="太郎",
            name_kana_last="ヤマダ",
            name_kana_first="タロウ",
            birth_date=date(1990, 1, 1),
            sex=1,
            postal_code="1000001",
            address1="東京都",
            address2="千代田区",
            address3="丸の内1-1",
            phone="09012345678",
        )
        self.connection = ConnectStaff.objects.create(
            corporate_number=self.company.corporate_number, email="staff@example.com"
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
            name_last="山田",
            name_first="太郎",
            name_kana_last="ヤマダ",
            name_kana_first="タロウ",
            birth_date=date(1990, 1, 1),
            sex=1,
            postal_code="1000001",
            address1="東京都",
            address2="千代田区",
            address3="丸の内1-2",  # 住所が異なる
            phone="09012345678",
        )
        self.connection.approve(self.approver)
        self.assertTrue(
            ProfileRequest.objects.filter(connect_staff=self.connection).exists()
        )

    def test_profile_request_not_created_if_profile_is_same(self):
        """プロフィールが一致する場合にプロフィール申請が作成されないこと"""
        StaffProfile.objects.create(
            user=self.staff_user,
            name_last="山田",
            name_first="太郎",
            name_kana_last="ヤマダ",
            name_kana_first="タロウ",
            birth_date=date(1990, 1, 1),
            sex=1,
            postal_code="1000001",
            address1="東京都",
            address2="千代田区",
            address3="丸の内1-1",
            phone="09012345678",
        )
        self.connection.approve(self.approver)
        self.assertFalse(
            ProfileRequest.objects.filter(connect_staff=self.connection).exists()
        )

    def test_profile_request_deleted_on_unapprove(self):
        """未承認に戻した際にプロフィール申請が削除されること"""
        StaffProfile.objects.create(
            user=self.staff_user,
            name_last="山田",
            name_first="次郎",
            name_kana_last="ヤマダ",
            name_kana_first="ジロウ",
            birth_date=date(1990, 1, 1),
            sex=1,
            postal_code="1000001",
            address1="東京都",
            address2="千代田区",
            address3="丸の内1-1",
            phone="09012345678",
        )
        self.connection.approve(self.approver)
        self.assertTrue(
            ProfileRequest.objects.filter(connect_staff=self.connection).exists()
        )
        self.connection.unapprove()
        self.assertFalse(
            ProfileRequest.objects.filter(connect_staff=self.connection).exists()
        )

    def test_bank_request_created_on_approval_if_different(self):
        """銀行情報が異なる場合、接続承認時にBankRequestが作成されることをテスト"""
        StaffProfileBank.objects.create(
            user=self.staff_user,
            bank_code="1111",
            branch_code="111",
            account_type="普通",
            account_number="1234567",
            account_holder="テスト タロウ",
        )
        StaffBank.objects.create(
            staff=self.staff,
            bank_code="2222",
            branch_code="222",
            account_type="普通",
            account_number="7654321",
            account_holder="テスト ジロウ",
        )
        self.connection.approve(self.approver)
        self.assertTrue(
            BankRequest.objects.filter(connect_staff=self.connection).exists()
        )

    def test_bank_request_not_created_on_approval_if_same(self):
        """銀行情報が同じ場合、接続承認時にBankRequestが作成されないことをテスト"""
        StaffProfileBank.objects.create(
            user=self.staff_user,
            bank_code="1111",
            branch_code="111",
            account_type="普通",
            account_number="1234567",
            account_holder="テスト タロウ",
        )
        StaffBank.objects.create(
            staff=self.staff,
            bank_code="1111",
            branch_code="111",
            account_type="普通",
            account_number="1234567",
            account_holder="テスト タロウ",
        )
        self.connection.approve(self.approver)
        self.assertFalse(
            BankRequest.objects.filter(connect_staff=self.connection).exists()
        )

    def test_disability_request_created_on_approval_if_different(self):
        """障害者情報が異なる場合、接続承認時にDisabilityRequestが作成されることをテスト"""
        StaffProfileDisability.objects.create(
            user=self.staff_user, disability_type="身体障害", disability_grade="1級"
        )
        StaffDisability.objects.create(
            staff=self.staff, disability_type="精神障害", disability_grade="2級"
        )
        self.connection.approve(self.approver)
        self.assertTrue(
            DisabilityRequest.objects.filter(connect_staff=self.connection).exists()
        )

    def test_disability_request_not_created_on_approval_if_same(self):
        """障害者情報が同じ場合、接続承認時にDisabilityRequestが作成されないことをテスト"""
        StaffProfileDisability.objects.create(
            user=self.staff_user, disability_type="身体障害", disability_grade="1級"
        )
        StaffDisability.objects.create(
            staff=self.staff, disability_type="身体障害", disability_grade="1級"
        )
        self.connection.approve(self.approver)
        self.assertFalse(
            DisabilityRequest.objects.filter(connect_staff=self.connection).exists()
        )

    def test_international_request_created_on_approval_if_different(self):
        """外国籍情報が異なる場合、接続承認時にConnectInternationalRequestが作成されることをテスト"""
        StaffProfileInternational.objects.create(
            user=self.staff_user,
            residence_card_number="AB12345678CD",
            residence_status="永住者",
            residence_period_from="2020-01-01",
            residence_period_to="2030-01-01",
        )
        StaffInternational.objects.create(
            staff=self.staff,
            residence_card_number="XY98765432ZW",
            residence_status="定住者",
            residence_period_from="2021-01-01",
            residence_period_to="2031-01-01",
        )
        self.connection.approve(self.approver)
        self.assertTrue(
            ConnectInternationalRequest.objects.filter(
                connect_staff=self.connection
            ).exists()
        )

    def test_international_request_not_created_on_approval_if_same(self):
        """外国籍情報が同じ場合、接続承認時にConnectInternationalRequestが作成されないことをテスト"""
        StaffProfileInternational.objects.create(
            user=self.staff_user,
            residence_card_number="AB12345678CD",
            residence_status="永住者",
            residence_period_from="2020-01-01",
            residence_period_to="2030-01-01",
        )
        StaffInternational.objects.create(
            staff=self.staff,
            residence_card_number="AB12345678CD",
            residence_status="永住者",
            residence_period_from="2020-01-01",
            residence_period_to="2030-01-01",
        )
        self.connection.approve(self.approver)
        self.assertFalse(
            ConnectInternationalRequest.objects.filter(
                connect_staff=self.connection
            ).exists()
        )


class StaffAgreementConsentTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.company_user = self._create_user(
            email="company@example.com",
            is_staff=True,
            is_active=True
        )
        self.staff_user = self._create_user(
            email="staff@example.com",
            is_staff=False,
            is_active=True
        )
        self.company = self._create_company()
        self.staff = self._create_staff(self.staff_user, self.company)

    def _create_user(self, email, is_staff, is_active):
        User = get_user_model()
        # The 'username' field is required. Use email as username.
        return User.objects.create_user(
            username=email,
            email=email,
            password="password",
            is_staff=is_staff,
            is_active=is_active
        )

    def _create_company(self):
        return Company.objects.create(
            name="Test Company",
            corporate_number="1234567890123"
        )

    def _create_staff(self, user, company):
        staff = Staff.objects.create(
            email=user.email,
            name="Test Staff",
        )
        staff.user = user
        staff.company = company
        staff.save()
        return staff

    def test_redirect_to_consent_if_unagreed_exists(self):
        """未同意の同意書がある場合、同意画面にリダイレクトされる"""
        self.client.login(email='company@example.com', password='password')
        agreement = StaffAgreement.objects.create(
            corporation_number=self.company.corporate_number,
            name="Test Agreement",
            agreement_text="Please agree.",
            is_active=True
        )
        connection = ConnectStaff.objects.create(
            corporate_number=self.company.corporate_number,
            email=self.staff.email,
            status='pending'
        )

        response = self.client.post(reverse('connect:staff_approve', kwargs={'pk': connection.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('connect:staff_agreement_consent', kwargs={'pk': connection.pk}))

    def test_approve_if_all_agreed(self):
        """全ての同意書に同意済みの場合、直接承認される"""
        self.client.login(email='company@example.com', password='password')
        agreement = StaffAgreement.objects.create(
            corporation_number=self.company.corporate_number,
            name="Test Agreement",
            agreement_text="Please agree.",
            is_active=True
        )
        ConnectStaffAgree.objects.create(
            email=self.staff.email,
            corporate_number=self.company.corporate_number,
            staff_agreement=agreement,
            is_agreed=True
        )
        connection = ConnectStaff.objects.create(
            corporate_number=self.company.corporate_number,
            email=self.staff.email,
            status='pending'
        )

        response = self.client.post(reverse('connect:staff_approve', kwargs={'pk': connection.pk}))
        self.assertRedirects(response, reverse('connect:staff_list'))
        connection.refresh_from_db()
        self.assertEqual(connection.status, 'approved')

    def test_consent_submission_and_approval(self):
        """同意画面で同意し、その後承認される"""
        self.client.login(email='company@example.com', password='password')
        agreement = StaffAgreement.objects.create(
            corporation_number=self.company.corporate_number,
            name="Test Agreement",
            agreement_text="Please agree.",
            is_active=True
        )
        connection = ConnectStaff.objects.create(
            corporate_number=self.company.corporate_number,
            email=self.staff.email,
            status='pending'
        )

        # 同意画面へ
        response = self.client.post(reverse('connect:staff_approve', kwargs={'pk': connection.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('connect:staff_agreement_consent', kwargs={'pk': connection.pk}))

        # 同意を送信
        response = self.client.post(reverse('connect:staff_agreement_consent', kwargs={'pk': connection.pk}), {
            'agreements': [agreement.pk]
        })

        # 承認され、リストにリダイレクトされる
        self.assertRedirects(response, reverse('connect:staff_list'))
        connection.refresh_from_db()
        self.assertEqual(connection.status, 'approved')
        self.assertTrue(
            ConnectStaffAgree.objects.filter(
                email=self.staff.email,
                staff_agreement=agreement,
                is_agreed=True
            ).exists()
        )
