
# 共通カナバリデーション/正規化
from apps.common.forms.fields import to_fullwidth_katakana, validate_kana
# forms.py
import os
from django import forms
from django.forms import TextInput
from .models import Client, ClientFile
from django.core.exceptions import ValidationError
from stdnum.jp import cn as houjin

class ClientForm(forms.ModelForm):
    def clean_name_furigana(self):
        value = self.cleaned_data.get('name_furigana', '')
        validate_kana(value)
        value = to_fullwidth_katakana(value)
        return value

    def clean_corporate_number(self):
        corporate_number = self.cleaned_data.get('corporate_number')
        if not corporate_number:
            return corporate_number
        try:
            houjin.validate(corporate_number)
        except Exception as e:
            raise ValidationError(f'法人番号が正しくありません: {e}')
        return corporate_number

    regist_form_client = forms.ChoiceField(
        choices=[],
        label='登録区分',  # 日本語ラベル
        widget=forms.Select(attrs={'class':'form-select form-select-sm'}) ,
        required=True,
    )
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ここでのみDropdownsをimport.そうしないとmigrateでエラーになる
        from apps.system.settings.models import Dropdowns
        from apps.master.models import BillPayment
        
        self.fields['regist_form_client'].choices = [
            (opt.value, opt.name)
            for opt in Dropdowns.objects.filter(active=True, category='regist_form_client').order_by('disp_seq')
        ]
        
        # 支払いサイトの選択肢を設定
        self.fields['payment_site'].queryset = BillPayment.get_active_list()
        
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

    class Meta:
        model = Client
        fields = ['corporate_number','name','name_furigana',
                  'postal_code','address',  'memo', 'regist_form_client', 'basic_contract_date', 'payment_site']
        widgets = {
            'corporate_number': forms.TextInput(attrs={'class': 'form-control form-control-sm',
                'pattern': '[0-9]{13}', 'inputmode': 'numeric', 'maxlength': '13', 'style': 'ime-mode:disabled;', 'autocomplete': 'off'}),
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'name_furigana': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control form-control-sm'
                ,'pattern': '[0-9]{7}', 'inputmode': 'numeric', 'minlength': '7', 'maxlength': '7', 'style': 'ime-mode:disabled;', 'autocomplete': 'off'}),
            'address': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            # 'phone': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            # 'email': forms.EmailInput(attrs={'class': 'form-control form-control-sm'}),
            'memo': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'basic_contract_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'payment_site': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            # 'regist_form_code': forms.Select(attrs={'class': 'form-control form-control-sm form-select-sm'}),
        }


# クライアント組織フォーム
from .models import ClientContacted, ClientDepartment, ClientUser

class ClientDepartmentForm(forms.ModelForm):
    def clean_phone_number(self):
        value = self.cleaned_data.get('phone_number', '')
        import re
        # 半角数字・ハイフンのみ許可（全角数字不可）
        if value and not re.fullmatch(r'^[0-9\-]+$', value):
            raise forms.ValidationError('電話番号は数字とハイフンのみ入力してください。')
        return value
    class Meta:
        model = ClientDepartment
        fields = ['name', 'department_code', 'postal_code', 'address', 'phone_number', 'display_order', 'valid_from', 'valid_to']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'department_code': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'pattern': '[0-9]{7}', 'inputmode': 'numeric', 'maxlength': '7'}),
            'address': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'inputmode': 'numeric',
                'pattern': '[0-9\-]*',
                'style': 'ime-mode:disabled;',
                'autocomplete': 'off',
            }),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'valid_from': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'valid_to': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
        }


# クライアント担当者フォーム
class ClientUserForm(forms.ModelForm):
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
    def clean_phone_number(self):
        value = self.cleaned_data.get('phone_number', '')
        import re
        # 半角数字・ハイフンのみ許可（全角数字不可）
        if value and not re.fullmatch(r'^[0-9\-]+$', value):
            raise forms.ValidationError('電話番号は半角数字とハイフンのみ入力してください。')
        return value
    def __init__(self, *args, **kwargs):
        client = kwargs.pop('client', None)
        super().__init__(*args, **kwargs)
        if client:
            self.fields['department'].queryset = ClientDepartment.objects.filter(client=client).order_by('display_order', 'name')

    class Meta:
        model = ClientUser
        fields = ['department', 'name_last', 'name_first', 'name_kana_last', 'name_kana_first', 'position', 'phone_number', 'email', 'memo', 'display_order']
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
                'pattern': '[0-9\-]*',
                'style': 'ime-mode:disabled;',
                'autocomplete': 'off',
            }),
            'email': forms.EmailInput(attrs={'class': 'form-control form-control-sm'}),
            'memo': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
        }


# クライアント連絡履歴フォーム
class ClientContactedForm(forms.ModelForm):
    contact_type = forms.ChoiceField(
        choices=[],
        label='連絡種別',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        client = kwargs.pop('client', None)
        super().__init__(*args, **kwargs)
        from apps.system.settings.models import Dropdowns
        self.fields['contact_type'].choices = [
            (opt.value, opt.name)
            for opt in Dropdowns.objects.filter(active=True, category='contact_type').order_by('disp_seq')
        ]
        
        # クライアントが指定されている場合、組織と担当者の選択肢を絞り込む
        if client:
            self.fields['department'].queryset = ClientDepartment.objects.filter(client=client).order_by('display_order', 'name')
            self.fields['user'].queryset = ClientUser.objects.filter(client=client).order_by('display_order', 'name_last', 'name_first')
        else:
            self.fields['department'].queryset = ClientDepartment.objects.none()
            self.fields['user'].queryset = ClientUser.objects.none()

    class Meta:
        model = ClientContacted
        fields = ['contacted_at', 'department', 'user', 'contact_type', 'content', 'detail']
        widgets = {
            'contacted_at': forms.DateTimeInput(attrs={'class': 'form-control form-control-sm', 'type': 'datetime-local'}),
            'department': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'user': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'content': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'detail': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
        }


class ClientFileForm(forms.ModelForm):
    """クライアントファイル添付フォーム"""
    
    class Meta:
        model = ClientFile
        fields = ['file', 'description']
        widgets = {
            'file': forms.ClearableFileInput(attrs={
                'class': 'form-control form-control-sm',
                'accept': '.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.jpg,.jpeg,.png,.gif,.bmp,.webp',
                'multiple': False
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'ファイルの説明（任意）'
            }),
        }
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # ファイルサイズチェック（10MB制限）
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError('ファイルサイズは10MB以下にしてください。')
            
            # ファイル拡張子チェック
            allowed_extensions = [
                '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt',
                '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'
            ]
            file_extension = os.path.splitext(file.name)[1].lower()
            if file_extension not in allowed_extensions:
                raise forms.ValidationError(
                    f'許可されていないファイル形式です。許可されている形式: {", ".join(allowed_extensions)}'
                )
        
        return file