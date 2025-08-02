
from django.test import TestCase
from django.core.exceptions import ValidationError
from apps.client.validators import validate_corporate_number

class CorporateNumberValidatorTest(TestCase):

    def test_valid_corporate_numbers(self):
        """実在する正しい法人番号でエラーが発生しないことを確認"""
        valid_numbers = [
            '5835678256246',  # stdnumのドキュメントにある有効な例
        ]
        for number in valid_numbers:
            with self.subTest(number=number):
                try:
                    validate_corporate_number(number)
                except ValidationError as e:
                    self.fail(f"正しい法人番号 {number} でValidationErrorが発生しました: {e}")

    def test_invalid_corporate_numbers(self):
        """無効な法人番号でエラーが発生することを確認"""
        invalid_numbers = [
            '1234567890123',  # チェックディジットが違う
            '12345',          # 桁数が違う
            'abcdefghijklm',  # 数字以外
            '7000012010005',  # チェックディジットだけ違う
        ]
        for number in invalid_numbers:
            with self.subTest(number=number):
                with self.assertRaises(ValidationError):
                    validate_corporate_number(number)

    def test_empty_value_is_allowed(self):
        """空の値が許容されることを確認"""
        try:
            validate_corporate_number('')
            validate_corporate_number(None)
        except ValidationError:
            self.fail("空の法人番号でValidationErrorが発生しました。")
