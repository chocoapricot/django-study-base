from .settings import *

# テスト環境専用設定
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_TERMS_OF_SERVICE_REQUIRED = False

# テスト用データベース設定
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# テスト実行を高速化
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]