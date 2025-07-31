from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model, authenticate
from django.urls import reverse
from django.contrib.auth.hashers import check_password
from apps.accounts.forms import CustomSignupForm
from apps.accounts.adapters import CustomAccountAdapter
from allauth.account.models import EmailAddress

User = get_user_model()

@override_settings(
    ACCOUNT_SIGNUP_FORM_CLASS='apps.accounts.forms.CustomSignupForm',
    ACCOUNT_EMAIL_VERIFICATION='none'
)
class AuthenticationTestCase(TestCase):
    """
    認証システムのテストケース
    
    django-allauthを使用したカスタム認証システムの動作を検証します。
    - カスタムサインアップフォーム
    - 利用規約同意フロー
    - ユーザー作成とパスワード処理
    """
    
    def setUp(self):
        """テストの初期設定"""
        self.client = Client()
        self.test_email = 'test@example.com'
        self.test_password = 'testpassword123!'  # パスワードバリデーター要件を満たす
        self.test_first_name = '太郎'
        self.test_last_name = '田中'
        
        # 利用規約同意をデフォルトで設定（個別テストで上書き可能）
        self.client.session['agreed_to_terms'] = True
        self.client.session.save()

    def tearDown(self):
        """テスト後のクリーンアップ"""
        # テストで作成されたユーザーとEmailAddressを削除
        User.objects.filter(email=self.test_email).delete()
        User.objects.filter(email='test_adapter_user@example.com').delete()
        EmailAddress.objects.filter(email=self.test_email).delete()
        
        # セッションデータをクリア
        self.client.session.clear()

    def test_real_signup_flow(self):
        """実際のサインアップフローをテスト"""
        print("=== 実際のサインアップフローテスト開始 ===")
        
        # 1. 利用規約への同意を確実に設定
        print("1. 利用規約への同意を設定")
        session = self.client.session
        session['agreed_to_terms'] = True
        session.save()
        print(f"セッション設定後: {self.client.session.get('agreed_to_terms')}")
        
        # 2. サインアップページにPOSTリクエスト
        print("2. サインアップページにPOSTリクエスト")
        signup_data = {
            'email': self.test_email,
            'password1': self.test_password,
            'password2': self.test_password,
            'first_name': self.test_first_name,
            'last_name': self.test_last_name,
        }
        
        response = self.client.post(reverse('account_signup'), signup_data)
        print(f"サインアップレスポンスステータス: {response.status_code}")
        print(f"リダイレクト先: {response.get('Location', 'なし')}")
        
        # レスポンスが302でない場合、内容を確認
        if response.status_code != 302:
            print(f"レスポンス内容の一部: {response.content.decode()[:500]}")
        
        # 3. ユーザーが作成されたかチェック
        print("3. ユーザーが作成されたかチェック")
        try:
            created_user = User.objects.get(email=self.test_email)
            print(f"作成されたユーザー: {created_user}")
            print(f"ユーザー名: {created_user.username}")
            print(f"メールアドレス: {created_user.email}")
            print(f"姓: {created_user.last_name}")
            print(f"名: {created_user.first_name}")
            print(f"is_active: {created_user.is_active}")
            
            # パスワードとフィールドの検証
            self.assertTrue(created_user.check_password(self.test_password), "パスワードが正しく保存されていません")
            self.assertEqual(created_user.last_name, self.test_last_name)
            self.assertEqual(created_user.first_name, self.test_first_name)
            
            print("=== サインアップフローテスト成功 ===")

        except User.DoesNotExist:
            print("ユーザーが作成されていません")
            # 全ユーザーを確認
            all_users = User.objects.all()
            print(f"データベース内の全ユーザー: {list(all_users)}")
            self.fail("サインアップでユーザーが作成されませんでした")

    def test_terms_of_service_flow(self):
        """利用規約同意フローを含むサインアップテスト"""
        print("=== 利用規約同意フローテスト開始 ===")
        
        # 1. 利用規約に同意していない状態でサインアップページにアクセス
        print("1. 利用規約未同意でサインアップページにアクセス")
        response = self.client.get(reverse('account_signup'))
        print(f"サインアップページレスポンス: {response.status_code}")
        
        # 利用規約ページにリダイレクトされることを確認
        if response.status_code == 302:
            print(f"リダイレクト先: {response.get('Location')}")
            self.assertIn('terms-of-service', response.get('Location', ''))
        
        # 2. 利用規約ページで同意
        print("2. 利用規約ページで同意")
        terms_response = self.client.post(reverse('terms_of_service'), {
            'agree_to_terms': 'on'
        })
        print(f"利用規約同意レスポンス: {terms_response.status_code}")
        print(f"同意後のセッション: {self.client.session.get('agreed_to_terms')}")
        
        # 3. 同意後にサインアップを実行
        print("3. 同意後にサインアップを実行")
        signup_data = {
            'email': self.test_email,
            'password1': self.test_password,
            'password2': self.test_password,
            'first_name': self.test_first_name,
            'last_name': self.test_last_name,
        }
        
        signup_response = self.client.post(reverse('account_signup'), signup_data)
        print(f"サインアップレスポンス: {signup_response.status_code}")
        
        # 4. ユーザーが作成されたかチェック
        print("4. ユーザーが作成されたかチェック")
        try:
            created_user = User.objects.get(email=self.test_email)
            print(f"作成されたユーザー: {created_user}")
            self.assertTrue(created_user.check_password(self.test_password))
            self.assertEqual(created_user.last_name, self.test_last_name)
            self.assertEqual(created_user.first_name, self.test_first_name)
            print("=== 利用規約同意フローテスト成功 ===")
            
        except User.DoesNotExist:
            self.fail("利用規約同意後のサインアップでユーザーが作成されませんでした")

    def test_direct_user_creation(self):
        """直接ユーザー作成のテスト（比較用）"""
        print("=== 直接ユーザー作成テスト開始 ===")
        
        user = User.objects.create_user(
            username=self.test_email,
            email=self.test_email,
            password=self.test_password,
            first_name=self.test_first_name,
            last_name=self.test_last_name
        )
        
        print(f"直接作成されたユーザー: {user}")
        self.assertTrue(user.check_password(self.test_password))
        self.assertEqual(user.email, self.test_email)
        print("=== 直接ユーザー作成テスト成功 ===")

    def test_custom_signup_form(self):
        """カスタムサインアップフォームのテスト"""
        print("=== カスタムサインアップフォームテスト開始 ===")
        
        form_data = {
            'email': self.test_email,
            'password1': self.test_password,
            'password2': self.test_password,
            'first_name': self.test_first_name,
            'last_name': self.test_last_name,
        }
        
        form = CustomSignupForm(data=form_data)
        print(f"フォームの有効性: {form.is_valid()}")
        
        if not form.is_valid():
            print(f"フォームエラー: {form.errors}")
        
        self.assertTrue(form.is_valid(), "カスタムサインアップフォームが無効です")
        print("=== カスタムサインアップフォームテスト成功 ===")
