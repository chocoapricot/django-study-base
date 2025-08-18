from django.test import TestCase
from apps.staff.forms import StaffForm

from apps.system.settings.models import Dropdowns

class StaffFormPhoneKanaTest(TestCase):
    def setUp(self):
        Dropdowns.objects.create(category='regist_form', value='1', name='正社員', disp_seq=1, active=True)
        Dropdowns.objects.create(category='sex', value='1', name='男性', disp_seq=1, active=True)
    def test_phone_rejects_alpha(self):
        # 電話番号に英字が含まれる場合はバリデーションエラー
        form = StaffForm(data={
            'regist_form_code': '1',
            'employee_no': 'EMP005',
            'name_last': '山田',
            'name_first': '太郎',
            'name_kana_last': 'ヤマダ',
            'name_kana_first': 'タロウ',
            'birth_date': '2000-01-01',
            'sex': '1',
            'hire_date': '2020-04-01',
            'postal_code': '1000001',
            'address1': '東京都',
            'phone': '03-1234-ABCD',
            'email': 'test@example.com',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)

    def test_kana_validation_and_conversion(self):
        # ひらがな→エラー、半角カナ→全角カナに変換
        form = StaffForm(data={
            'regist_form_code': '1',
            'employee_no': 'EMP006',
            'name_last': '山田',
            'name_first': '太郎',
            'name_kana_last': 'やまだ',
            'name_kana_first': 'ﾀﾛｳ',
            'birth_date': '2000-01-01',
            'sex': '1',
            'hire_date': '2020-04-01',
            'postal_code': '1000001',
            'address1': '東京都',
            'phone': '03-1234-5678',
            'email': 'test@example.com',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('name_kana_last', form.errors)
