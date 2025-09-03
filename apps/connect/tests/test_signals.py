from django.test import TestCase
from apps.master.models import StaffAgreement
from apps.connect.models import ConnectStaff, ConnectStaffAgree
from django.contrib.auth import get_user_model

class ConnectStaffSignalTest(TestCase):
    def setUp(self):
        """テストに必要なデータを作成"""
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='password'
        )
        self.agreement = StaffAgreement.objects.create(
            name='Test Agreement',
            agreement_text='Some text'
        )
        self.connect_staff = ConnectStaff.objects.create(
            corporate_number='1234567890123',
            email='testuser@example.com',
            status='approved',
            approved_by=self.user
        )
        ConnectStaffAgree.objects.create(
            email=self.connect_staff.email,
            corporate_number=self.connect_staff.corporate_number,
            staff_agreement=self.agreement,
            is_agreed=True
        )

    def test_unapprove_connect_staff_deletes_agreement(self):
        """ConnectStaffの承認解除時に、関連するConnectStaffAgreeが削除されることをテスト"""
        self.assertEqual(ConnectStaffAgree.objects.count(), 1)

        self.connect_staff.status = 'pending'
        self.connect_staff.save()

        self.assertEqual(ConnectStaffAgree.objects.count(), 0)

    def test_delete_connect_staff_deletes_agreement(self):
        """ConnectStaff削除時に、関連するConnectStaffAgreeが削除されることをテスト"""
        self.assertEqual(ConnectStaffAgree.objects.count(), 1)

        self.connect_staff.delete()

        self.assertEqual(ConnectStaffAgree.objects.count(), 0)
