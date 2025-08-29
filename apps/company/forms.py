from django import forms
from .models import Company, CompanyDepartment, CompanyUser
from stdnum.jp import cn as houjin
from django.core.exceptions import ValidationError

class CompanyForm(forms.ModelForm):
    def clean_phone_number(self):
        value = self.cleaned_data.get('phone_number', '')
        import re
        if value and not re.fullmatch(r'[0-9\-]+', value):
            raise forms.ValidationError('電話番号は数字とハイフンのみ入力してください。')
        return value
    class Meta:
        model = Company
        fields = ['name', 'corporate_number', 'representative', 'postal_code', 'address', 'phone_number']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'corporate_number': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'representative': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'address': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
        }
    
    def clean_corporate_number(self):
        corporate_number = self.cleaned_data.get('corporate_number')
        if not corporate_number:
            return corporate_number
        try:
            houjin.validate(corporate_number)
        except Exception as e:
            raise forms.ValidationError(f'法人番号が正しくありません: {e}')
        return corporate_number

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 初期値を保存して変更検知に使用
        if self.instance and self.instance.pk:
            self.initial_data = {
                field: getattr(self.instance, field) for field in self.fields
            }
        else:
            self.initial_data = {}
    
    def has_changed(self):
        """実際にデータが変更されたかどうかをチェック"""
        if not self.instance or not self.instance.pk:
            return True  # 新規作成の場合は常に変更ありとする
        
        for field_name in self.fields:
            initial_value = self.initial_data.get(field_name)
            current_value = self.cleaned_data.get(field_name)
            
            # 空文字列とNoneを同じものとして扱う
            if (initial_value or '') != (current_value or ''):
                return True
        
        return False

class CompanyDepartmentForm(forms.ModelForm):
    def clean_phone_number(self):
        value = self.cleaned_data.get('phone_number', '')
        import re
        if value and not re.fullmatch(r'[0-9\-]+', value):
            raise forms.ValidationError('電話番号は数字とハイフンのみ入力してください。')
        return value
    class Meta:
        model = CompanyDepartment
        fields = ['name', 'department_code', 'accounting_code', 'display_order', 'postal_code', 'address', 'phone_number', 'valid_from', 'valid_to']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'department_code': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'accounting_code': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'id': 'id_postal_code_dept'}),
            'address': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'id': 'id_address_dept'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'valid_from': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'valid_to': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 初期値を保存して変更検知に使用
        if self.instance and self.instance.pk:
            self.initial_data = {
                field: getattr(self.instance, field) for field in self.fields
            }
        else:
            self.initial_data = {}
    
    def has_changed(self):
        """実際にデータが変更されたかどうかをチェック"""
        if not self.instance or not self.instance.pk:
            return True  # 新規作成の場合は常に変更ありとする
        
        for field_name in self.fields:
            initial_value = self.initial_data.get(field_name)
            current_value = self.cleaned_data.get(field_name)
            
            # 空文字列とNoneを同じものとして扱う
            if (initial_value or '') != (current_value or ''):
                return True
        
        return False

from apps.common.forms.fields import to_fullwidth_katakana, validate_kana

class DepartmentChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        period_str = ""
        if obj.valid_from or obj.valid_to:
            start = obj.valid_from.strftime('%Y/%m/%d') if obj.valid_from else '無期限'
            end = obj.valid_to.strftime('%Y/%m/%d') if obj.valid_to else '無期限'
            period_str = f" ({start}～{end})"
        return f"{obj.name}{period_str}"

class CompanyUserForm(forms.ModelForm):
    department = DepartmentChoiceField(
        queryset=CompanyDepartment.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        label='所属部署',
    )

    def clean_phone_number(self):
        value = self.cleaned_data.get('phone_number', '')
        import re
        if value and not re.fullmatch(r'^[0-9\-]+$', value):
            raise forms.ValidationError('電話番号は半角数字とハイフンのみ入力してください。')
        return value

    def clean_name_kana_last(self):
        value = self.cleaned_data.get('name_kana_last', '')
        if not value:
            return value
        validate_kana(value)
        value = to_fullwidth_katakana(value)
        return value

    def clean_name_kana_first(self):
        value = self.cleaned_data.get('name_kana_first', '')
        if not value:
            return value
        validate_kana(value)
        value = to_fullwidth_katakana(value)
        return value

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['department'].queryset = CompanyDepartment.get_valid_departments()

    class Meta:
        model = CompanyUser
        fields = [
            'department', 'name_last', 'name_first', 'name_kana_last', 'name_kana_first',
            'position', 'phone_number', 'email', 'display_order'
        ]
        widgets = {
            'department': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'name_last': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'name_first': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'name_kana_last': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'name_kana_first': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'position': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'inputmode': 'numeric',
                'pattern': r'[0-9\-]*',
                'style': 'ime-mode:disabled;',
                'autocomplete': 'off',
            }),
            'email': forms.EmailInput(attrs={'class': 'form-control form-control-sm'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
        }
