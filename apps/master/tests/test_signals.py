from django.test import TestCase
from apps.master.models import StaffAgreement
from apps.connect.models import ConnectStaff, ConnectStaffAgree
from django.contrib.auth import get_user_model

class StaffAgreementSignalTest(TestCase):
    def setUp(self):
        """テストに必要なデータを作成"""
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='password'
        )
        self.agreement = StaffAgreement.objects.create(
            name='Test Agreement',
            agreement_text='Original text'
        )
        self.connect_staff = ConnectStaff.objects.create(
            corporate_number='1234567890123',
            email='testuser@example.com',
            status='approved',
            approved_by=self.user
        )
        self.staff_agree = ConnectStaffAgree.objects.create(
            email=self.connect_staff.email,
            corporate_number=self.connect_staff.corporate_number,
            staff_agreement=self.agreement,
            is_agreed=True
        )

    def test_delete_staff_agreement_deletes_related_connect_staff_agree(self):
        """StaffAgreement削除時に、関連するConnectStaffAgreeが削除されることをテスト"""
        self.assertEqual(ConnectStaffAgree.objects.count(), 1)
        self.agreement.delete()
        self.assertEqual(ConnectStaffAgree.objects.count(), 0)

    def test_update_agreement_text_resets_is_agreed(self):
        """StaffAgreementの文言変更時に、is_agreedがFalseになることをテスト"""
        self.assertTrue(ConnectStaffAgree.objects.get(pk=self.staff_agree.pk).is_agreed)

        self.agreement.agreement_text = 'Updated text'
        self.agreement.save()

        self.assertFalse(ConnectStaffAgree.objects.get(pk=self.staff_agree.pk).is_agreed)

    def test_update_agreement_without_text_change_does_not_reset_is_agreed(self):
        """StaffAgreementの文言以外が変更された場合、is_agreedが変更されないことをテスト"""
        self.assertTrue(ConnectStaffAgree.objects.get(pk=self.staff_agree.pk).is_agreed)

        self.agreement.name = 'Updated Name'
        self.agreement.save()

        self.assertTrue(ConnectStaffAgree.objects.get(pk=self.staff_agree.pk).is_agreed)
