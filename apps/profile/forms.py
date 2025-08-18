from django import forms
from django.core.exceptions import ValidationError
from .models import StaffProfile, StaffMynumber


from apps.common.forms.fields import to_fullwidth_katakana, validate_kana

class StaffProfileForm(forms.ModelForm):
    def clean_phone(self):
        value = self.cleaned_data.get('phone', '')
        import re
        # 半角数字・ハイフンのみ許可（全角数字不可）
        if value and not re.fullmatch(r'^[0-9\-]+$', value):
            raise forms.ValidationError('電話番号は半角数字とハイフンのみ入力してください。')
        return value
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
    """スタッフプロフィールフォーム"""
    sex = forms.ChoiceField(
        choices=[],
        label='性別',
        widget=forms.Select(attrs={'class': 'form-control form-control-sm'}),
        required=False,  # __init__で必須化
    )
    
    class Meta:
        model = StaffProfile
        fields = [
            'name_last', 'name_first', 'name_kana_last', 'name_kana_first',
            'birth_date', 'sex', 'postal_code', 'address_kana',
            'address1', 'address2', 'address3', 'phone'
        ]
        widgets = {
            'name_last': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'name_first': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'name_kana_last': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'name_kana_first': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '7'}),
            'address_kana': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'address1': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'address2': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'address3': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'phone': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'inputmode': 'numeric',
                'pattern': '[0-9\-]*',
                'style': 'ime-mode:disabled;',
                'autocomplete': 'off',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dropdownsから性別の選択肢を取得
        from apps.system.settings.models import Dropdowns
        self.fields['sex'].choices = [('', '選択してください')] + [
            (opt.value, opt.name)
            for opt in Dropdowns.objects.filter(active=True, category='sex').order_by('disp_seq')
        ]
        # 必須フィールドの設定
        self.fields['name_last'].required = True
        self.fields['name_first'].required = True
        self.fields['name_kana_last'].required = True
        self.fields['name_kana_first'].required = True
        self.fields['birth_date'].required = True
        self.fields['sex'].required = True
        self.fields['postal_code'].required = True
        self.fields['address1'].required = True  # 都道府県
        self.fields['address2'].required = True  # 市区町村
        self.fields['phone'].required = True


class StaffMynumberForm(forms.ModelForm):
    """スタッフマイナンバーフォーム"""
    
    class Meta:
        model = StaffMynumber
        fields = ['mynumber']
        widgets = {
            'mynumber': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'maxlength': '12',
                'pattern': '[0-9]{12}',
                'inputmode': 'numeric',
                'style': 'ime-mode:disabled;',
                'autocomplete': 'off'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 必須フィールドの設定
        self.fields['mynumber'].required = True
    
    def clean_mynumber(self):
        """マイナンバーのバリデーション"""
        mynumber = self.cleaned_data.get('mynumber')
        if mynumber:
            try:
                from stdnum.jp import in_
                # マイナンバーの形式と検査数字をチェック
                if not in_.is_valid(mynumber):
                    raise ValidationError('正しいマイナンバーを入力してください。')
                # 正規化（ハイフンなどを除去）
                mynumber = in_.compact(mynumber)
            except ImportError:
                # python-stdnumがインストールされていない場合は基本的なチェックのみ
                import re
                if not re.match(r'^\d{12}$', mynumber):
                    raise ValidationError('マイナンバーは12桁の数字で入力してください。')
            except Exception:
                raise ValidationError('正しいマイナンバーを入力してください。')
        
        return mynumber