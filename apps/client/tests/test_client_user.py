from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.client.models import Client, ClientDepartment, ClientUser
from apps.client.forms import ClientUserForm

User = get_user_model()


class ClientUserModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client_obj = Client.objects.create(
            name='テスト会社',
            name_furigana='テストガイシャ',
            regist_form_client=10
        )
        self.department = ClientDepartment.objects.create(
            client=self.client_obj,
            name='営業部',
            department_code='SALES'
        )

    def test_client_user_creation(self):
        """ClientUserモデルの作成テスト"""
        client_user = ClientUser.objects.create(
            client=self.client_obj,
            department=self.department,
            name_last='田中',
            name_first='太郎',
            name_kana_last='タナカ',
            name_kana_first='タロウ',
            position='課長',
            phone_number='090-1234-5678',
            email='tanaka@test.com',
            memo='営業担当',
            display_order=1
        )
        
        self.assertEqual(client_user.client, self.client_obj)
        self.assertEqual(client_user.department, self.department)
        self.assertEqual(client_user.name_last, '田中')
        self.assertEqual(client_user.name_first, '太郎')
        self.assertEqual(client_user.name, '田中 太郎')
        self.assertEqual(str(client_user), 'テスト会社 - 田中 太郎')

    def test_client_user_without_department(self):
        """部署なしのClientUserテスト"""
        client_user = ClientUser.objects.create(
            client=self.client_obj,
            name_last='佐藤',
            name_first='花子',
            position='部長'
        )
        
        self.assertEqual(client_user.client, self.client_obj)
        self.assertIsNone(client_user.department)
        self.assertEqual(client_user.name, '佐藤 花子')

    def test_client_user_ordering(self):
        """ClientUserの表示順テスト"""
        user1 = ClientUser.objects.create(
            client=self.client_obj,
            name_last='田中',
            name_first='太郎',
            display_order=2
        )
        user2 = ClientUser.objects.create(
            client=self.client_obj,
            name_last='佐藤',
            name_first='花子',
            display_order=1
        )
        
        users = list(ClientUser.objects.all())
        self.assertEqual(users[0], user2)  # display_order=1が先
        self.assertEqual(users[1], user1)  # display_order=2が後


class ClientUserFormTest(TestCase):
    def setUp(self):
        self.client_obj = Client.objects.create(
            name='テスト会社',
            name_furigana='テストガイシャ',
            regist_form_client=10
        )
        self.department = ClientDepartment.objects.create(
            client=self.client_obj,
            name='営業部'
        )

    def test_valid_form(self):
        """有効なフォームデータのテスト"""
        form_data = {
            'department': self.department.pk,
            'name_last': '田中',
            'name_first': '太郎',
            'name_kana_last': 'タナカ',
            'name_kana_first': 'タロウ',
            'position': '課長',
            'phone_number': '090-1234-5678',
            'email': 'tanaka@test.com',
            'memo': '営業担当',
            'display_order': 1
        }
        form = ClientUserForm(data=form_data, client=self.client_obj)
        self.assertTrue(form.is_valid())

    def test_required_fields(self):
        """必須フィールドのテスト"""
        form = ClientUserForm(data={}, client=self.client_obj)
        self.assertFalse(form.is_valid())
        self.assertIn('name_last', form.errors)
        self.assertIn('name_first', form.errors)

    def test_email_validation(self):
        """メールアドレスのバリデーションテスト"""
        form_data = {
            'name_last': '田中',
            'name_first': '太郎',
            'email': 'invalid-email'
        }
        form = ClientUserForm(data=form_data, client=self.client_obj)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_department_queryset_filtering(self):
        """部署選択肢のフィルタリングテスト"""
        # 別のクライアントの部署を作成
        other_client = Client.objects.create(
            name='他の会社',
            name_furigana='ホカノガイシャ',
            regist_form_client=10
        )
        other_department = ClientDepartment.objects.create(
            client=other_client,
            name='他の部署'
        )
        
        form = ClientUserForm(client=self.client_obj)
        department_choices = [choice[0] for choice in form.fields['department'].queryset.values_list('pk')]
        
        self.assertIn(self.department.pk, department_choices)
        self.assertNotIn(other_department.pk, department_choices)


class ClientUserViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        # 必要な権限を付与
        from django.contrib.auth.models import Permission
        permissions = Permission.objects.filter(
            content_type__app_label='client',
            codename__in=[
                'add_clientuser', 'view_clientuser', 
                'change_clientuser', 'delete_clientuser',
                'view_client'  # クライアント詳細画面用
            ]
        )
        self.user.user_permissions.set(permissions)
        
        self.client_obj = Client.objects.create(
            name='テスト会社',
            name_furigana='テストガイシャ',
            regist_form_client=10
        )
        self.department = ClientDepartment.objects.create(
            client=self.client_obj,
            name='営業部'
        )
        self.client_user = ClientUser.objects.create(
            client=self.client_obj,
            department=self.department,
            name_last='田中',
            name_first='太郎'
        )
        self.test_client = TestClient()

    def test_client_user_create_view(self):
        """担当者作成ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('client:client_user_create', kwargs={'client_pk': self.client_obj.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_client_user_list_view(self):
        """担当者一覧ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('client:client_user_list', kwargs={'client_pk': self.client_obj.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '田中 太郎')

    def test_client_user_update_view(self):
        """担当者更新ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('client:client_user_update', kwargs={'pk': self.client_user.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_client_user_delete_view(self):
        """担当者削除ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('client:client_user_delete', kwargs={'pk': self.client_user.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_client_user_create_post(self):
        """担当者作成POSTのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        form_data = {
            'department': self.department.pk,
            'name_last': '佐藤',
            'name_first': '花子',
            'position': '部長',
            'display_order': 1
        }
        
        response = self.test_client.post(
            reverse('client:client_user_create', kwargs={'client_pk': self.client_obj.pk}),
            data=form_data
        )
        
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.assertTrue(
            ClientUser.objects.filter(
                client=self.client_obj,
                name_last='佐藤',
                name_first='花子'
            ).exists()
        )

    def test_client_detail_shows_departments_and_users(self):
        """クライアント詳細画面に組織と担当者が表示されるテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('client:client_detail', kwargs={'pk': self.client_obj.pk})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '組織一覧')
        self.assertContains(response, '担当者一覧')
        self.assertContains(response, '営業部')
        self.assertContains(response, '田中 太郎')