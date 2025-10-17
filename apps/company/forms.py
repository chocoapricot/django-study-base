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
        fields = ['name', 'corporate_number', 'representative', 'postal_code', 'address', 'phone_number', 'haken_permit_number', 'shokai_permit_number', 'foreign_regist_number']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'corporate_number': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'representative': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'address': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'haken_permit_number': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'shokai_permit_number': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'foreign_regist_number': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
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
        fields = ['name', 'corporate_number', 'department_code', 'accounting_code', 'display_order', 'postal_code', 'address', 'phone_number', 'valid_from', 'valid_to']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'corporate_number': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
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

class CompanyUserForm(forms.ModelForm):
    department_code = forms.ChoiceField(
        label='部署',
        required=False,
        widget=forms.Select(attrs={'class': 'form-control form-control-sm'})
    )

    def __init__(self, *args, **kwargs):
        corporate_number = kwargs.pop('corporate_number', None)
        super().__init__(*args, **kwargs)

        choices = [('', '---------')]
        if corporate_number:
            # 有効な部署一覧を取得
            valid_departments = CompanyDepartment.get_valid_departments().filter(corporate_number=corporate_number)
            choices += [(d.department_code, d.name) for d in valid_departments]

            # もし編集中のユーザーが部署に所属していて、その部署が有効リストにない場合、追加する
            if self.instance and self.instance.pk and self.instance.department_code:
                current_dept_code = self.instance.department_code
                is_in_choices = any(choice[0] == current_dept_code for choice in choices)
                if not is_in_choices:
                    try:
                        # 部署の有効期限が切れていても、選択肢には表示する
                        current_dept = CompanyDepartment.objects.get(department_code=current_dept_code, corporate_number=corporate_number)
                        choices.append((current_dept.department_code, f"{current_dept.name}（現在設定中）"))
                    except CompanyDepartment.DoesNotExist:
                        # 念のため、存在しない部署コードが設定されていた場合のケア
                        choices.append((current_dept_code, f"不明な部署({current_dept_code})"))

        self.fields['department_code'].choices = choices

    def clean_phone_number(self):
        value = self.cleaned_data.get('phone_number', '')
        import re
        if value and not re.fullmatch(r'^[0-9\-]+$', value):
            raise forms.ValidationError('電話番号は半角数字とハイフンのみ入力してください。')
        return value

    class Meta:
        model = CompanyUser
        fields = [
            'department_code', 'name_last', 'name_first',
            'position', 'phone_number', 'email', 'display_order'
        ]
        widgets = {
            'name_last': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'name_first': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
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
