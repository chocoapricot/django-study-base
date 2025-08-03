
# 共通カナバリデーション/正規化
from apps.common.forms.fields import to_fullwidth_katakana, validate_kana
# forms.py
from django import forms
from django.forms import TextInput
from .models import Client
from django.core.exceptions import ValidationError
from stdnum.jp import cn as koujin

class ClientForm(forms.ModelForm):
    def clean_name_furigana(self):
        value = self.cleaned_data.get('name_furigana', '')
        validate_kana(value)
        value = to_fullwidth_katakana(value)
        return value

    def clean_corporate_number(self):
        corporate_number = self.cleaned_data.get('corporate_number')
        if not corporate_number:
            return corporate_number
        try:
            koujin.validate(corporate_number)
        except Exception as e:
            raise ValidationError(f'法人番号が正しくありません: {e}')
        return corporate_number

    regist_form_client = forms.ChoiceField(
        choices=[],
        label='登録区分',  # 日本語ラベル
        widget=forms.Select(attrs={'class':'form-select form-select-sm'}) ,
        required=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ここでのみDropdownsをimport.そうしないとmigrateでエラーになる
        from apps.system.settings.models import Dropdowns
        self.fields['regist_form_client'].choices = [
            (opt.value, opt.name)
            for opt in Dropdowns.objects.filter(active=True, category='regist_form_client').order_by('disp_seq')
        ]
    class Meta:
        model = Client
        fields = ['corporate_number','name','name_furigana',
                  'postal_code','address',  'url', 'memo', 'regist_form_client']
        widgets = {
            'corporate_number': forms.TextInput(attrs={'class': 'form-control form-control-sm',
                'pattern': '[0-9]{13}', 'inputmode': 'numeric', 'maxlength': '13', 'style': 'ime-mode:disabled;', 'autocomplete': 'off'}),
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'name_furigana': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control form-control-sm'
                ,'pattern': '[0-9]{7}', 'inputmode': 'numeric', 'minlength': '7', 'maxlength': '7', 'style': 'ime-mode:disabled;', 'autocomplete': 'off'}),
            'address': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            # 'phone': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            # 'email': forms.EmailInput(attrs={'class': 'form-control form-control-sm'}),
            'url': forms.URLInput(attrs={'class': 'form-control form-control-sm'}),
            'memo': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            # 'regist_form_code': forms.Select(attrs={'class': 'form-control form-control-sm form-select-sm'}),
        }


# クライアント連絡履歴フォーム
from .models import ClientContacted
class ClientContactedForm(forms.ModelForm):
    contact_type = forms.ChoiceField(
        choices=[],
        label='連絡種別',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.system.settings.models import Dropdowns
        self.fields['contact_type'].choices = [
            (opt.value, opt.name)
            for opt in Dropdowns.objects.filter(active=True, category='contact_type').order_by('disp_seq')
        ]

    class Meta:
        model = ClientContacted
        fields = ['contact_type', 'content', 'detail']
        widgets = {
            'content': forms.TextInput(attrs={'class': 'form-control'}),
            'detail': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }