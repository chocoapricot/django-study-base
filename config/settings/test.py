from .settings import *

# テスト用の設定
TESTING = True

# allauthのテスト設定
ACCOUNT_EMAIL_VERIFICATION = "none"  # テスト中はメール認証を無効化
ACCOUNT_SIGNUP_FORM_CLASS = 'apps.accounts.forms.CustomSignupForm'
