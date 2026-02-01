
# 共通カナバリデーション/正規化
from apps.common.forms.fields import to_fullwidth_katakana, validate_kana
# forms.py
import os
from django import forms
from django.forms import TextInput
from .models import Client, ClientFile, ClientFlag
from django.core.exceptions import ValidationError
from apps.common.forms import BadgeRadioSelect, BadgeCheckboxSelectMultiple
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

    regist_status = forms.ModelChoiceField(
        queryset=None,
        label='登録区分',
        widget=forms.Select(attrs={'class':'form-select form-select-sm'}),
        required=True,
    )
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ここでのみDropdownsをimport.そうしないとmigrateでエラーになる
        from apps.system.settings.models import Dropdowns
        from apps.master.models import BillPayment
        
        from apps.master.models import ClientRegistStatus
        self.fields['regist_status'].queryset = ClientRegistStatus.objects.filter(is_active=True).order_by('display_order')
        
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
                  'postal_code','address',  'memo', 'regist_status', 'basic_contract_date', 'basic_contract_date_haken', 'payment_site']
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
            'basic_contract_date_haken': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'payment_site': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            # 'regist_status_code': forms.Select(attrs={'class': 'form-control form-control-sm form-select-sm'}),
        }


# クライアント組織フォーム
from .models import ClientContacted, ClientDepartment, ClientUser, ClientContactSchedule
from apps.master.models import ClientContactType

class ClientContactScheduleForm(forms.ModelForm):
    contact_type = forms.ModelChoiceField(
        queryset=ClientContactType.objects.filter(is_active=True).order_by('display_order'),
        label='連絡種別',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        required=False,
        empty_label='選択してください'
    )

    def __init__(self, *args, **kwargs):
        client = kwargs.pop('client', None)
        super().__init__(*args, **kwargs)
        
        # クライアントが指定されている場合、組織と担当者の選択肢を絞り込む
        if client:
            self.fields['department'].queryset = ClientDepartment.objects.filter(client=client).order_by('display_order', 'name')
            self.fields['user'].queryset = ClientUser.objects.filter(client=client).order_by('display_order', 'name_last', 'name_first')
        else:
            self.fields['department'].queryset = ClientDepartment.objects.none()
            self.fields['user'].queryset = ClientUser.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        department = cleaned_data.get('department')
        user = cleaned_data.get('user')

        if department and user:
            # 担当者が指定の所属に属しているかチェック
            if user.department != department:
                self.add_error('user', '指定された担当者はこの所属にはいません。')

        return cleaned_data

    class Meta:
        model = ClientContactSchedule
        fields = ['contact_date', 'department', 'user', 'contact_type', 'content', 'detail']
        widgets = {
            'contact_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'department': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'user': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'content': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'detail': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
        }


class ClientDepartmentForm(forms.ModelForm):
    def clean_phone_number(self):
        value = self.cleaned_data.get('phone_number', '')
        import re
        # 半角数字・ハイフンのみ許可（全角数字不可）
        if value and not re.fullmatch(r'^[0-9\-]+$', value):
            raise forms.ValidationError('電話番号は数字とハイフンのみ入力してください。')
        return value
    def clean(self):
        cleaned_data = super().clean()
        is_haken_office = cleaned_data.get('is_haken_office')
        haken_jigyosho_teishokubi = cleaned_data.get('haken_jigyosho_teishokubi')
        haken_jigyosho_teishokubi_notice_date = cleaned_data.get('haken_jigyosho_teishokubi_notice_date')
        is_haken_unit = cleaned_data.get('is_haken_unit')
        haken_unit_manager_title = cleaned_data.get('haken_unit_manager_title')

        # 派遣事業所関連のバリデーション
        if not is_haken_office and haken_jigyosho_teishokubi:
            self.add_error('haken_jigyosho_teishokubi', '派遣事業所該当でない場合、派遣事業所抵触日は入力できません。')
        
        if not is_haken_office and haken_jigyosho_teishokubi_notice_date:
            self.add_error('haken_jigyosho_teishokubi_notice_date', '派遣事業所該当でない場合、事業所抵触日通知日は入力できません。')

        # 事業所抵触日通知日のバリデーション
        if haken_jigyosho_teishokubi_notice_date and not haken_jigyosho_teishokubi:
            self.add_error('haken_jigyosho_teishokubi_notice_date', '事業所抵触日通知日を入力する場合は、事業所抵触日も入力してください。')

        # 派遣組織単位関連のバリデーション
        if is_haken_unit:
            if not haken_unit_manager_title:
                self.add_error('haken_unit_manager_title', '派遣組織単位該当の場合、派遣組織単位長役職は必須です。')
        else:
            if haken_unit_manager_title:
                self.add_error('haken_unit_manager_title', '派遣組織単位該当でない場合、派遣組織単位長役職は入力できません。')

        return cleaned_data

    class Meta:
        model = ClientDepartment
        fields = [
            'name', 'department_code', 'postal_code', 'address', 'phone_number',
            'is_haken_office', 'is_haken_unit', 'haken_unit_manager_title', 'haken_jigyosho_teishokubi',
            'haken_jigyosho_teishokubi_notice_date', 'commander', 'complaint_officer', 'responsible_person', 'display_order', 'valid_from', 'valid_to'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'department_code': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'pattern': '[0-9]{7}', 'inputmode': 'numeric', 'maxlength': '7'}),
            'address': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'inputmode': 'numeric',
                'pattern': r'[0-9\-]*',
                'style': 'ime-mode:disabled;',
                'autocomplete': 'off',
            }),
            'is_haken_office': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_haken_unit': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'haken_unit_manager_title': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'haken_jigyosho_teishokubi': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'haken_jigyosho_teishokubi_notice_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'valid_from': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'valid_to': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'commander': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'complaint_officer': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'responsible_person': forms.Select(attrs={'class': 'form-select form-select-sm'}),
        }

    def __init__(self, *args, **kwargs):
        client = kwargs.pop('client', None)
        super().__init__(*args, **kwargs)
        if client:
            self.fields['commander'].queryset = ClientUser.objects.filter(client=client).order_by('display_order', 'name_last', 'name_first')
            self.fields['complaint_officer'].queryset = ClientUser.objects.filter(client=client).order_by('display_order', 'name_last', 'name_first')
            self.fields['responsible_person'].queryset = ClientUser.objects.filter(client=client).order_by('display_order', 'name_last', 'name_first')


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
                'pattern': r'[0-9\-]*',
                'style': 'ime-mode:disabled;',
                'autocomplete': 'off',
            }),
            'email': forms.EmailInput(attrs={'class': 'form-control form-control-sm'}),
            'memo': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
        }


