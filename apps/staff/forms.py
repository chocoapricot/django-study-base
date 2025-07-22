# forms.py
from django import forms
from django.forms import TextInput
from .models import Staff, StaffContacted
# スタッフ連絡履歴フォーム
class StaffContactedForm(forms.ModelForm):
    contact_type = forms.ChoiceField(
        choices=[],
        label='連絡種別',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.system.dropdowns.models import Dropdowns
        self.fields['contact_type'].choices = [
            (opt.value, opt.name)
            for opt in Dropdowns.objects.filter(active=True, category='contact_type').order_by('disp_seq')
        ]

    class Meta:
        model = StaffContacted
        fields = ['contact_type', 'content', 'detail']
        widgets = {
            'content': forms.TextInput(attrs={'class': 'form-control'}),
            'detail': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


import re

def to_fullwidth_katakana(text):
    # ひらがな→カタカナ
    text = re.sub(r'[ぁ-ん]', lambda m: chr(ord(m.group(0)) + 0x60), text)
    # 半角カタカナ→全角カタカナ
    # 半角カタカナunicode: FF66-FF9D, FF9E, FF9F, 30FC, 3099, 309A
    import unicodedata
    text = unicodedata.normalize('NFKC', text)
    return text

def validate_kana(value):
    # カタカナ・ひらがなのみ許可
    if not re.fullmatch(r'[\u30A0-\u30FF\u3040-\u309Fー\uFF9E\uFF9F\u3099\u309A]+', value):
        raise forms.ValidationError('カナはカタカナまたはひらがなのみ入力してください。')

class StaffForm(forms.ModelForm):
    def clean_name_kana_last(self):
        value = self.cleaned_data.get('name_kana_last', '')
        validate_kana(value)
        value = to_fullwidth_katakana(value)
        return value

    def clean_name_kana_first(self):
        value = self.cleaned_data.get('name_kana_first', '')
        validate_kana(value)
        value = to_fullwidth_katakana(value)
        return value

    sex = forms.ChoiceField(
        choices=[],
        label='性別',  # 日本語ラベル
        required=True,
        #widget=forms.RadioSelect(attrs={'class':'form-check form-check-inline'}),  # ここでラジオボタンを指定(⇒立て並びにしかできない！)
        widget=forms.RadioSelect  # ここでラジオボタンを指定(⇒立て並びにしかできない！)
    )

    regist_form_code = forms.ChoiceField(
        choices=[],
        label='登録区分',  # 日本語ラベル
        widget=forms.Select(attrs={'class':'form-select form-select-sm'}) ,
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ここでのみDropdownsをimport.そうしないとmigrateでエラーになる
        from apps.system.dropdowns.models import Dropdowns
        self.fields['sex'].choices = [
            (opt.value, opt.name)
            for opt in Dropdowns.objects.filter(active=True, category='sex').order_by('disp_seq')
        ]
        self.fields['regist_form_code'].choices = [
            (opt.value, opt.name)
            for opt in Dropdowns.objects.filter(active=True, category='regist_form').order_by('disp_seq')
        ]
    class Meta:
        model = Staff
        fields = [
            'name_last','name_first','name_kana_last','name_kana_first',
            'birth_date','sex',
            # 'age', ← ここは除外
            'postal_code','address1','address2','address3', 'phone', 'email', 'regist_form_code'
        ]
        widgets = {
            'name_last': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'name_first': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'name_kana_last': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'name_kana_first': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            #'sex': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            #'age': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'pattern': '[0-9]{7}', 'inputmode': 'numeric', 'minlength': '7', 'maxlength': '7', 'style': 'ime-mode:disabled;', 'autocomplete': 'off'
            }),
            'address1': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'address2': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'address3': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'phone': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'email': forms.EmailInput(attrs={'class': 'form-control form-control-sm'}),
            # 'regist_form_code': forms.Select(attrs={'class': 'form-control form-control-sm form-select-sm'}),
        }
