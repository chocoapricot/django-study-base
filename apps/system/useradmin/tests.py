
from django.test import TestCase
from unittest.mock import patch
from .validators import MyPasswordValidator
class MyPasswordValidatorTest(TestCase):
    def test_accepts_max_length(self):
        # 最大長16文字に設定した場合のテスト
        def fake_param(key, default=None):
            if key == 'PASSWORD_MAX_LENGTH':
                return '16'
            if key == 'PASSWORD_MIN_LENGTH':
                return '8'
            if key == 'PASSWORD_SYMBOL_REQUIRED':
                return 'true'
            return default
        with patch('apps.system.useradmin.validators.my_parameter', side_effect=fake_param):
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
        validator = MyPasswordValidator()
        ok_passwords = [
            'abcde!12', 'abcde@12', 'abcde#12', 'abcde$12', 'abcde%12', 'abcde^12', 'abcde&12', 'abcde*12',
            'abcde-12', 'abcde+12', 'abcde=12', 'abcde?12', 'abcde(12', 'abcde)12', 'abcde[12', 'abcde]12'
        ]
        for pw in ok_passwords:
            try:
                validator.validate(pw)
            except Exception:
                self.fail(f"'{pw}' should be accepted as valid (contains symbol)")

    def test_rejects_no_symbol(self):
        validator = MyPasswordValidator()
        ng_passwords = ['abcdefgh', '12345678', 'パスワードです']
        for pw in ng_passwords:
            with self.assertRaises(Exception):
                validator.validate(pw)

    def test_rejects_fullwidth_symbol(self):
        validator = MyPasswordValidator()
        # 全角記号はNG
        ng_passwords = ['abcde！12', 'abcde＠12', 'abcde＃12']
        for pw in ng_passwords:
            with self.assertRaises(Exception):
                validator.validate(pw)
