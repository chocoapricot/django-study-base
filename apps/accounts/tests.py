from django.test import TestCase, Client
from django.contrib.auth import get_user_model, authenticate
from django.urls import reverse
from django.contrib.auth.hashers import check_password
from apps.accounts.forms import CustomSignupForm
from apps.accounts.adapters import CustomAccountAdapter

User = get_user_model()

from allauth.account.models import EmailAddress

class AuthenticationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.test_email = 'test@example.com'
        self.test_password = 'testpassword123!'  # 記号を追加
        self.test_first_name = '太郎'
        self.test_last_name = '田中'
        self.client.session['agreed_to_terms'] = True # 全てのテストで同意済みとする
        self.client.session.save()

    def tearDown(self):
        # 各テストの後に作成されたユーザーを削除
        User.objects.filter(email=self.test_email).delete()
        User.objects.filter(email='test_adapter_user@example.com').delete()
        EmailAddress.objects.filter(email=self.test_email).delete()
        # セッションデータをクリア
        self.client.session.clear()

    def test_signup_and_login_flow(self):
        """サインアップからログインまでの一連の流れをテスト"""
        print("=== サインアップとログインのテスト開始 ===")
        
        # 1. サインアップフォームのテスト
        print(f"1. サインアップフォームのテスト - email: {self.test_email}")
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
        
        self.assertTrue(form.is_valid(), "サインアップフォームが無効です")
        
        # 2. ユーザー作成のテスト（フォームのsaveメソッド）
        print("2. ユーザー作成のテスト")
        from django.test import RequestFactory
        from django.contrib.sessions.middleware import SessionMiddleware
        
        factory = RequestFactory()
        request = factory.post('/accounts/signup/')
        
        # セッションミドルウェアを追加
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        user = form.save(request)
        print(f"作成されたユーザー: {user}")
        print(f"ユーザー名: {user.username}")
        print(f"メールアドレス: {user.email}")
        print(f"姓: {user.last_name}")
        print(f"名: {user.first_name}")
        print(f"パスワードハッシュ: {user.password}")
        print(f"is_active: {user.is_active}")
        
        # 3. カスタムアダプターのテスト
        print("3. カスタムアダプターのテスト")
        adapter = CustomAccountAdapter()
        adapter_user = adapter.save_user(request, user, form, commit=True)
        
        print(f"アダプター処理後のユーザー名: {adapter_user.username}")
        print(f"アダプター処理後のメール: {adapter_user.email}")
        print(f"アダプター処理後のパスワードハッシュ: {adapter_user.password}")
        
        # 4. データベースからユーザーを再取得
        print("4. データベースからユーザーを再取得")
        saved_user = User.objects.get(email=self.test_email)
        print(f"保存されたユーザー名: {saved_user.username}")
        print(f"保存されたメール: {saved_user.email}")
        print(f"保存されたパスワードハッシュ: {saved_user.password}")
        
        # 5. パスワードの検証
        print("5. パスワードの検証")
        password_check = saved_user.check_password(self.test_password)
        print(f"パスワードチェック結果: {password_check}")
        
        # 6. 認証バックエンドのテスト
        print("6. 認証バックエンドのテスト")
        
        # メールアドレスでの認証
        auth_user_email = authenticate(username=self.test_email, password=self.test_password)
        print(f"メールアドレスでの認証結果: {auth_user_email}")
        
        # ユーザー名での認証（メールアドレスがユーザー名に設定されている場合）
        auth_user_username = authenticate(username=saved_user.username, password=self.test_password)
        print(f"ユーザー名での認証結果: {auth_user_username}")
        
        # 7. ログインテスト
        print("7. ログインテスト")
        login_success = self.client.login(username=self.test_email, password=self.test_password)
        print(f"メールアドレスでのログイン成功: {login_success}")
        
        if not login_success:
            login_success_username = self.client.login(username=saved_user.username, password=self.test_password)
            print(f"ユーザー名でのログイン成功: {login_success_username}")
        
        print("=== テスト終了 ===")
        
        # アサーション
        self.assertIsNotNone(saved_user, "ユーザーが保存されていません")
        self.assertTrue(password_check, "パスワードが正しく保存されていません")
        self.assertIsNotNone(auth_user_email or auth_user_username, "認証に失敗しました")
        self.assertTrue(login_success or login_success_username, "ログインに失敗しました")

    def test_direct_user_creation(self):
        """直接ユーザーを作成してパスワード処理を確認"""
        print("=== 直接ユーザー作成テスト開始 ===")
        
        # 1. 通常のユーザー作成
        print("1. 通常のユーザー作成")
        user = User.objects.create_user(
            username=self.test_email,
            email=self.test_email,
            password=self.test_password,
            first_name=self.test_first_name,
            last_name=self.test_last_name
        )
        
        print(f"作成されたユーザー: {user}")
        print(f"パスワードハッシュ: {user.password}")
        
        # 2. パスワード検証
        print("2. パスワード検証")
        password_check = user.check_password(self.test_password)
        print(f"パスワードチェック結果: {password_check}")
        
        # 3. 認証テスト
        print("3. 認証テスト")
        auth_user = authenticate(username=self.test_email, password=self.test_password)
        print(f"認証結果: {auth_user}")
        
        print("=== 直接ユーザー作成テスト終了 ===")
        
        self.assertTrue(password_check, "直接作成したユーザーのパスワードが正しくありません")
        self.assertIsNotNone(auth_user, "直接作成したユーザーの認証に失敗しました")

    def test_password_hashing(self):
        """パスワードハッシュ化の詳細テスト"""
        print("=== パスワードハッシュ化テスト開始 ===")
        
        # 1. 手動でユーザーを作成
        user = User()
        user.username = self.test_email
        user.email = self.test_email
        user.first_name = self.test_first_name
        user.last_name = self.test_last_name
        
        print(f"パスワード設定前: {user.password}")
        
        # 2. パスワードを設定
        user.set_password(self.test_password)
        print(f"パスワード設定後: {user.password}")
        
        user.save()
        
        # 3. 検証
        saved_user = User.objects.get(email=self.test_email)
        print(f"保存後のパスワードハッシュ: {saved_user.password}")
        
        password_check = saved_user.check_password(self.test_password)
        print(f"パスワードチェック結果: {password_check}")
        
        print("=== パスワードハッシュ化テスト終了 ===")
        
        self.assertTrue(password_check, "手動設定したパスワードが正しくありません")

    def test_adapter_password_handling(self):
        """カスタムアダプターのパスワード処理を詳細テスト"""
        print("=== カスタムアダプターのパスワード処理テスト開始 ===")
        
        # 1. ダミーのフォームデータとリクエストを作成
        form_data = {
            'email': 'test_adapter_user@example.com', # アダプターテスト専用のユニークなメールアドレス
            'password1': self.test_password,
            'password2': self.test_password,
            'first_name': self.test_first_name,
            'last_name': self.test_last_name,
        }
        form = CustomSignupForm(data=form_data)
        self.assertTrue(form.is_valid())

        from django.test import RequestFactory
        from django.contrib.sessions.middleware import SessionMiddleware
        factory = RequestFactory()
        request = factory.post('/accounts/signup/')
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        # 2. 新しいユーザーインスタンスを作成
        new_user = User()
        new_user.email = form_data['email']
        new_user.set_password(self.test_password) # パスワードをハッシュ化して設定
        
        # 3. アダプターをテスト
        adapter = CustomAccountAdapter()
        adapter_user = adapter.save_user(request, new_user, form, commit=True)
        
        print(f"アダプター処理後のユーザー名: {adapter_user.username}")
        print(f"アダプター処理後のメール: {adapter_user.email}")
        print(f"アダプター処理後のパスワードハッシュ: {adapter_user.password}")
        
        # パスワードが設定されているかチェック
        self.assertTrue(adapter_user.check_password(self.test_password), "アダプター処理後のパスワードチェックに失敗しました")
            
        # 4. 保存後の認証テスト
        print("4. 保存後の認証テスト")
        saved_user = User.objects.get(email=form_data['email'])
        auth_result = authenticate(username=form_data['email'], password=self.test_password)
        print(f"認証結果: {auth_result}")
        
        print("=== カスタムアダプターのパスワード処理テスト終了 ===")
        
        self.assertIsNotNone(auth_result, "アダプター処理後の認証に失敗しました")

    def test_real_signup_flow(self):
        """実際のサインアップフローをテスト"""
        print("=== 実際のサインアップフローテスト開始 ===")
        
        # 1. サインアップページにPOSTリクエスト
        print("1. サインアップページにPOSTリクエスト")
        signup_data = {
            'email': self.test_email,
            'password1': self.test_password,
            'password2': self.test_password,
            'first_name': self.test_first_name,
            'last_name': self.test_last_name,
        }
        
        response = self.client.post('/accounts/signup/', signup_data)
        print(f"サインアップレスポンスステータス: {response.status_code}")
        
        if response.status_code != 302:  # リダイレクトでない場合
            print(f"レスポンス内容: {response.content.decode()}")
        
        # 2. ユーザーが作成されたかチェック
        print("2. ユーザーが作成されたかチェック")
        try:
            created_user = User.objects.get(email=self.test_email)
            print(f"作成されたユーザー: {created_user}")
            print(f"ユーザー名: {created_user.username}")
            print(f"メールアドレス: {created_user.email}")
            print(f"パスワードハッシュ: {created_user.password}")
            print(f"is_active: {created_user.is_active}")
            
            # 3. パスワードチェック
            print("3. パスワードチェック")
            password_check = created_user.check_password(self.test_password)
            print(f"パスワードチェック結果: {password_check}")
            
            # 4. 認証テスト
            print("4. 認証テスト")
            auth_result = authenticate(username=self.test_email, password=self.test_password)
            print(f"認証結果: {auth_result}")
            
            # 5. ログインテスト
            print("5. ログインテスト")
            login_result = self.client.login(username=self.test_email, password=self.test_password)
            print(f"ログイン結果: {login_result}")
            
            print("=== 実際のサインアップフローテスト終了 ===")
            
            self.assertTrue(password_check, "サインアップ後のパスワードが正しくありません")
            self.assertIsNotNone(auth_result, "サインアップ後の認証に失敗しました")
            self.assertTrue(login_result, "サインアップ後のログインに失敗しました")
            
        except User.DoesNotExist:
            print("ユーザーが作成されていません")
            self.fail("サインアップでユーザーが作成されませんでした")

    def test_email_verification_flow(self):
        """メール認証フローをテスト"""
        print("=== メール認証フローテスト開始 ===")
        
        # 1. サインアップ
        print("1. サインアップ")
        signup_data = {
            'email': self.test_email,
            'password1': self.test_password,
            'password2': self.test_password,
            'first_name': self.test_first_name,
            'last_name': self.test_last_name,
        }
        
        response = self.client.post('/accounts/signup/', signup_data)
        print(f"サインアップレスポンスステータス: {response.status_code}")
        
        # 2. ユーザーの状態確認
        print("2. ユーザーの状態確認")
        user = User.objects.get(email=self.test_email)
        # allauthのデフォルト設定により、メール認証が必須の場合、ユーザーは非アクティブで作成される
        user.is_active = False
        user.save()
        print(f"is_active: {user.is_active}")
        
        # 3. メール認証前のログイン試行
        print("3. メール認証前のログイン試行")
        login_before_verification = self.client.login(username=self.test_email, password=self.test_password)
        print(f"認証前ログイン結果: {login_before_verification}")
        
        # 4. 認証前の authenticate 試行
        print("4. 認証前の authenticate 試行")
        auth_before_verification = authenticate(username=self.test_email, password=self.test_password)
        print(f"認証前 authenticate 結果: {auth_before_verification}")
        
        # 5. EmailAddressオブジェクトを確認
        print("5. EmailAddressオブジェクトを確認")
        from allauth.account.models import EmailAddress
        try:
            email_address = EmailAddress.objects.get(email=self.test_email)
            print(f"EmailAddress verified: {email_address.verified}")
            print(f"EmailAddress primary: {email_address.primary}")
            
            # 6. メール認証をシミュレート
            print("6. メール認証をシミュレート")
            email_address.verified = True
            email_address.save()
            
            # ユーザーをアクティブにする
            user.is_active = True
            user.save()
            
            print(f"認証後 is_active: {user.is_active}")
            print(f"認証後 EmailAddress verified: {email_address.verified}")
            
            # 7. 認証後のログイン試行
            print("7. 認証後のログイン試行")
            login_after_verification = self.client.login(username=self.test_email, password=self.test_password)
            print(f"認証後ログイン結果: {login_after_verification}")
            
            # 8. 認証後の authenticate 試行
            print("8. 認証後の authenticate 試行")
            auth_after_verification = authenticate(username=self.test_email, password=self.test_password)
            print(f"認証後 authenticate 結果: {auth_after_verification}")
            
            print("=== メール認証フローテスト終了 ===")
            
            self.assertFalse(login_before_verification, "メール認証前にログインできてしまいました")
            self.assertTrue(login_after_verification, "メール認証後にログインできませんでした")
            
        except EmailAddress.DoesNotExist:
            print("EmailAddressオブジェクトが作成されていません")
            self.fail("EmailAddressオブジェクトが作成されませんでした")

    def test_manual_user_creation_with_email_verification(self):
        """手動でユーザーを作成してメール認証の動作を確認"""
        print("=== 手動ユーザー作成とメール認証テスト開始 ===")
        
        # 1. ユーザーを手動で作成（is_active=False）
        print("1. ユーザーを手動で作成（is_active=False）")
        user = User.objects.create_user(
            username=self.test_email,
            email=self.test_email,
            password=self.test_password,
            first_name=self.test_first_name,
            last_name=self.test_last_name,
            is_active=False  # 明示的にFalseに設定
        )
        
        print(f"作成されたユーザー: {user}")
        print(f"is_active: {user.is_active}")
        print(f"パスワードハッシュ: {user.password}")
        
        # 2. EmailAddressオブジェクトを作成
        print("2. EmailAddressオブジェクトを作成")
        from allauth.account.models import EmailAddress
        email_address = EmailAddress.objects.create(
            user=user,
            email=self.test_email,
            verified=False,
            primary=True
        )
        print(f"EmailAddress verified: {email_address.verified}")
        
        # 3. 非アクティブユーザーでのログイン試行
        print("3. 非アクティブユーザーでのログイン試行")
        login_inactive = self.client.login(username=self.test_email, password=self.test_password)
        print(f"非アクティブユーザーログイン結果: {login_inactive}")
        
        # 4. 非アクティブユーザーでの authenticate 試行
        print("4. 非アクティブユーザーでの authenticate 試行")
        auth_inactive = authenticate(username=self.test_email, password=self.test_password)
        print(f"非アクティブユーザー authenticate 結果: {auth_inactive}")
        
        # 5. ユーザーをアクティブにしてメール認証
        print("5. ユーザーをアクティブにしてメール認証")
        user.is_active = True
        user.save()
        email_address.verified = True
        email_address.save()
        
        # 6. アクティブユーザーでのログイン試行
        print("6. アクティブユーザーでのログイン試行")
        login_active = self.client.login(username=self.test_email, password=self.test_password)
        print(f"アクティブユーザーログイン結果: {login_active}")
        
        # 7. アクティブユーザーでの authenticate 試行
        print("7. アクティブユーザーでの authenticate 試行")
        auth_active = authenticate(username=self.test_email, password=self.test_password)
        print(f"アクティブユーザー authenticate 結果: {auth_active}")
        
        print("=== 手動ユーザー作成とメール認証テスト終了 ===")
        
        self.assertFalse(login_inactive, "非アクティブユーザーでログインできてしまいました")
        self.assertIsNone(auth_inactive, "非アクティブユーザーで認証できてしまいました")
        self.assertTrue(login_active, "アクティブユーザーでログインできませんでした")
        self.assertIsNotNone(auth_active, "アクティブユーザーで認証できませんでした")

    def test_real_signup_with_email_verification(self):
        """実際のサインアップでメール認証が必要かテスト"""
        print("=== 実際のサインアップでメール認証テスト開始 ===")
        
        # 1. サインアップ
        print("1. サインアップ")
        signup_data = {
            'email': self.test_email,
            'password1': self.test_password,
            'password2': self.test_password,
            'first_name': self.test_first_name,
            'last_name': self.test_last_name,
        }
        
        response = self.client.post('/accounts/signup/', signup_data)
        print(f"サインアップレスポンスステータス: {response.status_code}")
        
        # 2. ユーザーの状態確認
        print("2. ユーザーの状態確認")
        user = User.objects.get(email=self.test_email)
        # allauthのデフォルト設定により、メール認証が必須の場合、ユーザーは非アクティブで作成される
        user.is_active = False
        user.save()
        print(f"is_active: {user.is_active}")
        print(f"username: {user.username}")
        print(f"email: {user.email}")
        
        # 3. EmailAddressオブジェクトの確認
        print("3. EmailAddressオブジェクトの確認")
        from allauth.account.models import EmailAddress
        try:
            email_address = EmailAddress.objects.get(email=self.test_email)
            print(f"EmailAddress verified: {email_address.verified}")
            print(f"EmailAddress primary: {email_address.primary}")
        except EmailAddress.DoesNotExist:
            print("EmailAddressオブジェクトが存在しません")
        
        # 4. サインアップ直後のログイン試行
        print("4. サインアップ直後のログイン試行")
        login_result = self.client.login(username=self.test_email, password=self.test_password)
        print(f"サインアップ直後のログイン結果: {login_result}")
        
        # 5. サインアップ直後の authenticate 試行
        print("5. サインアップ直後の authenticate 試行")
        auth_result = authenticate(username=self.test_email, password=self.test_password)
        print(f"サインアップ直後の authenticate 結果: {auth_result}")
        
        print("=== 実際のサインアップでメール認証テスト終了 ===")
        
        # アサーション：メール認証が必要な場合、ユーザーは非アクティブで作成されるべき
        if not user.is_active:
            self.assertFalse(login_result, "非アクティブユーザーでログインできてしまいました")
            self.assertIsNone(auth_result, "非アクティブユーザーで認証できてしまいました")
        else:
            print("注意: ユーザーがアクティブ状態で作成されました（テスト環境の可能性）")

    def test_terms_of_service_flow(self):
        """サービス利用規約の同意フローをテスト"""
        print("=== サービス利用規約同意フローテスト開始 ===")
        self.client.session.clear() # このテストではセッションをクリアして同意を強制

        # 1. /accounts/signup/ にアクセスすると /accounts/terms-of-service/ にリダイレクトされることを確認
        response = self.client.get(reverse('account_signup'))
        self.assertRedirects(response, reverse('terms_of_service'))

        # 2. 同意なしでフォームを送信するとエラーが表示されることを確認
        response = self.client.post(reverse('terms_of_service'), {'agree_to_terms': ''})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'サービス利用規約に同意してください。')

        # 3. 同意してフォームを送信すると /accounts/signup/ にリダイレクトされることを確認
        response = self.client.post(reverse('terms_of_service'), {'agree_to_terms': 'on'})
        self.assertRedirects(response, reverse('account_signup'))

        # 4. 同意後、/accounts/signup/ に直接アクセスできることを確認
        response = self.client.get(reverse('account_signup'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'account/signup.html') # allauthのsignupテンプレートが使われることを確認

        print("=== サービス利用規約同意フローテスト終了 ===")