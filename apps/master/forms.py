from django import forms
from .models import Qualification, Skill, BillPayment, BillBank


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
    """支払いサイトフォーム"""
    
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
    """振込先銀行フォーム"""
    
    class Meta:
        model = BillBank
        fields = ['name', 'bank_code', 'branch_name', 'branch_code', 'account_type', 'account_number', 'account_holder', 'account_holder_kana', 'is_active', 'display_order']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'bank_code': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '4', 'pattern': '[0-9]{4}'}),
            'branch_name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'branch_code': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '3', 'pattern': '[0-9]{3}'}),
            'account_type': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '8', 'pattern': '[0-9]{1,8}'}),
            'account_holder': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'account_holder_kana': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
        }
        labels = {
            'bank_code': '銀行コード（4桁）',
            'branch_code': '支店コード（3桁）',
            'account_holder_kana': '口座名義（カナ）',
        }
        help_texts = {
            'bank_code': '4桁の数字で入力してください（任意）',
            'branch_code': '3桁の数字で入力してください（任意）',
            'account_number': '1-8桁の数字で入力してください',
        }