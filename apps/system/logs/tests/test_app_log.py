from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.system.logs.models import AppLog

User = get_user_model()


class AppLogModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_app_log_creation(self):
        """AppLogモデルの作成テスト"""
        log = AppLog.objects.create(
            user=self.user,
            action='create',
            model_name='TestModel',
            object_id='1',
            object_repr='テストオブジェクト'
        )
        
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action, 'create')
        self.assertEqual(log.model_name, 'TestModel')
        self.assertEqual(log.object_id, '1')
        self.assertEqual(log.object_repr, 'テストオブジェクト')
        self.assertIsNotNone(log.timestamp)

    def test_app_log_str_representation(self):
        """AppLogの文字列表現テスト"""
        log = AppLog.objects.create(
            user=self.user,
            action='update',
            model_name='TestModel',
            object_id='1',
            object_repr='テストオブジェクト'
        )
        
        # 実際のstr表現をチェック
        str_repr = str(log)
        self.assertIn('testuser', str_repr)
        self.assertIn('update', str_repr)
        self.assertIn('TestModel', str_repr)
        self.assertIn('テストオブジェクト', str_repr)