from django import forms
from django.core.exceptions import ValidationError
from .models import (
    Qualification,
    Skill,
    BillPayment,
    BillBank,
    Bank,
    BankBranch,
    Information,
    JobCategory,
    StaffAgreement,
    MailTemplate,
    ContractPattern,
    ContractTerms,
    MinimumPay,
    BusinessContent,
    HakenResponsibilityDegree,
    DefaultValue,
    EmploymentType,
)
from apps.system.settings.models import Dropdowns
from apps.common.constants import Constants


class BusinessContentForm(forms.ModelForm):
    """業務内容フォーム"""
    class Meta:
        model = BusinessContent
        fields = ['content', 'display_order', 'is_active']
        widgets = {
            'content': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 5}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class HakenResponsibilityDegreeForm(forms.ModelForm):
    """派遣責任程度フォーム"""
    class Meta:
        model = HakenResponsibilityDegree
        fields = ['content', 'display_order', 'is_active']
        widgets = {
            'content': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class EmploymentTypeForm(forms.ModelForm):
    """雇用形態フォーム"""
    class Meta:
        model = EmploymentType
        fields = ['name', 'display_order', 'is_fixed_term', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'is_fixed_term': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class MailTemplateForm(forms.ModelForm):
    """メールテンプレートフォーム"""

    class Meta:
        model = MailTemplate
        fields = ["subject", "body", "remarks"]
        widgets = {
            "subject": forms.TextInput(attrs={"class": "form-control form-control-sm"}),
            "body": forms.Textarea(
                attrs={"class": "form-control form-control-sm", "rows": 10}
            ),
            "remarks": forms.Textarea(
                attrs={"class": "form-control form-control-sm", "rows": 3}
            ),
        }


class CustomModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.value}: {obj.name}"


class JobCategoryForm(forms.ModelForm):
    """職種マスタフォーム"""
    jobs_kourou = CustomModelChoiceField(
        queryset=Dropdowns.objects.filter(category='jobs_kourou', active=True),
        required=False,
        label='職業分類(厚労省)',
        empty_label='選択してください',
        widget=forms.Select(attrs={'class': 'form-control form-control-sm'})
    )
    jobs_soumu = CustomModelChoiceField(
        queryset=Dropdowns.objects.filter(category='jobs_soumu', active=True),
        required=False,
        label='職業分類(総務省)',
        empty_label='選択してください',
        widget=forms.Select(attrs={'class': 'form-control form-control-sm'})
    )

    class Meta:
        model = JobCategory
        fields = ['name', 'is_manufacturing_dispatch', 'jobs_kourou', 'jobs_soumu', 'display_order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'is_manufacturing_dispatch': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class MinimumPayForm(forms.ModelForm):
    """最低賃金フォーム"""
    class Meta:
        model = MinimumPay
        fields = ['pref', 'start_date', 'hourly_wage', 'is_active', 'display_order']
        widgets = {
            'start_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'hourly_wage': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pref_choices = [
            ('', '選択してください')
        ]
        pref_choices.extend([
            (d.value, f"{d.value}:{d.name}") for d in Dropdowns.objects.filter(category='pref', active=True).order_by('disp_seq')
        ])
        self.fields['pref'] = forms.ChoiceField(
            choices=pref_choices,
            label='都道府県',
            widget=forms.Select(attrs={'class': 'form-control form-control-sm'})
        )


class ContractPatternForm(forms.ModelForm):
    """契約書パターンフォーム"""
    class Meta:
        model = ContractPattern
        fields = ['name', 'domain', 'contract_type_code', 'employment_type', 'memo', 'display_order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'domain': forms.RadioSelect(),
            'contract_type_code': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'employment_type': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'memo': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 契約種別の選択肢（クライアント用）
        self.fields['contract_type_code'] = forms.ChoiceField(
            label='契約種別',
            choices=[('', '---------')] + [
                (d.value, d.name) for d in Dropdowns.objects.filter(category='client_contract_type', active=True)
            ],
            required=False,
            widget=forms.Select(attrs={'class': 'form-control form-control-sm'})
        )
        
        # 雇用形態の選択肢（スタッフ用）
        self.fields['employment_type'] = forms.ChoiceField(
            label='雇用形態',
            choices=[('', '---------')] + [
                (d.value, d.name) for d in Dropdowns.objects.filter(category='employment_type', active=True)
            ],
            required=False,
            widget=forms.Select(attrs={'class': 'form-control form-control-sm'})
        )

    def clean(self):
        cleaned_data = super().clean()
        domain = cleaned_data.get('domain')
        contract_type_code = cleaned_data.get('contract_type_code')
        employment_type = cleaned_data.get('employment_type')

        if domain == Constants.DOMAIN.CLIENT:  # クライアント
            if not contract_type_code:
                self.add_error('contract_type_code', 'クライアントが対象の場合、契約種別は必須です。')
            # クライアントの場合は雇用形態をクリア
            cleaned_data['employment_type'] = None
        else:  # スタッフ
            # スタッフの場合は契約種別をクリア
            cleaned_data['contract_type_code'] = None

        return cleaned_data


class ContractTermForm(forms.ModelForm):
    """契約文言フォーム"""
    def __init__(self, *args, **kwargs):
        # The validation logic needs the contract_pattern instance.
        # It's passed from the view during form instantiation.
        self.contract_pattern = kwargs.pop('contract_pattern', None)
        super().__init__(*args, **kwargs)
        # For update, the pattern is on the instance.
        if self.instance and self.instance.pk:
            self.contract_pattern = self.instance.contract_pattern

    class Meta:
        model = ContractTerms
        fields = ['contract_clause', 'contract_terms', 'display_position', 'memo', 'display_order']
        widgets = {
            'contract_clause': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'contract_terms': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 5}),
            'display_position': forms.RadioSelect,
            'memo': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        display_position = cleaned_data.get('display_position')

        if not self.contract_pattern:
            # This validation cannot proceed without the contract pattern.
            # This can happen if the view doesn't pass it.
            return cleaned_data

        # Preamble (1) and Postscript (3) should be unique per contract pattern.
        if display_position in [1, 3]:
            query = ContractTerms.objects.filter(
                contract_pattern=self.contract_pattern,
                display_position=display_position
            )
            # When updating, exclude the current instance from the check.
            if self.instance and self.instance.pk:
                query = query.exclude(pk=self.instance.pk)

            if query.exists():
                position_name = dict(self.Meta.model.POSITION_CHOICES).get(display_position)
                raise ValidationError(f'この契約書パターンにはすでに「{position_name}」が登録されています。')

        return cleaned_data


class QualificationCategoryForm(forms.ModelForm):
    """資格カテゴリフォーム"""
    
    class Meta:
        model = Qualification
        fields = ['name', 'description', 'is_active', 'display_order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'description': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # カテゴリフォームの場合、インスタンスにlevelを設定
        if self.instance:
            self.instance.level = 1
            self.instance.parent = None
    
    def save(self, commit=True):
        """カテゴリとして保存"""
        instance = super().save(commit=False)
        instance.level = 1  # カテゴリ
        instance.parent = None
        if commit:
            # カテゴリの場合はバリデーションをスキップ
            instance.save(skip_validation=True)
        return instance


class QualificationForm(forms.ModelForm):
    """資格フォーム"""
    
    class Meta:
        model = Qualification
        fields = ['name', 'parent', 'description', 'is_active', 'display_order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'parent': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'description': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 親カテゴリの選択肢をカテゴリ（level=1）のみに限定
        self.fields['parent'].queryset = Qualification.objects.filter(level=1, is_active=True).order_by('display_order', 'name')
        self.fields['parent'].empty_label = "カテゴリを選択してください"
        self.fields['parent'].required = True
    
    def save(self, commit=True):
        """資格として保存"""
        instance = super().save(commit=False)
        instance.level = 2  # 資格
        if commit:
            # 資格の場合は通常のバリデーションを実行
            instance.save()
        return instance
    
    def clean(self):
        """フォームレベルのバリデーション"""
        cleaned_data = super().clean()
        parent = cleaned_data.get('parent')
        if not parent:
            raise forms.ValidationError('資格は親カテゴリが必要です。')
        return cleaned_data


class SkillCategoryForm(forms.ModelForm):
    """技能カテゴリフォーム"""
    
    class Meta:
        model = Skill
        fields = ['name', 'description', 'is_active', 'display_order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'description': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # カテゴリフォームの場合、インスタンスにlevelを設定
        if self.instance:
            self.instance.level = 1
            self.instance.parent = None
    
    def save(self, commit=True):
        """カテゴリとして保存"""
        instance = super().save(commit=False)
        instance.level = 1  # カテゴリ
        instance.parent = None
        if commit:
            # カテゴリの場合はバリデーションをスキップ
            instance.save(skip_validation=True)
        return instance
    
    def clean(self):
        """フォームレベルのバリデーション"""
        cleaned_data = super().clean()
        # カテゴリフォームでは特別なバリデーションは不要
        return cleaned_data


class SkillForm(forms.ModelForm):
    """技能フォーム"""
    
    class Meta:
        model = Skill
        fields = ['name', 'parent', 'description', 'is_active', 'display_order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'parent': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'description': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 親カテゴリの選択肢をカテゴリ（level=1）のみに限定
        self.fields['parent'].queryset = Skill.objects.filter(level=1, is_active=True).order_by('display_order', 'name')
        self.fields['parent'].empty_label = "カテゴリを選択してください"
        self.fields['parent'].required = True
    
    def save(self, commit=True):
        """技能として保存"""
        instance = super().save(commit=False)
        instance.level = 2  # 技能
        if commit:
            # 技能の場合は通常のバリデーションを実行
            instance.save()
        return instance
    
    def clean(self):
        """フォームレベルのバリデーション"""
        cleaned_data = super().clean()
        parent = cleaned_data.get('parent')
        if not parent:
            raise forms.ValidationError('技能は親カテゴリが必要です。')
        return cleaned_data


class BillPaymentForm(forms.ModelForm):
    """支払条件フォーム"""
    
    class Meta:
        model = BillPayment
        fields = ['name', 'closing_day', 'invoice_months_after', 'invoice_day', 'payment_months_after', 'payment_day', 'is_active', 'display_order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'closing_day': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '1', 'max': '31'}),
            'invoice_months_after': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'invoice_day': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '1', 'max': '31'}),
            'payment_months_after': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'payment_day': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '1', 'max': '31'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
        }
        labels = {
            'closing_day': '締め日（月末の場合は31）',
            'invoice_months_after': '請求書提出月数（締め日から何か月後）',
            'invoice_day': '請求書必着日',
            'payment_months_after': '支払い月数（締め日から何か月後）',
            'payment_day': '支払い日',
        }
        help_texts = {
            'closing_day': '月末締めの場合は31を入力してください',
            'invoice_months_after': '締め日から何か月後に請求書を提出するか',
            'payment_months_after': '締め日から何か月後に支払いが行われるか',
        }


class BillBankForm(forms.ModelForm):
    """会社銀行フォーム"""
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

    class Meta:
        model = BillBank
        fields = [
            'bank_code', 'branch_code', 'account_type', 'account_number',
            'account_holder', 'account_holder_kana', 'is_active', 'display_order'
        ]
        widgets = {
            'bank_code': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '4'}),
            'branch_code': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '3'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '8'}),
            'account_holder': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'account_holder_kana': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 口座種別の選択肢をDropdownsから取得
        account_type_choices = [
            (d.value, d.name) for d in Dropdowns.objects.filter(category='bank_account_type', active=True).order_by('disp_seq')
        ]
        self.fields['account_type'] = forms.ChoiceField(
            choices=account_type_choices,
            label='口座種別',
            widget=forms.RadioSelect
        )
        self.fields['bank_code'].required = True
        self.fields['branch_code'].required = True
        self.fields['account_type'].required = True
        self.fields['account_number'].required = True
        self.fields['account_holder'].required = True
        self.fields['account_holder_kana'].required = True

        if self.instance and self.instance.pk:
            self.fields['bank_name'].initial = self.instance.bank_name
            self.fields['branch_name'].initial = self.instance.branch_name

    def clean_bank_code(self):
        bank_code = self.cleaned_data.get('bank_code')
        if bank_code:
            if not Bank.objects.filter(bank_code=bank_code, is_active=True).exists():
                raise ValidationError("存在しない銀行コードです。")
        return bank_code

    def clean(self):
        cleaned_data = super().clean()
        bank_code = cleaned_data.get('bank_code')
        branch_code = cleaned_data.get('branch_code')

        if bank_code and branch_code:
            try:
                bank = Bank.objects.get(bank_code=bank_code, is_active=True)
                if not BankBranch.objects.filter(bank=bank, branch_code=branch_code, is_active=True).exists():
                    self.add_error('branch_code', "存在しない支店コードです。")
            except Bank.DoesNotExist:
                pass
        return cleaned_data

    def save(self, commit=True):
        self.cleaned_data.pop('bank_name', None)
        self.cleaned_data.pop('branch_name', None)
        return super().save(commit)


class BankForm(forms.ModelForm):
    """銀行フォーム"""
    
    class Meta:
        model = Bank
        fields = ['name', 'bank_code', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'bank_code': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '4', 'pattern': '[0-9]{4}'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'bank_code': '銀行コード（4桁）',
        }
        help_texts = {
            'bank_code': '4桁の数字で入力してください（必須）',
        }


class BankBranchForm(forms.ModelForm):
    """銀行支店フォーム"""
    
    class Meta:
        model = BankBranch
        fields = ['bank', 'name', 'branch_code', 'is_active']


class CSVImportForm(forms.Form):
    """CSV取込フォーム"""
    csv_file = forms.FileField(
        label='CSVファイル',
        help_text='CSVファイルを選択してください。',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control form-control-sm'})
    )


class InformationForm(forms.ModelForm):
    """お知らせ情報フォーム"""
    target = forms.ChoiceField(
        label='対象',
        widget=forms.RadioSelect,
        choices=()
    )

    class Meta:
        model = Information
        fields = ['target', 'subject', 'content', 'start_date', 'end_date']
        widgets = {
            'subject': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'content': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 5}),
            'start_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['target'].choices = [(d.value, d.name) for d in Dropdowns.objects.filter(category='domain', active=True)]


class StaffAgreementForm(forms.ModelForm):
    """スタッフ同意文言フォーム"""
    class Meta:
        model = StaffAgreement
        fields = ['name', 'agreement_text', 'display_order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'agreement_text': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 10}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class DefaultValueForm(forms.ModelForm):
    """初期値マスタフォーム"""
    class Meta:
        model = DefaultValue
        fields = ['target_item', 'format', 'value']
        widgets = {
            'target_item': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'readonly': 'readonly'}),
            'format': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'value': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['format'].widget.attrs['disabled'] = True
            if self.instance.format == 'text':
                self.fields['value'].widget.attrs.update({
                    'rows': '1',
                    'style': 'resize: none;'
                })