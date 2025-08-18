from django.test import TestCase
from apps.profile.forms import StaffProfileForm

from apps.system.settings.models import Dropdowns

class StaffProfileFormTest(TestCase):
    def setUp(self):
        Dropdowns.objects.create(category='sex', value='1', name='男性', disp_seq=1, active=True)
    def test_kana_validation(self):
        # カナがひらがな→エラー
        form = StaffProfileForm(data={
            'name_last': '山田',
            'name_first': '太郎',
            'name_kana_last': 'やまだ',
            'name_kana_first': 'たろう',
            'birth_date': '2000-01-01',
            'sex': '',
            'postal_code': '1234567',
            'address_kana': '',
            'address1': '',
            'address2': '',
            'address3': '',
            'phone': '090-1234-5678',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('name_kana_last', form.errors)
        self.assertIn('name_kana_first', form.errors)

    def test_kana_fullwidth_conversion(self):
        # 半角カナ→全角カナに変換される
        form = StaffProfileForm(data={
            'name_last': '山田',
            'name_first': '太郎',
            'name_kana_last': 'ﾔﾏﾀﾞ',
            'name_kana_first': 'ﾀﾛｳ',
            'birth_date': '2000-01-01',
            'sex': '',
            'postal_code': '1234567',
            'address_kana': '',
            'address1': '',
            'address2': '',
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
