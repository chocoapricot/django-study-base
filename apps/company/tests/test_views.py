from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from ..models import Company, CompanyDepartment, CompanyUser

User = get_user_model()

class CompanyViewTest(TestCase):
    """会社ビューのテスト"""

    def setUp(self):
        self.client = Client()
        # 権限を持つユーザー
        self.perm_user = User.objects.create_user(
            username='perm_user',
            email='perm@example.com',
            password='testpass123'
        )
        self.perm_user.user_permissions.add(
            Permission.objects.get(codename='view_company'),
            Permission.objects.get(codename='change_company')
        )
        # 権限を持たないユーザー
        self.no_perm_user = User.objects.create_user(
            username='no_perm_user',
            email='no_perm@example.com',
            password='testpass123'
        )

        # テスト用の画像を作成
        self.seal_image = SimpleUploadedFile(
            name='test_seal.png',
            content=b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0aIDATx\x9cc\xf8\xff\xff?\x03\x00\x05\xfe\x02\xfe\xdc\xccY\xe7\x00\x00\x00\x00IEND\xaeB`\x82',
            content_type='image/png'
        )

        self.company = Company.objects.create(
            name="テスト会社",
            corporate_number="1234567890123",
            dispatch_treatment_method='agreement',
            postal_code="1000001",
            address="東京都千代田区千代田1-1",
            phone_number="03-1234-5678"
        )
        self.company.round_seal.save('test.png', self.seal_image)

    def test_serve_company_seal_with_permission(self):
        """認証済みユーザーの印章画像ビューへのアクセス（権限あり）"""
        self.client.login(username='perm_user', password='testpass123')
        url = reverse('company:serve_company_seal', kwargs={'seal_type': 'round'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.seal_image.seek(0)
        self.assertEqual(response.content, self.seal_image.read())

    def test_serve_company_seal_no_permission(self):
        """認証済みユーザーの印章画像ビューへのアクセス（権限なし）"""
        self.client.login(username='no_perm_user', password='testpass123')
        url = reverse('company:serve_company_seal', kwargs={'seal_type': 'round'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_serve_company_seal_unauthenticated(self):
        """未認証ユーザーの印章画像ビューへのアクセス"""
        url = reverse('company:serve_company_seal', kwargs={'seal_type': 'round'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_company_detail_view_requires_login(self):
        """会社詳細ビューのログイン必須テスト"""
        response = self.client.get(reverse('company:company_detail'))
        self.assertEqual(response.status_code, 302)

    def test_company_detail_view_with_permission(self):
        """会社詳細ビュー（権限あり）"""
        self.client.login(username='perm_user', password='testpass123')
        response = self.client.get(reverse('company:company_detail'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "テスト会社")

    def test_company_detail_view_no_permission(self):
        """会社詳細ビュー（権限なし）"""
        self.client.login(username='no_perm_user', password='testpass123')
        response = self.client.get(reverse('company:company_detail'))
        self.assertEqual(response.status_code, 403)

    def test_company_edit_view_with_permission(self):
        """会社編集ビュー（権限あり）"""
        self.client.login(username='perm_user', password='testpass123')
        response = self.client.get(reverse('company:company_edit'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "会社情報編集")

    def test_company_edit_view_no_permission(self):
        """会社編集ビュー（権限なし）"""
        self.client.login(username='no_perm_user', password='testpass123')
        response = self.client.get(reverse('company:company_edit'))
        self.assertEqual(response.status_code, 403)
    
    def test_company_edit_no_changes(self):
        """会社編集で変更がない場合のテスト"""
        self.client.login(username='perm_user', password='testpass123')
        response = self.client.post(reverse('company:company_edit'), {
            'name': self.company.name,
            'corporate_number': getattr(self.company, 'corporate_number', '') or '',
            'representative': getattr(self.company, 'representative', '') or '',
            'postal_code': getattr(self.company, 'postal_code', '') or '',
            'address': getattr(self.company, 'address', '') or '',
            'phone_number': getattr(self.company, 'phone_number', '') or '',
        })
        self.assertIn(response.status_code, [200, 302])

    def test_change_history_list_view_with_permission(self):
        """変更履歴一覧ビュー（権限あり）"""
        self.client.login(username='perm_user', password='testpass123')
        response = self.client.get(reverse('company:change_history_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'common/common_change_history_list.html')
        self.assertContains(response, "会社関連 変更履歴一覧")

    def test_change_history_list_view_no_permission(self):
        """変更履歴一覧ビュー（権限なし）"""
        self.client.login(username='no_perm_user', password='testpass123')
        response = self.client.get(reverse('company:change_history_list'))
        self.assertEqual(response.status_code, 403)


class DepartmentViewTest(TestCase):
    """部署ビューのテスト"""
    
    def setUp(self):
        self.client = Client()
        # 権限を持つユーザー
        self.perm_user = User.objects.create_user(
            username='perm_user', password='testpassword'
        )
        self.perm_user.user_permissions.add(
            Permission.objects.get(codename='view_companydepartment'),
            Permission.objects.get(codename='add_companydepartment'),
            Permission.objects.get(codename='change_companydepartment'),
            Permission.objects.get(codename='delete_companydepartment')
        )
        # 権限を持たないユーザー（閲覧のみ可能）
        self.no_perm_user = User.objects.create_user(
            username='no_perm_user', password='testpassword'
        )
        self.no_perm_user.user_permissions.add(
            Permission.objects.get(codename='view_companyuser'),
            Permission.objects.get(codename='view_company')
        )
        self.no_perm_user.user_permissions.add(
            Permission.objects.get(codename='view_companyuser'),
            Permission.objects.get(codename='view_company')
        )

        self.department = CompanyDepartment.objects.create(
            name="開発部",
            corporate_number="1234567890123",
            department_code="DEV001",
            display_order=1
        )

    def test_department_detail_view_with_permission(self):
        """部署詳細ビュー（権限あり）"""
        self.client.login(username='perm_user', password='testpassword')
        response = self.client.get(reverse('company:department_detail', kwargs={'pk': self.department.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "開発部")

    def test_department_detail_view_no_permission(self):
        """部署詳細ビュー（権限なし）"""
        self.client.login(username='no_perm_user', password='testpassword')
        response = self.client.get(reverse('company:department_detail', kwargs={'pk': self.department.pk}))
        self.assertEqual(response.status_code, 403)
    
    def test_department_create_view_get_with_permission(self):
        """部署作成ビュー GET（権限あり）"""
        self.client.login(username='perm_user', password='testpassword')
        response = self.client.get(reverse('company:department_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "部署作成")

    def test_department_create_view_get_no_permission(self):
        """部署作成ビュー GET（権限なし）"""
        self.client.login(username='no_perm_user', password='testpassword')
        response = self.client.get(reverse('company:department_create'))
        self.assertEqual(response.status_code, 403)
    
    def test_department_create_post_with_permission(self):
        """部署作成 POST（権限あり）"""
        self.client.login(username='perm_user', password='testpassword')
        data = {'name': '営業部', 'corporate_number': '1234567890123', 'department_code': 'SALES001', 'display_order': 2}
        response = self.client.post(reverse('company:department_create'), data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(CompanyDepartment.objects.filter(name='営業部').exists())

    def test_department_create_post_no_permission(self):
        """部署作成 POST（権限なし）"""
        self.client.login(username='no_perm_user', password='testpassword')
        data = {'name': '総務部', 'corporate_number': '1234567890123', 'department_code': 'GA001', 'display_order': 3}
        response = self.client.post(reverse('company:department_create'), data)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(CompanyDepartment.objects.filter(name='総務部').exists())

    def test_department_edit_view_get_with_permission(self):
        """部署編集ビュー GET（権限あり）"""
        self.client.login(username='perm_user', password='testpassword')
        response = self.client.get(reverse('company:department_edit', kwargs={'pk': self.department.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "部署編集")

    def test_department_edit_view_get_no_permission(self):
        """部署編集ビュー GET（権限なし）"""
        self.client.login(username='no_perm_user', password='testpassword')
        response = self.client.get(reverse('company:department_edit', kwargs={'pk': self.department.pk}))
        self.assertEqual(response.status_code, 403)

    def test_department_edit_post_with_permission(self):
        """部署編集 POST（権限あり）"""
        self.client.login(username='perm_user', password='testpassword')
        data = {
            'name': '開発部(更新)', 'corporate_number': self.department.corporate_number,
            'department_code': self.department.department_code, 'display_order': self.department.display_order
        }
        response = self.client.post(reverse('company:department_edit', kwargs={'pk': self.department.pk}), data)
        self.assertEqual(response.status_code, 302)
        self.department.refresh_from_db()
        self.assertEqual(self.department.name, '開発部(更新)')

    def test_department_edit_post_no_permission(self):
        """部署編集 POST（権限なし）"""
        self.client.login(username='no_perm_user', password='testpassword')
        data = {'name': '開発部(更新失敗)'}
        response = self.client.post(reverse('company:department_edit', kwargs={'pk': self.department.pk}), data)
        self.assertEqual(response.status_code, 403)
        self.department.refresh_from_db()
        self.assertNotEqual(self.department.name, '開発部(更新失敗)')

    def test_department_delete_view_get_with_permission(self):
        """部署削除ビュー GET（権限あり）"""
        self.client.login(username='perm_user', password='testpassword')
        response = self.client.get(reverse('company:department_delete', kwargs={'pk': self.department.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "部署削除確認")

    def test_department_delete_view_get_no_permission(self):
        """部署削除ビュー GET（権限なし）"""
        self.client.login(username='no_perm_user', password='testpassword')
        response = self.client.get(reverse('company:department_delete', kwargs={'pk': self.department.pk}))
        self.assertEqual(response.status_code, 403)

    def test_department_delete_post_with_permission(self):
        """部署削除 POST（権限あり）"""
        self.client.login(username='perm_user', password='testpassword')
        department_id = self.department.pk
        response = self.client.post(reverse('company:department_delete', kwargs={'pk': department_id}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(CompanyDepartment.objects.filter(pk=department_id).exists())

    def test_department_delete_post_no_permission(self):
        """部署削除 POST（権限なし）"""
        self.client.login(username='no_perm_user', password='testpassword')
        department_id = self.department.pk
        response = self.client.post(reverse('company:department_delete', kwargs={'pk': department_id}))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(CompanyDepartment.objects.filter(pk=department_id).exists())


class CompanyUserViewTest(TestCase):
    """自社担当者ビューのテスト"""

    def setUp(self):
        from django.contrib.auth.models import Group
        Company.objects.all().delete()
        self.client = Client()
        # 権限を持つユーザー
        self.perm_user = User.objects.create_user(
            username='perm_user', password='testpassword'
        )
        self.perm_user.user_permissions.add(
            Permission.objects.get(codename='view_companyuser'),
            Permission.objects.get(codename='add_companyuser'),
            Permission.objects.get(codename='change_companyuser'),
            Permission.objects.get(codename='delete_companyuser'),
            Permission.objects.get(codename='view_company') # リダイレクト先で必要
        )
        # 権限を持たないユーザー
        self.no_perm_user = User.objects.create_user(
            username='no_perm_user', password='testpassword'
        )
        # 閲覧のみ権限を持つユーザー
        self.view_only_user = User.objects.create_user(
            username='view_only_user', password='testpassword'
        )
        self.view_only_user.user_permissions.add(
            Permission.objects.get(codename='view_companyuser')
        )
        # companyグループ作成
        self.company_group = Group.objects.create(name='company')

        self.company = Company.objects.create(name="テスト株式会社", corporate_number="1112223334445", dispatch_treatment_method='agreement')
        self.department = CompanyDepartment.objects.create(
            name="テスト部署",
            corporate_number="1112223334445",
            department_code="TEST_DEPT"
        )
        self.company_user = CompanyUser.objects.create(
            corporate_number="1112223334445",
            department_code="TEST_DEPT",
            name_last="山田",
            name_first="太郎",
            email="taro.yamada@example.com"
        )
        self.create_url = reverse('company:company_user_create')
        self.edit_url = reverse('company:company_user_edit', kwargs={'pk': self.company_user.pk})
        self.delete_url = reverse('company:company_user_delete', kwargs={'pk': self.company_user.pk})
        self.detail_url = reverse('company:company_user_detail', kwargs={'pk': self.company_user.pk})
        self.redirect_url = reverse('company:company_detail')

    def test_views_with_permission(self):
        """権限ありユーザーのビューアクセス"""
        self.client.login(username='perm_user', password='testpassword')
        # Create
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 200)
        data = {'department_code': self.department.department_code, 'name_last': '鈴木', 'name_first': '一郎', 'display_order': 0}
        response = self.client.post(self.create_url, data)
        self.assertRedirects(response, self.redirect_url)
        self.assertTrue(CompanyUser.objects.filter(name_last='鈴木').exists())
        # Edit
        response = self.client.get(self.edit_url)
        self.assertEqual(response.status_code, 200)
        data = {'department_code': self.department.department_code, 'name_last': '山田', 'name_first': '太郎', 'position': '本部長', 'display_order': 0}
        response = self.client.post(self.edit_url, data)
        self.assertRedirects(response, self.redirect_url)
        self.company_user.refresh_from_db()
        self.assertEqual(self.company_user.position, '本部長')
        # Detail
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        # Delete
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(self.delete_url)
        self.assertRedirects(response, self.redirect_url)
        self.assertFalse(CompanyUser.objects.filter(pk=self.company_user.pk).exists())

    def test_views_no_permission(self):
        """権限なしユーザーのビューアクセス"""
        self.client.login(username='no_perm_user', password='testpassword')
        # Create
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 403)
        data = {'department_code': self.department.department_code, 'name_last': '佐藤', 'name_first': '次郎'}
        response = self.client.post(self.create_url, data)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(CompanyUser.objects.filter(name_last='佐藤').exists())
        # Edit
        response = self.client.get(self.edit_url)
        self.assertEqual(response.status_code, 403)
        data = {'department_code': self.department.department_code, 'name_last': '山田', 'name_first': '太郎', 'position': '課長'}
        response = self.client.post(self.edit_url, data)
        self.assertEqual(response.status_code, 403)
        # Detail
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 403)
        # Delete
        response = self.client.get(self.delete_url)
        self.assertEqual(response.status_code, 403)
        response = self.client.post(self.delete_url)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(CompanyUser.objects.filter(pk=self.company_user.pk).exists())

    def test_account_creation_and_deletion_with_permission(self):
        """アカウント作成・削除（権限あり）"""
        self.client.login(username='perm_user', password='testpassword')

        # 初期状態ではアカウントが存在しないことを確認
        self.assertFalse(User.objects.filter(email=self.company_user.email).exists())

        # アカウント作成
        response = self.client.post(self.detail_url, {'toggle_account': '1'})
        self.assertRedirects(response, self.detail_url)
        self.assertTrue(User.objects.filter(email=self.company_user.email).exists())
        user_account = User.objects.get(email=self.company_user.email)
        self.assertIn(self.company_group, user_account.groups.all())

        # アカウント削除
        response = self.client.post(self.detail_url, {'toggle_account': '1'})
        self.assertRedirects(response, self.detail_url)
        self.assertFalse(User.objects.filter(email=self.company_user.email).exists())

    def test_account_creation_no_permission(self):
        """アカウント作成（権限なし）"""
        self.client.login(username='view_only_user', password='testpassword')

        response = self.client.post(self.detail_url, {'toggle_account': '1'})
        # 権限がない場合、ビューはメッセージを表示してリダイレクトする
        self.assertRedirects(response, self.detail_url)
        self.assertFalse(User.objects.filter(email=self.company_user.email).exists())

    def test_account_creation_no_email(self):
        """アカウント作成（メールアドレスなし）"""
        self.client.login(username='perm_user', password='testpassword')
        no_email_user = CompanyUser.objects.create(
            corporate_number=self.company.corporate_number,
            name_last="佐藤", name_first="花子"
        )
        detail_url = reverse('company:company_user_detail', kwargs={'pk': no_email_user.pk})

        response = self.client.post(detail_url, {'toggle_account': '1'})
        self.assertRedirects(response, detail_url)
        # メールアドレスがないのでUserは作成されない
        self.assertEqual(User.objects.count(), 3) # perm_user, no_perm_user, view_only_user
