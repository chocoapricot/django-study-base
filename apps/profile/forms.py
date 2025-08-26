from django import forms
from django.core.exceptions import ValidationError
from .models import StaffProfile, ProfileMynumber, StaffProfileInternational, StaffBankProfile, StaffDisabilityProfile, StaffContact


from apps.common.forms.fields import to_fullwidth_katakana, validate_kana

class StaffProfileForm(forms.ModelForm):
    def save(self, commit=True, user=None):
        instance = super().save(commit=False)
        if user is not None:
            instance.user = user
        if commit:
            instance.save()
        return instance
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
        widget=forms.RadioSelect,
        required=False,  # __init__で必須化
    )
    
    class Meta:
        model = StaffProfile
        fields = [
            'name_last', 'name_first', 'name_kana_last', 'name_kana_first',
            'birth_date', 'sex', 'postal_code',
            'address1', 'address2', 'address3', 'phone'
        ]
        widgets = {
            'name_last': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'name_first': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'name_kana_last': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'name_kana_first': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '7'}),
            'address1': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'address2': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'address3': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'phone': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'inputmode': 'numeric',
                'pattern': r'[0-9\-]*',
                'style': 'ime-mode:disabled;',
                'autocomplete': 'off',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dropdownsから性別の選択肢を取得
        from apps.system.settings.models import Dropdowns
        self.fields['sex'].choices = [
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


class ProfileMynumberForm(forms.ModelForm):
    """スタッフマイナンバーフォーム"""
    
    class Meta:
        model = ProfileMynumber
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


class StaffProfileInternationalForm(forms.ModelForm):
    """スタッフ外国籍プロフィールフォーム"""
    
    class Meta:
        model = StaffProfileInternational
        fields = ['residence_card_number', 'residence_status', 'residence_period_from', 'residence_period_to']
        widgets = {
            'residence_card_number': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': '在留カード番号を入力してください'
            }),
            'residence_status': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': '在留資格を入力してください'
            }),
            'residence_period_from': forms.DateInput(attrs={
                'class': 'form-control form-control-sm',
                'type': 'date'
            }),
            'residence_period_to': forms.DateInput(attrs={
                'class': 'form-control form-control-sm',
                'type': 'date'
            }),
        }
        labels = {
            'residence_card_number': '在留カード番号',
            'residence_status': '在留資格',
            'residence_period_from': '在留許可開始日',
            'residence_period_to': '在留期限',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 必須フィールドの設定
        for field_name in self.fields:
            self.fields[field_name].required = True
    
    def clean(self):
        cleaned_data = super().clean()
        period_from = cleaned_data.get('residence_period_from')
        period_to = cleaned_data.get('residence_period_to')
        
        if period_from and period_to and period_from >= period_to:
            raise forms.ValidationError('在留許可開始日は在留期限より前の日付を入力してください。')
        
        return cleaned_data


class StaffBankProfileForm(forms.ModelForm):
    """スタッフ銀行プロフィールフォーム"""
    account_type = forms.ChoiceField(
        choices=[],
        label='口座種別',
        widget=forms.RadioSelect,
    )

    class Meta:
        model = StaffBankProfile
        fields = [
            'bank_code', 'branch_code', 'account_type',
            'account_number', 'account_holder'
        ]
        widgets = {
            'bank_code': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '4'}),
            'branch_code': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '3'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '8'}),
            'account_holder': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.system.settings.models import Dropdowns
        self.fields['account_type'].choices = [
            (opt.value, opt.name)
            for opt in Dropdowns.objects.filter(active=True, category='bank_account_type').order_by('disp_seq')
        ]
        self.fields['account_type'].required = True
        self.fields['account_number'].required = True
        self.fields['account_holder'].required = True


class StaffDisabilityProfileForm(forms.ModelForm):
    """スタッフ障害者情報フォーム"""
    disability_type = forms.ChoiceField(
        label='障害の種類',
        widget=forms.RadioSelect,
        choices=[],
        required=False,
    )

    class Meta:
        model = StaffDisabilityProfile
        fields = [
            'disability_type', 'disability_grade', 'notes'
        ]
        widgets = {
            'disability_grade': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'notes': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.system.settings.models import Dropdowns
        self.fields['disability_type'].choices = [
            ('', '選択しない')
        ] + [
            (opt.value, opt.name)
            for opt in Dropdowns.objects.filter(active=True, category='disability_type').order_by('disp_seq')
        ]


class StaffContactForm(forms.ModelForm):
    """スタッフ連絡先情報フォーム"""

    class Meta:
        model = StaffContact
        fields = [
            'phone', 'email', 'notes'
        ]
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'inputmode': 'numeric',
                'pattern': r'[0-9\-]*',
                'style': 'ime-mode:disabled;',
                'autocomplete': 'off',
            }),
            'email': forms.EmailInput(attrs={'class': 'form-control form-control-sm'}),
            'notes': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
        }
