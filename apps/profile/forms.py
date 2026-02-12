from django import forms
from django.core.exceptions import ValidationError
from .models import StaffProfile, StaffProfileMynumber, StaffProfileInternational, StaffProfileBank, StaffProfileDisability, StaffProfileContact, StaffProfilePayroll
from apps.common.forms import MyRadioSelect
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
        widget=MyRadioSelect(),
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


class StaffProfileMynumberForm(forms.ModelForm):
    """スタッフマイナンバーフォーム"""
    
    class Meta:
        model = StaffProfileMynumber
        fields = [
            'mynumber',
            'mynumber_card_front', 'mynumber_card_back',
            'identity_document_1', 'identity_document_2'
        ]
        widgets = {
            'mynumber': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'maxlength': '12',
                'pattern': '[0-9]{12}',
                'inputmode': 'numeric',
                'style': 'ime-mode:disabled;',
                'autocomplete': 'off'
            }),
            'mynumber_card_front': forms.FileInput(attrs={'class': 'form-control form-control-sm'}),
            'mynumber_card_back': forms.FileInput(attrs={'class': 'form-control form-control-sm'}),
            'identity_document_1': forms.FileInput(attrs={'class': 'form-control form-control-sm'}),
            'identity_document_2': forms.FileInput(attrs={'class': 'form-control form-control-sm'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 必須フィールドの設定
        self.fields['mynumber'].required = True
        # 添付ファイルは必須ではない
        self.fields['mynumber_card_front'].required = False
        self.fields['mynumber_card_back'].required = False
        self.fields['identity_document_1'].required = False
        self.fields['identity_document_2'].required = False
    
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
        fields = ['residence_card_number', 'residence_status', 'residence_period_from', 'residence_period_to', 'residence_card_front', 'residence_card_back']
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
            'residence_card_front': forms.FileInput(attrs={'class': 'form-control form-control-sm'}),
            'residence_card_back': forms.FileInput(attrs={'class': 'form-control form-control-sm'}),
        }
        labels = {
            'residence_card_number': '在留カード番号',
            'residence_status': '在留資格',
            'residence_period_from': '在留許可開始日',
            'residence_period_to': '在留期限',
            'residence_card_front': '在留カード（表面）',
            'residence_card_back': '在留カード（裏面）',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 必須フィールドの設定
        for field_name in ['residence_card_number', 'residence_status', 'residence_period_from', 'residence_period_to']:
            self.fields[field_name].required = True
    
    def clean(self):
        cleaned_data = super().clean()
        period_from = cleaned_data.get('residence_period_from')
        period_to = cleaned_data.get('residence_period_to')
        
        if period_from and period_to and period_from >= period_to:
            raise forms.ValidationError('在留許可開始日は在留期限より前の日付を入力してください。')
        
        return cleaned_data


class StaffProfileBankForm(forms.ModelForm):
    """スタッフ銀行プロフィールフォーム"""
    bank_name = forms.CharField(
        label='銀行名',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': '銀行名を入力'})
    )
    branch_name = forms.CharField(
        label='支店名',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': '支店名を入力'})
    )
    account_type = forms.ChoiceField(
        choices=[],
        label='口座種別',
        widget=MyRadioSelect(),
    )

    class Meta:
        model = StaffProfileBank
        fields = [
            'bank_code', 'branch_code', 'account_type',
            'account_number', 'account_holder', 'document_file'
        ]
        widgets = {
            'bank_code': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '4'}),
            'branch_code': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '3'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '8'}),
            'account_holder': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'document_file': forms.FileInput(attrs={'class': 'form-control form-control-sm'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.system.settings.models import Dropdowns
        self.fields['account_type'].choices = [
            (opt.value, opt.name)
            for opt in Dropdowns.objects.filter(active=True, category='bank_account_type').order_by('disp_seq')
        ]
        self.fields['bank_code'].required = True
        self.fields['branch_code'].required = True
        self.fields['account_type'].required = True
        self.fields['account_number'].required = True
        self.fields['account_holder'].required = True
        self.fields['document_file'].required = False
        if self.instance and self.instance.pk:
            self.fields['bank_name'].initial = self.instance.bank_name
            self.fields['branch_name'].initial = self.instance.branch_name

    def clean_bank_code(self):
        bank_code = self.cleaned_data.get('bank_code')
        if bank_code:
            from apps.master.models import Bank
            if not Bank.objects.filter(bank_code=bank_code, is_active=True).exists():
                raise ValidationError("存在しない銀行コードです。")
        return bank_code

    def clean_branch_code(self):
        branch_code = self.cleaned_data.get('branch_code')
        # bank_code がないと検証できないので、ここでは何もしない
        # clean メソッドで bank_code と合わせて検証する
        return branch_code

    def clean(self):
        cleaned_data = super().clean()
        bank_code = cleaned_data.get('bank_code')
        branch_code = cleaned_data.get('branch_code')

        if bank_code and branch_code:
            from apps.master.models import Bank, BankBranch
            try:
                bank = Bank.objects.get(bank_code=bank_code, is_active=True)
                if not BankBranch.objects.filter(bank=bank, branch_code=branch_code, is_active=True).exists():
                    self.add_error('branch_code', "存在しない支店コードです。")
            except Bank.DoesNotExist:
                # clean_bank_code で既にエラーが出ているはずなので、ここでは何もしない
                pass

        return cleaned_data

    def save(self, commit=True):
        # bank_name と branch_name をDBに保存しないようにする
        self.cleaned_data.pop('bank_name', None)
        self.cleaned_data.pop('branch_name', None)
        return super().save(commit)


class StaffProfileDisabilityForm(forms.ModelForm):
    """スタッフ障害者情報フォーム"""
    disability_type = forms.ChoiceField(
        label='障害の種類',
        widget=MyRadioSelect(),
        choices=[],
        required=True,
    )

    class Meta:
        model = StaffProfileDisability
        fields = [
            'disability_type', 'disability_grade'
        ]
        widgets = {
            'disability_grade': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.system.settings.models import Dropdowns
        self.fields['disability_type'].choices = [
            (opt.value, opt.name)
            for opt in Dropdowns.objects.filter(active=True, category='disability_type').order_by('disp_seq')
        ]


class StaffProfileContactForm(forms.ModelForm):
    """スタッフ連絡先情報フォーム"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['emergency_contact'].required = True
        self.fields['relationship'].required = True

    class Meta:
        model = StaffProfileContact
        fields = [
            'emergency_contact', 'relationship', 'postal_code',
            'address1', 'address2', 'address3'
        ]
        widgets = {
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'relationship': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '7'}),
            'address1': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'address2': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'address3': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
        }

    def clean_postal_code(self):
        """郵便番号のバリデーション"""
        postal_code = self.cleaned_data.get('postal_code')
        if postal_code:
            if not postal_code.isdigit() or len(postal_code) != 7:
                raise forms.ValidationError("郵便番号は7桁の数字で入力してください。")
        return postal_code


class StaffProfilePayrollForm(forms.ModelForm):
    """スタッフ給与プロフィールフォーム"""
    class Meta:
        model = StaffProfilePayroll
        fields = ['basic_pension_number']
        widgets = {
            'basic_pension_number': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'maxlength': '12',
                'placeholder': '123-456-7890',
                'style': 'ime-mode:disabled;',
                'autocomplete': 'off'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['basic_pension_number'].required = True
