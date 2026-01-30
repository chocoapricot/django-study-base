from django.test import TestCase
from django.urls import reverse
from apps.accounts.models import MyUser
from apps.staff.models import Staff
from apps.client.models import Client
from apps.company.models import Company
from apps.master.models import Information
from apps.common.middleware import set_current_tenant_id

class DataDeletionTest(TestCase):

    def setUp(self):
        # 会社作成
        self.company = Company.objects.create(
            name='テスト会社',
            corporate_number='1234567890123'
        )
        set_current_tenant_id(self.company.id)

        # 1. テストデータのセットアップ
        # 管理者ユーザー
        self.admin_user = MyUser.objects.create_superuser(
            'admin', 'admin@example.com', 'password',
            tenant_id=self.company.id
        )
        # 一般ユーザー
        self.normal_user = MyUser.objects.create_user(
            'testuser', 'testuser@test.com', 'password'
        )
        # マスターデータ
        Information.objects.create(
            subject='Test Info',
            content='This is a test information.'
        )
        # トランザクションデータ
        Client.objects.create(
            tenant_id=self.company.id,
            name='Test Client',
            name_furigana='テストクライアント'
        )
        Staff.objects.create(
            tenant_id=self.company.id,
            email='teststaff@test.com',
            name_last='Test',
            name_first='Staff',
            name_kana_last='テスト',
            name_kana_first='スタッフ',
        )

    def test_delete_application_data(self):
        # 初期状態の確認
        self.assertEqual(Client.objects.count(), 1)
        self.assertEqual(Staff.objects.count(), 1)
        self.assertEqual(Information.objects.count(), 1)
        self.assertEqual(MyUser.objects.filter(is_superuser=False).count(), 1)
        self.assertEqual(MyUser.objects.filter(is_superuser=True).count(), 1)

        # 2. テストの実行
        # 管理者でログイン
        self.client.login(username='admin', password='password')
        session = self.client.session
        session['current_tenant_id'] = self.company.id
        session.save()

        # データ削除エンドポイントにPOSTリクエスト
        response = self.client.post(reverse('home:delete_application_data'))

        # 3. アサーション（検証）
        # リダイレクトを確認
        self.assertRedirects(response, reverse('home:start_page'))

        # トランザクションデータが削除されたことを確認
        self.assertEqual(Client.objects.count(), 0)
        self.assertEqual(Staff.objects.count(), 0)

        # マスターデータが残っていることを確認
        self.assertEqual(Information.objects.count(), 1)

        # 一般ユーザーが削除されたことを確認
        self.assertEqual(MyUser.objects.filter(is_superuser=False).count(), 0)

        # 管理者ユーザーが残っていることを確認
        self.assertEqual(MyUser.objects.filter(is_superuser=True).count(), 1)

    def test_delete_application_data_permission_denied(self):
        # 一般ユーザーでログイン
        self.client.login(username='testuser', password='password')

        # データ削除エンドポイントにPOSTリクエスト
        response = self.client.post(reverse('home:delete_application_data'))

        # ログインページにリダイレクトされることを確認
        self.assertRedirects(response, f"{reverse('account_login')}?next={reverse('home:delete_application_data')}", fetch_redirect_response=False)

        # データが削除されていないことを確認
        self.assertEqual(Client.objects.count(), 1)
        self.assertEqual(Staff.objects.count(), 1)
        self.assertEqual(Information.objects.count(), 1)
        self.assertEqual(MyUser.objects.count(), 2)
