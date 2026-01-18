from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.master.models import Bank, Qualification

User = get_user_model()


class BankPermissionTest(TestCase):
    """銀行マスタの権限テスト"""

    def setUp(self):
        self.client = Client()
        # is_staff=Trueがないとそもそもadminにアクセスできず、権限チェックまでたどり着かない
        self.user = User.objects.create_user(
            username='testuser_no_perm',
            email='no_perm@example.com',
            password='testpass123',
            is_staff=True,
        )
        self.client.login(username='testuser_no_perm', password='testpass123')

        self.bank = Bank.objects.create(
            name='テスト銀行',
            bank_code='1234',
            created_by=self.user,
            updated_by=self.user,
        )

    def test_bank_management_no_permission(self):
        """銀行統合管理ビュー（権限なし）"""
        response = self.client.get(reverse('master:bank_management'))
        self.assertEqual(response.status_code, 403)

    def test_bank_create_no_permission(self):
        """銀行作成ビュー（権限なし）"""
        response = self.client.get(reverse('master:bank_create'))
        self.assertEqual(response.status_code, 403)

    def test_bank_update_no_permission(self):
        """銀行更新ビュー（権限なし）"""
        response = self.client.get(reverse('master:bank_update', kwargs={'pk': self.bank.pk}))
        self.assertEqual(response.status_code, 403)

    def test_bank_delete_no_permission(self):
        """銀行削除ビュー（権限なし）"""
        # 削除はPOSTで行われることが多い
        response = self.client.post(reverse('master:bank_delete', kwargs={'pk': self.bank.pk}))
        self.assertEqual(response.status_code, 403)


class QualificationPermissionTest(TestCase):
    """資格マスタの権限テスト"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser_no_perm_qual',
            email='no_perm_qual@example.com',
            password='testpass123',
            is_staff=True,
        )
        self.client.login(username='testuser_no_perm_qual', password='testpass123')

        self.category = Qualification.objects.create(
            name='テストカテゴリ',
            level=1,  # level=1がカテゴリ
            created_by=self.user,
            updated_by=self.user,
        )
        self.qualification = Qualification.objects.create(
            name='テスト資格',
            level=2,  # level=2が資格
            parent=self.category,
            created_by=self.user,
            updated_by=self.user,
        )

    def test_qualification_list_no_permission(self):
        """資格一覧ビュー（権限なし）"""
        response = self.client.get(reverse('master:qualification_list'))
        self.assertEqual(response.status_code, 403)

    def test_qualification_detail_no_permission(self):
        """資格詳細ビュー（権限なし）"""
        response = self.client.get(reverse('master:qualification_detail', kwargs={'pk': self.qualification.pk}))
        self.assertEqual(response.status_code, 403)

    def test_qualification_create_no_permission(self):
        """資格作成ビュー（権限なし）"""
        response = self.client.get(reverse('master:qualification_create'))
        self.assertEqual(response.status_code, 403)

    def test_qualification_category_create_no_permission(self):
        """資格カテゴリ作成ビュー（権限なし）"""
        response = self.client.get(reverse('master:qualification_category_create'))
        self.assertEqual(response.status_code, 403)

    def test_qualification_update_no_permission(self):
        """資格更新ビュー（権限なし）"""
        response = self.client.get(reverse('master:qualification_update', kwargs={'pk': self.qualification.pk}))
        self.assertEqual(response.status_code, 403)

    def test_qualification_delete_no_permission(self):
        """資格削除ビュー（権限なし）"""
        # 削除確認ページへのGET
        response_get = self.client.get(reverse('master:qualification_delete', kwargs={'pk': self.qualification.pk}))
        self.assertEqual(response_get.status_code, 403)
        # 削除実行のPOST
        response_post = self.client.post(reverse('master:qualification_delete', kwargs={'pk': self.qualification.pk}))
        self.assertEqual(response_post.status_code, 403)
