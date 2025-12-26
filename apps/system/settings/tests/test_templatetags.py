from django.test import TestCase
from django.template import Context, Template
from django.contrib.auth import get_user_model
from apps.system.settings.models import Parameter

User = get_user_model()


class ParameterTemplateTagTest(TestCase):
    """パラメータテンプレートタグのテスト"""
    
    def setUp(self):
        """テストデータの準備"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_parameter_tag_with_existing_value(self):
        """存在するパラメータの取得テスト"""
        # テスト用パラメータを作成
        Parameter.objects.create(
            category='test',
            key='TEST_PARAM',
            value='test_value',
            default_value='default_value',
            note='テスト用パラメータ',
            created_by=self.user,
            updated_by=self.user
        )
        
        template = Template('{% load parameters %}{% parameter "TEST_PARAM" %}')
        rendered = template.render(Context({}))
        
        self.assertEqual(rendered, 'test_value')
    
    def test_parameter_tag_with_default_value(self):
        """存在しないパラメータのデフォルト値テスト"""
        template = Template('{% load parameters %}{% parameter "NON_EXISTENT_PARAM" "default_value" %}')
        rendered = template.render(Context({}))
        
        self.assertEqual(rendered, 'default_value')
    
    def test_parameter_tag_without_default_value(self):
        """存在しないパラメータでデフォルト値なしのテスト"""
        template = Template('{% load parameters %}{% parameter "NON_EXISTENT_PARAM" %}')
        rendered = template.render(Context({}))
        
        self.assertEqual(rendered, 'None')
    
    def test_notification_interval_parameter(self):
        """通知間隔パラメータの取得テスト"""
        # 通知間隔パラメータを作成
        Parameter.objects.create(
            category='notification',
            key='NOTIFICATION_COUNT_INTERVAL',
            value='60',
            default_value='30',
            note='通知カウント間隔',
            created_by=self.user,
            updated_by=self.user
        )
        
        template = Template('{% load parameters %}{% parameter "NOTIFICATION_COUNT_INTERVAL" "30" %}')
        rendered = template.render(Context({}))
        
        self.assertEqual(rendered, '60')
    
    def test_inactive_parameter(self):
        """非アクティブなパラメータのテスト"""
        # 非アクティブなパラメータを作成
        Parameter.objects.create(
            category='test',
            key='INACTIVE_PARAM',
            value='inactive_value',
            default_value='default_value',
            note='非アクティブパラメータ',
            active=False,  # 非アクティブ
            created_by=self.user,
            updated_by=self.user
        )
        
        template = Template('{% load parameters %}{% parameter "INACTIVE_PARAM" "fallback_value" %}')
        rendered = template.render(Context({}))
        
        self.assertEqual(rendered, 'fallback_value')  # デフォルト値が返される