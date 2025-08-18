from django.test import TestCase
from apps.profile.forms import StaffProfileForm

from apps.system.settings.models import Dropdowns

class StaffProfileFormTest(TestCase):
    def test_phone_zenkaku(self):
        # 電話番号に全角数字が含まれる場合はバリデーションエラー
        form = StaffProfileForm(data={
            'name_last': '山田',
            'name_first': '太郎',
            'name_kana_last': 'ヤマダ',
            'name_kana_first': 'タロウ',
            'birth_date': '2000-01-01',
            'sex': '1',
            'postal_code': '1234567',
            'address_kana': '',
            'address1': '東京都',
            'address2': '千代田区',
            'address3': '',
            'phone': '０９０-１２３４-５６７８',  # 全角数字
        })
        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)
        self.assertIn('電話番号は半角数字とハイフンのみ入力してください。', form.errors['phone'])
    def setUp(self):
        Dropdowns.objects.create(category='sex', value='1', name='男性', disp_seq=1, active=True)
    def test_kana_validation(self):
        # ひらがなも許可され、カタカナに変換される
        form = StaffProfileForm(data={
            'name_last': '山田',
            'name_first': '太郎',
            'name_kana_last': 'やまだ',
            'name_kana_first': 'たろう',
            'birth_date': '2000-01-01',
            'sex': '1',
            'postal_code': '1234567',
            'address_kana': '',
            'address1': '東京都',
            'address2': '千代田区',
            'address3': '',
            'phone': '090-1234-5678',
        })
        valid = form.is_valid()
        self.assertTrue(valid)
        self.assertEqual(form.cleaned_data['name_kana_last'], 'ヤマダ')
        self.assertEqual(form.cleaned_data['name_kana_first'], 'タロウ')

    def test_kana_fullwidth_conversion(self):
        # 半角カナ→全角カナに変換される
        form = StaffProfileForm(data={
            'name_last': '山田',
            'name_first': '太郎',
            'name_kana_last': 'ﾔﾏﾀﾞ',
            'name_kana_first': 'ﾀﾛｳ',
            'birth_date': '2000-01-01',
            'sex': '1',  # 必須
            'postal_code': '1234567',
            'address_kana': '',
            'address1': '東京都',  # 必須
            'address2': '千代田区',  # 必須
            'address3': '',
            'phone': '090-1234-5678',
        })
        valid = form.is_valid()
        # バリデーションエラーがなければ全角変換を確認
        if valid:
            self.assertEqual(form.cleaned_data['name_kana_last'], 'ヤマダ')
            self.assertEqual(form.cleaned_data['name_kana_first'], 'タロウ')
        else:
            self.fail(f"form errors: {form.errors}")

    def test_phone_validation(self):
        # 電話番号に英字が含まれる→エラー
        form = StaffProfileForm(data={
            'name_last': '山田',
            'name_first': '太郎',
            'name_kana_last': 'ヤマダ',
            'name_kana_first': 'タロウ',
            'birth_date': '2000-01-01',
            'sex': '',
            'postal_code': '1234567',
            'address_kana': '',
            'address1': '',
            'address2': '',
            'address3': '',
            'phone': '090-1234-ABCD',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)

    def test_required_fields(self):
        """
        必須項目が未入力の場合はバリデーションエラー
        """
        form = StaffProfileForm(data={
            'name_last': '山田',
            'name_first': '太郎',
            'name_kana_last': 'ヤマダ',
            'name_kana_first': 'タロウ',
            # 'birth_date' 未入力
            # 'sex' 未入力
            # 'postal_code' 未入力
            'address_kana': '',
            # 'address1' 未入力
            # 'address2' 未入力
            'address3': '',
            # 'phone' 未入力
        })
        self.assertFalse(form.is_valid())
        self.assertIn('birth_date', form.errors)
        self.assertIn('sex', form.errors)
        self.assertIn('postal_code', form.errors)
        self.assertIn('address1', form.errors)
        self.assertIn('address2', form.errors)
        self.assertIn('phone', form.errors)

    def test_kana_hiragana_to_katakana(self):
        """
        ひらがな入力時にカタカナへ変換される
        """
        form = StaffProfileForm(data={
            'name_last': '山田',
            'name_first': '太郎',
            'name_kana_last': 'やまだ',
            'name_kana_first': 'たろう',
            'birth_date': '2000-01-01',
            'sex': '1',
            'postal_code': '1234567',
            'address_kana': '',
            'address1': '東京都',
            'address2': '千代田区',
            'address3': '',
            'phone': '090-1234-5678',
        })
        valid = form.is_valid()
        self.assertTrue(valid)
        self.assertEqual(form.cleaned_data['name_kana_last'], 'ヤマダ')
        self.assertEqual(form.cleaned_data['name_kana_first'], 'タロウ')
