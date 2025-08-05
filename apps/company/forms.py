from django import forms
from .models import Company, CompanyDepartment
from stdnum.util import get_cc_module

jp_corporate_number = get_cc_module('jp', 'corporate_number')

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'corporate_number', 'postal_code', 'address', 'phone_number', 'url']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'corporate_number': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'address': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'url': forms.URLInput(attrs={'class': 'form-control form-control-sm'}),
        }
    
    def clean_corporate_number(self):
        corporate_number = self.cleaned_data.get('corporate_number')
        if corporate_number and jp_corporate_number and not jp_corporate_number.is_valid(corporate_number):
            raise forms.ValidationError("有効な法人番号ではありません。")
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
