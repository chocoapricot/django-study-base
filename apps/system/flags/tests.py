from django.test import TestCase, Client as DjangoClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.company.models import Company
from apps.staff.models import Staff
from apps.staff.models_other import StaffFlag
from apps.master.models_other import FlagStatus
from apps.common.middleware import set_current_tenant_id

User = get_user_model()

class FlagListViewTests(TestCase):
    def setUp(self):
        # テナントの作成
        self.company = Company.objects.create(name='Test Company', tenant_id=1)
        set_current_tenant_id(self.company.tenant_id)

        # ユーザーの作成
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='password', tenant_id=self.company.tenant_id)

        self.client = DjangoClient()
        self.client.login(username='testuser', password='password')

        # セッションにテナントIDを設定
        session = self.client.session
        session['current_tenant_id'] = self.company.tenant_id
        session.save()

        # マスターデータの作成
        self.flag_status = FlagStatus.objects.create(name='Test Status', display_order=1)

        # スタッフの作成
        self.staff = Staff.objects.create(
            name_last='Test',
            name_first='User',
            email='test@example.com'
        )

        # フラッグの作成
        self.flag = StaffFlag.objects.create(
            staff=self.staff,
            flag_status=self.flag_status,
            details='Test details'
        )

    def test_flag_list_view_status_code(self):
        """フラッグ一覧ビューが正常にアクセスできることをテスト"""
        response = self.client.get(reverse('system_flags:flag_list'))
        self.assertEqual(response.status_code, 200)

    def test_flag_list_view_context(self):
        """フラッグ一覧ビューのコンテキストに正しいデータが含まれていることをテスト"""
        response = self.client.get(reverse('system_flags:flag_list'))
        self.assertIn('flags', response.context)
        flags = response.context['flags']
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]['entity_name'], 'Test User')
        self.assertEqual(flags[0]['type'], 'スタッフ')
        self.assertEqual(flags[0]['flag'].details, 'Test details')

    def test_flag_list_view_unauthenticated(self):
        """未認証ユーザーがログインページにリダイレクトされることをテスト"""
        self.client.logout()
        response = self.client.get(reverse('system_flags:flag_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
