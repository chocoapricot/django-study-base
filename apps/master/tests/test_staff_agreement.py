from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.master.models import StaffAgreement
import time

User = get_user_model()

class StaffAgreementModelTest(TestCase):
    """スタッフ同意文言モデルのテスト"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_str_method(self):
        """__str__メソッドのテスト"""
        agreement = StaffAgreement.objects.create(
            name='テスト同意文言',
            agreement_text='これはテスト用の同意文言です。',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(str(agreement), 'テスト同意文言')

    def test_default_values(self):
        """デフォルト値のテスト"""
        agreement = StaffAgreement.objects.create(
            name='デフォルト値テスト',
            agreement_text='テキスト',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(agreement.display_order, 0)
        self.assertTrue(agreement.is_active)

    def test_successful_creation(self):
        """正常な作成のテスト"""
        agreement = StaffAgreement.objects.create(
            name='作成テスト',
            agreement_text='作成テスト用のテキストです。',
            display_order=10,
            is_active=False,
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(agreement.name, '作成テスト')
        self.assertEqual(agreement.agreement_text, '作成テスト用のテキストです。')
        self.assertEqual(agreement.display_order, 10)
        self.assertFalse(agreement.is_active)

    def test_save_method_no_change(self):
        """変更がない場合にupdated_atが更新されないことをテスト"""
        agreement = StaffAgreement.objects.create(
            name='保存テスト',
            agreement_text='テキスト',
            created_by=self.user,
            updated_by=self.user
        )
        first_updated_at = agreement.updated_at

        time.sleep(0.01)

        agreement.save()

        agreement.refresh_from_db()
        second_updated_at = agreement.updated_at

        self.assertEqual(first_updated_at.strftime("%Y-%m-%d %H:%M:%S"), second_updated_at.strftime("%Y-%m-%d %H:%M:%S"))


class StaffAgreementViewTest(TestCase):
    """スタッフ同意文言ビューのテスト"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            is_staff=True
        )
        self.client.login(username='testuser', password='testpass123')

        self.agreement = StaffAgreement.objects.create(
            name='ビューテスト用同意文言',
            agreement_text='ビューテスト用のテキストです。',
            created_by=self.user,
            updated_by=self.user
        )

    def test_list_view(self):
        """一覧表示ビューのテスト"""
        response = self.client.get(reverse('master:staff_agreement_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ビューテスト用同意文言')
        self.assertTemplateUsed(response, 'master/staffagreement_list.html')

    def test_detail_view(self):
        """詳細表示ビューのテスト"""
        response = self.client.get(reverse('master:staff_agreement_detail', kwargs={'pk': self.agreement.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ビューテスト用同意文言')
        self.assertContains(response, 'ビューテスト用のテキストです。')
        self.assertTemplateUsed(response, 'master/staffagreement_detail.html')

    def test_master_index_list_contains_link(self):
        """マスタ一覧に同意文言管理へのリンクが表示されるかテスト"""
        from django.contrib.auth.models import Permission
        # The master_index_list view requires at least one 'view' permission to be accessed
        # and the specific permission for the item to be displayed.
        permissions = Permission.objects.filter(
            codename__in=['view_qualification', 'view_staffagreement']
        )
        self.user.user_permissions.set(permissions)

        response = self.client.get(reverse('master:master_index_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'スタッフ同意文言管理')
        self.assertContains(response, reverse('master:staff_agreement_list'))
