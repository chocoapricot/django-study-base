from django.test import TestCase, Client as TestClient
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
import re

# allauthのトークン生成ツールをインポート
from allauth.account.utils import user_pk_to_url_str
from allauth.account.forms import default_token_generator

User = get_user_model()

class PasswordResetTest(TestCase):
    """パスワードリセット機能のテストクラス (django-allauth)"""

    def setUp(self):
        """テストデータのセットアップ"""
        self.client = TestClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='oldpassword123',
            first_name='テスト',
            last_name='ユーザー'
        )

    def test_password_reset_page_display(self):
        """パスワードリセットページの表示テスト"""
        response = self.client.get(reverse('account_reset_password'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'account/password_reset.html')

    def test_password_reset_request_valid_email(self):
        """有効なメールアドレスでリセット要求をするとメールが送信されリダイレクトすること"""
        response = self.client.post(reverse('account_reset_password'), {'email': 'test@example.com'})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('パスワードリセットのご案内', mail.outbox[0].subject)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('account_reset_password_done'))

    def test_password_reset_request_invalid_email(self):
        """存在しないメールアドレスでリセット要求をしても、メールは送信されず、同じ画面にリダイレクトすること"""
        response = self.client.post(reverse('account_reset_password'), {'email': 'nonexistent@example.com'})
        self.assertEqual(len(mail.outbox), 0)  # メールが送信されないことを確認
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('account_reset_password_done'))

    def test_reset_form_get_with_valid_token(self):
        """有効なトークンでパスワードリセットフォームが表示されること"""
        token = default_token_generator.make_token(self.user)
        uid = user_pk_to_url_str(self.user)
        url = reverse('account_reset_password_from_key', kwargs={'uidb36': uid, 'key': token})
        
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '新しいパスワード')

    def test_reset_form_get_with_invalid_token(self):
        """無効なトークンではエラーメッセージが表示されること"""
        uid = user_pk_to_url_str(self.user)
        url = reverse('account_reset_password_from_key', kwargs={'uidb36': uid, 'key': 'invalid-token'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '無効なリンクです')

    def test_reset_form_post_success(self):
        """有効なトークンでパスワードをPOSTすると成功し、リダイレクトすること"""
        token = default_token_generator.make_token(self.user)
        uid = user_pk_to_url_str(self.user)
        url = reverse('account_reset_password_from_key', kwargs={'uidb36': uid, 'key': token})
        
        # POSTの前にGETリクエストでセッションを確立
        self.client.get(url, follow=True)

        new_password = '1qazxsw2#'
        response = self.client.post(url, {
            'password1': new_password,
            'password2': new_password,
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('account_reset_password_from_key_done'))
        
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))

    def test_reset_form_post_password_mismatch(self):
        """パスワードが一致しないPOSTではフォームエラーが表示されること"""
        token = default_token_generator.make_token(self.user)
        uid = user_pk_to_url_str(self.user)
        url = reverse('account_reset_password_from_key', kwargs={'uidb36': uid, 'key': token})
        
        # POSTの前にGETリクエストでセッションを確立
        self.client.get(url, follow=True)

        response = self.client.post(url, {
            'password1': '1qazxsw2#',
            'password2': 'another_1qazxsw2#',
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '2つのパスワードが一致しませんでした')

    def test_full_password_reset_flow(self):
        """パスワードリセットのE2Eフローテスト"""
        # 1. リセット要求
        response = self.client.post(reverse('account_reset_password'), {'email': self.user.email})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)

        # 2. メールからURLを抽出
        email_body = mail.outbox[0].body
        match = re.search(r'http[s]?://[^/]+(/accounts/password/reset/key/[^/]+/)', email_body)
        self.assertIsNotNone(match)
        reset_url = match.group(1)

        # 3. フォームをGET
        response = self.client.get(reset_url)
        self.assertEqual(response.status_code, 200)

        # 4. 新しいパスワードをPOST
        new_password = 'e2e_new_password_!@#'
        response = self.client.post(reset_url, {
            'password1': new_password,
            'password2': new_password,
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('account_reset_password_from_key_done'))

        # 5. 新しいパスワードでログイン
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))
        
        # ログインを試行
        login_response = self.client.post(reverse('account_login'), {
            'login': self.user.email,
            'password': new_password,
        })
        self.assertEqual(login_response.status_code, 302)
        self.assertRedirects(login_response, reverse('home:home'))
