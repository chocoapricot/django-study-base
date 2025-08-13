from django.test import TestCase
from unittest.mock import patch
from apps.accounts.validators import MyPasswordValidator


class MyPasswordValidatorTest(TestCase):
    def test_accepts_max_length(self):
        """最大長16文字に設定した場合のテスト"""
        def fake_param(key, default=None):
            if key == 'PASSWORD_MAX_LENGTH':
                return '16'
            if key == 'PASSWORD_MIN_LENGTH':
                return '8'
            if key == 'PASSWORD_SYMBOL_REQUIRED':
                return 'true'
            return default
            
        with patch('apps.accounts.validators.my_parameter', side_effect=fake_param):
            validator = MyPasswordValidator()
            # 16文字はOK
            try:
                validator.validate('abcde!1234567890')
            except Exception:
                self.fail('16文字のパスワードは許可されるべき')
            # 17文字はNG
            with self.assertRaises(Exception):
                validator.validate('abcde!12345678901')

    def test_accepts_halfwidth_symbols(self):
        """半角記号の受け入れテスト"""
        validator = MyPasswordValidator()
        ok_passwords = [
            'abcde!12', 'abcde@12', 'abcde#12', 'abcde$12', 'abcde%12', 
            'abcde^12', 'abcde&12', 'abcde*12', 'abcde(12', 'abcde)12',
            'abcde-12', 'abcde_12', 'abcde=12', 'abcde+12', 'abcde[12',
            'abcde]12', 'abcde{12', 'abcde}12', 'abcde|12',
            'abcde:12', 'abcde;12', 'abcde\"12', 'abcde\'12', 'abcde<12',
            'abcde>12', 'abcde,12', 'abcde.12', 'abcde?12', 'abcde/12'
        ]
        
        def fake_param(key, default=None):
            if key == 'PASSWORD_MIN_LENGTH':
                return '8'
            if key == 'PASSWORD_MAX_LENGTH':
                return '20'
            if key == 'PASSWORD_SYMBOL_REQUIRED':
                return 'true'
            return default
            
        with patch('apps.accounts.validators.my_parameter', side_effect=fake_param):
            validator = MyPasswordValidator()
            for password in ok_passwords:
                try:
                    validator.validate(password)
                except Exception as e:
                    self.fail(f'パスワード "{password}" は許可されるべき: {e}')

    def test_rejects_fullwidth_symbols(self):
        """全角記号の拒否テスト"""
        def fake_param(key, default=None):
            if key == 'PASSWORD_MIN_LENGTH':
                return '8'
            if key == 'PASSWORD_MAX_LENGTH':
                return '20'
            if key == 'PASSWORD_SYMBOL_REQUIRED':
                return 'true'
            return default
            
        with patch('apps.accounts.validators.my_parameter', side_effect=fake_param):
            validator = MyPasswordValidator()
            ng_passwords = [
                'abcde！12',  # 全角感嘆符
                'abcde＠12',  # 全角アットマーク
                'abcde＃12',  # 全角シャープ
                'abcde＄12',  # 全角ドル
                'abcde％12',  # 全角パーセント
            ]
            
            for password in ng_passwords:
                with self.assertRaises(Exception):
                    validator.validate(password)

    def test_minimum_length_validation(self):
        """最小長のバリデーションテスト"""
        def fake_param(key, default=None):
            if key == 'PASSWORD_MIN_LENGTH':
                return '10'
            if key == 'PASSWORD_MAX_LENGTH':
                return '20'
            if key == 'PASSWORD_SYMBOL_REQUIRED':
                return 'true'
            return default
            
        with patch('apps.accounts.validators.my_parameter', side_effect=fake_param):
            validator = MyPasswordValidator()
            
            # 10文字未満はNG
            with self.assertRaises(Exception):
                validator.validate('abcde!12')  # 8文字
            
            # 10文字以上はOK
            try:
                validator.validate('abcde!1234')  # 10文字
            except Exception:
                self.fail('10文字のパスワードは許可されるべき')

    def test_symbol_required_validation(self):
        """記号必須のバリデーションテスト"""
        def fake_param(key, default=None):
            if key == 'PASSWORD_MIN_LENGTH':
                return '8'
            if key == 'PASSWORD_MAX_LENGTH':
                return '20'
            if key == 'PASSWORD_SYMBOL_REQUIRED':
                return 'true'
            return default
            
        with patch('apps.accounts.validators.my_parameter', side_effect=fake_param):
            validator = MyPasswordValidator()
            
            # 記号なしはNG
            with self.assertRaises(Exception):
                validator.validate('abcde123')
            
            # 記号ありはOK
            try:
                validator.validate('abcde!23')
            except Exception:
                self.fail('記号を含むパスワードは許可されるべき')

    def test_symbol_not_required_validation(self):
        """記号不要のバリデーションテスト"""
        def fake_param(key, default=None):
            if key == 'PASSWORD_MIN_LENGTH':
                return '8'
            if key == 'PASSWORD_MAX_LENGTH':
                return '20'
            if key == 'PASSWORD_SYMBOL_REQUIRED':
                return 'false'
            return default
            
        with patch('apps.accounts.validators.my_parameter', side_effect=fake_param):
            validator = MyPasswordValidator()
            
            # 記号なしでもOK
            try:
                validator.validate('abcde123')
            except Exception:
                self.fail('記号不要設定時は記号なしパスワードも許可されるべき')
            
            # 記号ありでもOK
            try:
                validator.validate('abcde!23')
            except Exception:
                self.fail('記号ありパスワードも許可されるべき')

    def test_get_help_text(self):
        """ヘルプテキストの取得テスト"""
        def fake_param(key, default=None):
            if key == 'PASSWORD_MIN_LENGTH':
                return '8'
            if key == 'PASSWORD_MAX_LENGTH':
                return '16'
            if key == 'PASSWORD_SYMBOL_REQUIRED':
                return 'true'
            return default
            
        with patch('apps.accounts.validators.my_parameter', side_effect=fake_param):
            validator = MyPasswordValidator()
            help_text = validator.get_help_text()
            
            self.assertIn('8文字以上', help_text)
            self.assertIn('16文字以下', help_text)
            self.assertIn('記号', help_text)