# クライアント連絡履歴フォーム
class ClientContactedForm(forms.ModelForm):
    contact_type = forms.ModelChoiceField(
        queryset=ClientContactType.objects.filter(is_active=True).order_by('display_order'),
        label='連絡種別',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        required=False,
        empty_label='選択してください'
    )

    def __init__(self, *args, **kwargs):
        client = kwargs.pop('client', None)
        super().__init__(*args, **kwargs)
        
        # クライアントが指定されている場合、組織と担当者の選択肢を絞り込む
        if client:
            self.fields['department'].queryset = ClientDepartment.objects.filter(client=client).order_by('display_order', 'name')
            self.fields['user'].queryset = ClientUser.objects.filter(client=client).order_by('display_order', 'name_last', 'name_first')
        else:
            self.fields['department'].queryset = ClientDepartment.objects.none()
            self.fields['user'].queryset = ClientUser.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        department = cleaned_data.get('department')
        user = cleaned_data.get('user')

        if department and user:
            # 担当者が指定の所属に属しているかチェック
            if user.department != department:
                self.add_error('user', '指定された担当者はこの所属にはいません。')

        return cleaned_data

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


class ClientFlagForm(forms.ModelForm):
    """クライアントフラッグフォーム"""
    client = forms.ModelChoiceField(
        queryset=None,
        label='クライアント',
        required=True,
        widget=forms.HiddenInput()
    )
    company_department = forms.ModelChoiceField(
        queryset=None,
        label='会社組織',
        required=False,
        empty_label='選択してください',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    company_user = forms.ModelChoiceField(
        queryset=None,
        label='会社担当者',
        required=False,
        empty_label='選択してください',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    flag_status = forms.ModelChoiceField(
        queryset=None,
        label='フラッグステータス',
        required=True,
        empty_label=None,
        widget=BadgeRadioSelect()
    )

    class Meta:
        model = ClientFlag
        fields = ['client', 'company_department', 'company_user', 'flag_status', 'details']
        widgets = {
            'details': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        company_department = cleaned_data.get('company_department')
        company_user = cleaned_data.get('company_user')

        if company_user and not company_department:
            self.add_error('company_department', '会社担当者を入力するときは、会社組織を必須にしてください。')

        if company_user and company_department:
            if company_user.department_code != company_department.department_code:
                self.add_error('company_user', '会社組織と、会社担当者の所属する組織が違います。')

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.company.models import CompanyDepartment, CompanyUser
        from apps.master.models_other import FlagStatus
        from apps.common.middleware import get_current_tenant_id

        tenant_id = get_current_tenant_id()
        if tenant_id:
            self.fields['client'].queryset = Client.objects.filter(tenant_id=tenant_id)
            self.fields['company_department'].queryset = CompanyDepartment.objects.filter(tenant_id=tenant_id)
            self.fields['company_user'].queryset = CompanyUser.objects.filter(tenant_id=tenant_id)
            self.fields['flag_status'].queryset = FlagStatus.objects.filter(tenant_id=tenant_id, is_active=True).order_by('display_order')
        else:
            self.fields['client'].queryset = Client.objects.all()
            self.fields['company_department'].queryset = CompanyDepartment.objects.all()
            self.fields['company_user'].queryset = CompanyUser.objects.all()
            self.fields['flag_status'].queryset = FlagStatus.objects.filter(is_active=True).order_by('display_order')

        # バッジ色のマッピングを設定
        from apps.system.settings.templatetags.badge_tags import badge_class
        status_qs = self.fields['flag_status'].queryset
        if status_qs:
            self.fields['flag_status'].widget.badge_class_map = {
                str(s.pk): badge_class(s.display_order) for s in status_qs
            }


class ClientTagEditForm(forms.ModelForm):
    """クライアントタグ編集フォーム"""
    tags = forms.ModelMultipleChoiceField(
        queryset=None,
        widget=BadgeCheckboxSelectMultiple(),
        required=False,
        label='タグ'
    )

    class Meta:
        model = Client
        fields = ['tags']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.master.models_client import ClientTag
        from apps.common.middleware import get_current_tenant_id
        from apps.system.settings.templatetags.badge_tags import badge_class

        tenant_id = get_current_tenant_id()
        if tenant_id:
            qs = ClientTag.objects.filter(tenant_id=tenant_id, is_active=True).order_by('display_order', 'name')
        else:
            qs = ClientTag.objects.filter(is_active=True).order_by('display_order', 'name')

        self.fields['tags'].queryset = qs
        self.fields['tags'].widget.badge_class_map = {
            str(t.pk): badge_class(t.display_order) for t in qs
        }