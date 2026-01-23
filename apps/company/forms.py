import re
from django import forms
from .models import Company, CompanyDepartment, CompanyUser
from django.core.exceptions import ValidationError
from apps.common.forms import MyRadioSelect

class CompanyForm(forms.ModelForm):
    def clean_phone_number(self):
        value = self.cleaned_data.get('phone_number', '')
        if value and not re.fullmatch(r'[0-9\-]+', value):
            raise forms.ValidationError('電話番号は数字とハイフンのみ入力してください。')
        return value
    class Meta:
        model = Company
        fields = ['name', 'corporate_number', 'representative', 'postal_code', 'address', 'phone_number', 'haken_permit_number', 'shokai_permit_number', 'foreign_regist_number', 'dispatch_treatment_method']
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
            'dispatch_treatment_method': MyRadioSelect(),
        }
    
    def clean_corporate_number(self):
        corporate_number = self.cleaned_data.get('corporate_number')
        if not corporate_number:
            return corporate_number

        # stdnumライブラリが有効な法人番号を誤って弾くため、
        # チェックディジット検証を無効化し、桁数チェックのみを行う。
        # see: https://github.com/arthurdejong/python-stdnum/issues/145
        if not re.fullmatch(r'\d{13}', corporate_number):
            raise forms.ValidationError('法人番号は13桁の半角数字で入力してください。')

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

class CompanySealUploadForm(forms.Form):
    """会社印アップロードフォーム"""
    seal_image = forms.ImageField(
        label='画像ファイル',
        help_text='2MB以下のJPEGまたはPNG画像を選択してください。',
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/jpeg,image/png',
        })
    )
    seal_type = forms.CharField(widget=forms.HiddenInput()) # 'round' or 'square'
    
    # クロップデータ保持用
    crop_x = forms.FloatField(widget=forms.HiddenInput(), required=False)
    crop_y = forms.FloatField(widget=forms.HiddenInput(), required=False)
    crop_width = forms.FloatField(widget=forms.HiddenInput(), required=False)
    crop_height = forms.FloatField(widget=forms.HiddenInput(), required=False)

    def clean_seal_image(self):
        image = self.cleaned_data.get('seal_image')
        if image:
            # ファイルサイズチェック（2MB制限）
            if image.size > 2 * 1024 * 1024:
                raise forms.ValidationError('ファイルサイズは2MB以下にしてください。')
        return image
