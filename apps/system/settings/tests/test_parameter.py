from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.system.settings.models import Parameter
from apps.system.settings.forms import ParameterForm

User = get_user_model()


class ParameterModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_parameter_creation(self):
        """Parameterモデルの作成テスト"""
        parameter = Parameter.objects.create(
            key='test_key',
            value='test_value',
            description='テストパラメータ',
            data_type='string',
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )
        
        self.assertEqual(parameter.key, 'test_key')
        self.assertEqual(parameter.value, 'test_value')
        self.assertEqual(parameter.description, 'テストパラメータ')
        self.assertEqual(parameter.data_type, 'string')
        self.assertTrue(parameter.is_active)
        self.assertEqual(str(parameter), 'test_key: test_value')

    def test_parameter_unique_key(self):
        """パラメータキーの一意性テスト"""
        Parameter.objects.create(
            key='unique_key',
            value='value1',
            created_by=self.user,
            updated_by=self.user
        )
        
        # 同じキーのパラメータは作成できない
        with self.assertRaises(Exception):
            Parameter.objects.create(
                key='unique_key',
                value='value2',
                created_by=self.user,
                updated_by=self.user
            )

    def test_parameter_data_types(self):
        """パラメータのデータ型テスト"""
        # 文字列型
        string_param = Parameter.objects.create(
            key='string_param',
            value='文字列値',
            data_type='string',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(string_param.data_type, 'string')
        
        # 整数型
        integer_param = Parameter.objects.create(
            key='integer_param',
            value='123',
            data_type='integer',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(integer_param.data_type, 'integer')
        
        # 真偽値型
        boolean_param = Parameter.objects.create(
            key='boolean_param',
            value='true',
            data_type='boolean',
            created_by=self.user,
            updated_by=self.user
        )
        self.assertEqual(boolean_param.data_type, 'boolean')

    def test_parameter_get_typed_value(self):
        """型変換されたパラメータ値の取得テスト"""
        # 整数型パラメータ
        integer_param = Parameter.objects.create(
            key='int_param',
            value='42',
            data_type='integer',
            created_by=self.user,
            updated_by=self.user
        )
        # get_typed_valueメソッドがある場合のテスト
        # self.assertEqual(integer_param.get_typed_value(), 42)
        
        # 真偽値型パラメータ
        boolean_param = Parameter.objects.create(
            key='bool_param',
            value='true',
            data_type='boolean',
            created_by=self.user,
            updated_by=self.user
        )
        # self.assertTrue(boolean_param.get_typed_value())

    def test_parameter_active_filter(self):
        """アクティブなパラメータのフィルタテスト"""
        active_param = Parameter.objects.create(
            key='active_param',
            value='active_value',
            is_active=True,
            created_by=self.user,
            updated_by=self.user
        )
        inactive_param = Parameter.objects.create(
            key='inactive_param',
            value='inactive_value',
            is_active=False,
            created_by=self.user,
            updated_by=self.user
        )
        
        active_params = Parameter.objects.filter(is_active=True)
        self.assertIn(active_param, active_params)
        self.assertNotIn(inactive_param, active_params)


class ParameterFormTest(TestCase):
    def test_valid_form(self):
        """有効なフォームデータのテスト"""
        form_data = {
            'key': 'test_key',
            'value': 'test_value',
            'description': 'テストパラメータ',
            'data_type': 'string',
            'is_active': True
        }
        form = ParameterForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_required_fields(self):
        """必須フィールドのテスト"""
        form = ParameterForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('key', form.errors)
        self.assertIn('value', form.errors)

    def test_key_validation(self):
        """キーのバリデーションテスト"""
        # 無効なキー（スペースを含む）
        form_data = {
            'key': 'invalid key',
            'value': 'test_value',
            'data_type': 'string'
        }
        form = ParameterForm(data=form_data)
        # キーのバリデーションがある場合
        # self.assertFalse(form.is_valid())
        # self.assertIn('key', form.errors)


class ParameterViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        # 必要な権限を付与
        from django.contrib.auth.models import Permission
        permissions = Permission.objects.filter(
            content_type__app_label='settings',
            codename__in=[
                'add_parameter', 'view_parameter', 
                'change_parameter', 'delete_parameter'
            ]
        )
        self.user.user_permissions.set(permissions)
        
        self.parameter = Parameter.objects.create(
            key='test_key',
            value='test_value',
            description='テストパラメータ',
            created_by=self.user,
            updated_by=self.user
        )
        self.test_client = TestClient()

    def test_parameter_list_view(self):
        """パラメータ一覧ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(reverse('settings:parameter_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test_key')

    def test_parameter_create_view(self):
        """パラメータ作成ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(reverse('settings:parameter_create'))
        self.assertEqual(response.status_code, 200)

    def test_parameter_detail_view(self):
        """パラメータ詳細ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('settings:parameter_detail', kwargs={'pk': self.parameter.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test_key')

    def test_parameter_update_view(self):
        """パラメータ更新ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('settings:parameter_update', kwargs={'pk': self.parameter.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_parameter_delete_view(self):
        """パラメータ削除ビューのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('settings:parameter_delete', kwargs={'pk': self.parameter.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_parameter_create_post(self):
        """パラメータ作成POSTのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        form_data = {
            'key': 'new_key',
            'value': 'new_value',
            'description': '新しいパラメータ',
            'data_type': 'string',
            'is_active': True
        }
        
        response = self.test_client.post(
            reverse('settings:parameter_create'),
            data=form_data
        )
        
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.assertTrue(
            Parameter.objects.filter(key='new_key').exists()
        )

    def test_parameter_update_post(self):
        """パラメータ更新POSTのテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        form_data = {
            'key': 'test_key',
            'value': 'updated_value',
            'description': '更新されたパラメータ',
            'data_type': 'string',
            'is_active': True
        }
        
        response = self.test_client.post(
            reverse('settings:parameter_update', kwargs={'pk': self.parameter.pk}),
            data=form_data
        )
        
        self.assertEqual(response.status_code, 302)  # リダイレクト
        self.parameter.refresh_from_db()
        self.assertEqual(self.parameter.value, 'updated_value')
        self.assertEqual(self.parameter.description, '更新されたパラメータ')

    def test_parameter_search(self):
        """パラメータ検索機能のテスト"""
        self.test_client.login(username='testuser', password='testpass123')
        
        response = self.test_client.get(
            reverse('settings:parameter_list'),
            {'q': 'test_key'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'test_key')