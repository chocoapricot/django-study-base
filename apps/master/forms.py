from django import forms
from .models import Qualification, Skill


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