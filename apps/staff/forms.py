# forms.py
import os
from django import forms
from django.forms import TextInput
from .models import Staff, StaffContacted, StaffContactSchedule, StaffQualification, StaffSkill, StaffFile, StaffMynumber, StaffBank, StaffInternational, StaffDisability, StaffContact
from django.core.exceptions import ValidationError
from apps.common.forms import MyRadioSelect

# スタッフ連絡履歴フォーム
class StaffContactedForm(forms.ModelForm):
    contact_type = forms.ChoiceField(
        choices=[],
        label='連絡種別',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.system.settings.models import Dropdowns
        self.fields['contact_type'].choices = [
            (opt.value, opt.name)
            for opt in Dropdowns.objects.filter(active=True, category='contact_type').order_by('disp_seq')
        ]

    class Meta:
        model = StaffContacted
        fields = ['contacted_at', 'contact_type', 'content', 'detail']
        widgets = {
            'contacted_at': forms.DateTimeInput(attrs={'class': 'form-control form-control-sm', 'type': 'datetime-local'}),
            'content': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'detail': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
        }


# スタッフ連絡予定フォーム
class StaffContactScheduleForm(forms.ModelForm):
    contact_type = forms.ChoiceField(
        choices=[],
        label='連絡種別',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.system.settings.models import Dropdowns
        self.fields['contact_type'].choices = [
            (opt.value, opt.name)
            for opt in Dropdowns.objects.filter(active=True, category='contact_type').order_by('disp_seq')
        ]

    class Meta:
        model = StaffContactSchedule
        fields = ['contact_date', 'contact_type', 'content', 'detail']
        widgets = {
            'contact_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'content': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'detail': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
        }


# 共通カナバリデーション/正規化
from apps.common.forms.fields import to_fullwidth_katakana, validate_kana


class StaffForm(forms.ModelForm):
    employment_type = forms.ModelChoiceField(
        queryset=None,
        label='雇用形態',
        required=False,
        empty_label='選択してください',
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    def clean_phone(self):
        value = self.cleaned_data.get('phone', '')
        import re
        # 半角数字・ハイフンのみ許可（全角数字不可）
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

    def clean_employee_no(self):
        value = self.cleaned_data.get('employee_no', '')
        if value:
            import re
            if not re.fullmatch(r'^[A-Za-z0-9]{1,10}', value):
                raise forms.ValidationError('社員番号は半角英数字10文字以内で入力してください。')

            # 編集時に自分自身を除外して重複チェック
            qs = Staff.objects.filter(employee_no=value)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('この社員番号は既に使用されています。')
        return value

    def clean_email(self):
        value = self.cleaned_data.get('email', '')
        if value:
            # 編集時に自分自身を除外して重複チェック
            qs = Staff.objects.filter(email=value)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError('このメールアドレスは既に使用されています。')
        return value
    
    def clean(self):
        cleaned_data = super().clean()
        hire_date = cleaned_data.get('hire_date')
        resignation_date = cleaned_data.get('resignation_date')
        employee_no = cleaned_data.get('employee_no')
        employment_type = cleaned_data.get('employment_type')
        
        # 入社日、社員番号、雇用形態のセットバリデーション
        if hire_date and not employee_no:
            raise forms.ValidationError('入社日を入力する場合は、社員番号も入力してください。')
        
        if hire_date and not employment_type:
            raise forms.ValidationError('入社日を入力する場合は、雇用形態も選択してください。')
        
        if employee_no and not hire_date:
            raise forms.ValidationError('社員番号を入力する場合は、入社日も入力してください。')
        
        if employment_type and not hire_date:
            raise forms.ValidationError('雇用形態を選択する場合は、入社日も入力してください。')
        
        # 入社日なしに退職日入力はNG
        if resignation_date and not hire_date:
            raise forms.ValidationError('退職日を入力する場合は、入社日も入力してください。')
        
        # 入社日と退職日の妥当性チェック
        if hire_date and resignation_date and hire_date > resignation_date:
            raise forms.ValidationError('入社日は退職日より前の日付を入力してください。')
        
        # 退職日とスタッフ契約の契約終了日の整合性チェック
        if resignation_date and self.instance and self.instance.pk:
            from apps.contract.models import StaffContract
            
            # このスタッフの契約で、退職日より後に終了する契約があるかチェック
            future_contracts = StaffContract.objects.filter(
                staff=self.instance,
                end_date__isnull=False,
                end_date__gt=resignation_date
            ).order_by('end_date')
            
            if future_contracts.exists():
                # 最も早い契約終了日を取得
                earliest_contract = future_contracts.first()
                raise forms.ValidationError(
                    f'契約終了日以降に退職日を設定してください。'
                    f'契約「{earliest_contract.contract_name}」の終了日: {earliest_contract.end_date.strftime("%Y/%m/%d")}'
                )
        
        return cleaned_data

    sex = forms.ChoiceField(
        choices=[],
        label='性別',  # 日本語ラベル
        required=True,
        widget=MyRadioSelect()  # カスタムウィジェットで横並び表示
    )

    regist_status = forms.ModelChoiceField(
        queryset=None,
        label='登録区分',
        widget=forms.Select(attrs={'class':'form-select form-select-sm'}),
        required=True,
    )
    
    department_code = forms.ChoiceField(
        choices=[],
        label='所属部署',
        widget=forms.Select(attrs={'class':'form-select form-select-sm'}),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ここでのみDropdownsをimport.そうしないとmigrateでエラーになる
        from apps.system.settings.models import Dropdowns
        from apps.company.models import CompanyDepartment
        from django.utils import timezone
        from django.db import models
        
        self.fields['sex'].choices = [
            (opt.value, opt.name)
            for opt in Dropdowns.objects.filter(active=True, category='sex').order_by('disp_seq')
        ]
        from apps.master.models import StaffRegistStatus
        self.fields['regist_status'].queryset = StaffRegistStatus.objects.filter(is_active=True).order_by('display_order')

        from apps.master.models import EmploymentType
        self.fields['employment_type'].queryset = EmploymentType.objects.filter(is_active=True).order_by('display_order', 'name')
        
        # 現在有効な部署の選択肢を設定
        current_date = timezone.localdate()
        valid_departments = CompanyDepartment.get_valid_departments(current_date)
        self.fields['department_code'].choices = [('', '選択してください')] + [
            (dept.department_code, f"{dept.name} ({dept.department_code})")
            for dept in valid_departments
        ]
        
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
        model = Staff
        fields = [
            'regist_status',
            'employment_type',
            'employee_no',
            'name_last','name_first','name_kana_last','name_kana_first',
            'birth_date','sex',
            # 'age', ← ここは除外
            'hire_date', 'resignation_date', 'department_code',  # 新しいフィールドを追加
            'postal_code','address1','address2','address3', 'phone', 'email', 'memo'
        ]
        widgets = {
            'employee_no': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'maxlength': '10'}),
            'name_last': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'name_first': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'name_kana_last': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'name_kana_first': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'hire_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'resignation_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            #'sex': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            #'age': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'pattern': '[0-9]{7}', 'inputmode': 'numeric', 'minlength': '7', 'maxlength': '7', 'style': 'ime-mode:disabled;', 'autocomplete': 'off'
            }),
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
            'email': forms.EmailInput(attrs={'class': 'form-control form-control-sm'}),
            'memo': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            # 'regist_status': forms.Select(attrs={'class': 'form-control form-control-sm form-select-sm'}),
        }


class StaffQualificationForm(forms.ModelForm):
    """スタッフ資格フォーム"""
    
    class Meta:
        model = StaffQualification
        fields = ['qualification', 'acquired_date', 'expiry_date', 'certificate_number', 'memo', 'score']
        widgets = {
            'qualification': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'acquired_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'certificate_number': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'memo': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'score': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.staff = kwargs.pop('staff', None)  # スタッフインスタンスを受け取る
        super().__init__(*args, **kwargs)
        # 資格のみ（レベル2）を選択肢として設定
        from apps.master.models import Qualification
        qualifications = Qualification.objects.filter(level=2, is_active=True).select_related('parent').order_by('parent__display_order', 'parent__name', 'display_order', 'name')
        self.fields['qualification'].choices = [('', '選択してください')] + [
            (q.pk, f"{q.parent.name} > {q.name}" if q.parent else q.name)
            for q in qualifications
        ]
    
    def clean(self):
        """重複チェック"""
        cleaned_data = super().clean()
        qualification = cleaned_data.get('qualification')
        
        if qualification and self.staff:
            # 編集時は自分自身を除外
            existing_query = StaffQualification.objects.filter(
                staff=self.staff,
                qualification=qualification
            )
            if self.instance.pk:
                existing_query = existing_query.exclude(pk=self.instance.pk)
            
            if existing_query.exists():
                # 特定のフィールドにエラーを関連付ける
                self.add_error('qualification', f'この資格「{qualification.name}」は既に登録されています。')
        
        return cleaned_data


class StaffSkillForm(forms.ModelForm):
    """スタッフ技能フォーム"""
    
    class Meta:
        model = StaffSkill
        fields = ['skill', 'acquired_date', 'years_of_experience', 'memo']
        widgets = {
            'skill': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'acquired_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'years_of_experience': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0'}),
            'memo': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.staff = kwargs.pop('staff', None)  # スタッフインスタンスを受け取る
        super().__init__(*args, **kwargs)
        # 技能のみ（レベル2）を選択肢として設定
        from apps.master.models import Skill
        skills = Skill.objects.filter(level=2, is_active=True).select_related('parent').order_by('parent__display_order', 'parent__name', 'display_order', 'name')
        self.fields['skill'].choices = [('', '選択してください')] + [
            (s.pk, f"{s.parent.name} > {s.name}" if s.parent else s.name)
            for s in skills
        ]
    
    def clean(self):
        """重複チェック"""
        cleaned_data = super().clean()
        skill = cleaned_data.get('skill')
        
        if skill and self.staff:
            # 編集時は自分自身を除外
            existing_query = StaffSkill.objects.filter(
                staff=self.staff,
                skill=skill
            )
            if self.instance.pk:
                existing_query = existing_query.exclude(pk=self.instance.pk)
            
            if existing_query.exists():
                # 特定のフィールドにエラーを関連付ける
                self.add_error('skill', f'この技能「{skill.name}」は既に登録されています。')
        
        return cleaned_data


class StaffFileForm(forms.ModelForm):
    """スタッフファイル添付フォーム"""
    
    class Meta:
        model = StaffFile
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


class StaffMynumberForm(forms.ModelForm):
    """スタッフマイナンバーフォーム"""

    class Meta:
        model = StaffMynumber
        fields = ['mynumber']
        widgets = {
            'mynumber': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'maxlength': '12',
                'pattern': '[0-9]{12}',
                'inputmode': 'numeric',
                'style': 'ime-mode:disabled;',
                'autocomplete': 'off'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 必須フィールドの設定
        self.fields['mynumber'].required = True

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


class StaffContactForm(forms.ModelForm):
    """スタッフ連絡先情報フォーム"""

    class Meta:
        model = StaffContact
        fields = ['emergency_contact', 'relationship', 'postal_code', 'address1', 'address2', 'address3']
        widgets = {
            'emergency_contact': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'relationship': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'pattern': '[0-9]{7}', 'inputmode': 'numeric', 'minlength': '7', 'maxlength': '7', 'style': 'ime-mode:disabled;', 'autocomplete': 'off'
            }),
            'address1': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'address2': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'address3': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
        }


class StaffBankForm(forms.ModelForm):
    """スタッフ銀行情報フォーム"""
    bank_name = forms.CharField(
        label='銀行名',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': '例: 三菱ＵＦＪ銀行'})
    )
    branch_name = forms.CharField(
        label='支店名',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': '例: 東京営業部'})
    )
    account_type = forms.ChoiceField(
        choices=[],
        label='口座種別',
        widget=MyRadioSelect(),
        required=True,
    )

    class Meta:
        model = StaffBank
        fields = ['bank_code', 'branch_code', 'account_type', 'account_number', 'account_holder']
        widgets = {
            'bank_code': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'maxlength': '4',
                'pattern': '[0-9]{4}',
                'inputmode': 'numeric',
                'style': 'ime-mode:disabled;',
                'autocomplete': 'off',
                'placeholder': '例: 0001'
            }),
            'branch_code': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'maxlength': '3',
                'pattern': '[0-9]{3}',
                'inputmode': 'numeric',
                'style': 'ime-mode:disabled;',
                'autocomplete': 'off',
                'placeholder': '例: 001'
            }),
            'account_number': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'maxlength': '8',
                'pattern': '[0-9]{1,8}',
                'inputmode': 'numeric',
                'style': 'ime-mode:disabled;',
                'autocomplete': 'off',
                'placeholder': '例: 1234567'
            }),
            'account_holder': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': '例: ヤマダ タロウ'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 口座種別の選択肢を設定
        from apps.system.settings.models import Dropdowns
        self.fields['account_type'].choices = [
            (opt.value, opt.name)
            for opt in Dropdowns.objects.filter(active=True, category='bank_account_type').order_by('disp_seq')
        ]
        
        # 必須フィールドの設定
        self.fields['bank_code'].required = True
        self.fields['branch_code'].required = True
        self.fields['account_type'].required = True
        self.fields['account_number'].required = True
        self.fields['account_holder'].required = True

    def clean_bank_code(self):
        """銀行コードのバリデーション"""
        bank_code = self.cleaned_data.get('bank_code')
        if bank_code:
            if not bank_code.isdigit():
                raise ValidationError('銀行コードは数字で入力してください。')
            if len(bank_code) != 4:
                raise ValidationError('銀行コードは4桁で入力してください。')
        return bank_code

    def clean_branch_code(self):
        """支店コードのバリデーション"""
        branch_code = self.cleaned_data.get('branch_code')
        if branch_code:
            if not branch_code.isdigit():
                raise ValidationError('支店コードは数字で入力してください。')
            if len(branch_code) != 3:
                raise ValidationError('支店コードは3桁で入力してください。')
        return branch_code

    def clean_account_number(self):
        """口座番号のバリデーション"""
        account_number = self.cleaned_data.get('account_number')
        if account_number:
            if not account_number.isdigit():
                raise ValidationError('口座番号は数字で入力してください。')
            if len(account_number) < 1 or len(account_number) > 8:
                raise ValidationError('口座番号は1-8桁で入力してください。')
        return account_number


class StaffInternationalForm(forms.ModelForm):
    """スタッフ外国籍情報フォーム"""

    class Meta:
        model = StaffInternational
        fields = ['residence_card_number', 'residence_status', 'residence_period_from', 'residence_period_to']
        widgets = {
            'residence_card_number': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'maxlength': '20'
            }),
            'residence_status': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'maxlength': '100'
            }),
            'residence_period_from': forms.DateInput(attrs={
                'class': 'form-control form-control-sm',
                'type': 'date'
            }),
            'residence_period_to': forms.DateInput(attrs={
                'class': 'form-control form-control-sm',
                'type': 'date'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 必須フィールドの設定
        for field in self.fields:
            self.fields[field].required = True

    def clean(self):
        """在留期間の妥当性チェック"""
        cleaned_data = super().clean()
        residence_period_from = cleaned_data.get('residence_period_from')
        residence_period_to = cleaned_data.get('residence_period_to')

        if residence_period_from and residence_period_to:
            if residence_period_from >= residence_period_to:
                raise forms.ValidationError('在留許可開始日は在留期限より前の日付を入力してください。')

        return cleaned_data


class StaffDisabilityForm(forms.ModelForm):
    """スタッフ障害者情報フォーム"""
    disability_type = forms.ChoiceField(
        label='障害の種類',
        widget=MyRadioSelect(),
        choices=[],
        required=True,
    )

    class Meta:
        model = StaffDisability
        fields = ['disability_type', 'disability_grade', 'disability_severity']
        widgets = {
            'disability_grade': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'disability_severity': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.system.settings.models import Dropdowns
        self.fields['disability_type'].choices = [
            (opt.value, opt.name)
            for opt in Dropdowns.objects.filter(active=True, category='disability_type').order_by('disp_seq')
        ]
        self.fields['disability_grade'].required = True
        self.fields['disability_severity'].required = True

from .models_evaluation import StaffEvaluation
class StaffEvaluationForm(forms.ModelForm):
    """スタッフ評価フォーム"""
    class Meta:
        model = StaffEvaluation
        fields = ['evaluation_date', 'rating', 'comment']
        widgets = {
            'evaluation_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'rating': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'comment': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
        }

class StaffFaceUploadForm(forms.Form):
    """スタッフ顔写真アップロードフォーム"""
    face_image = forms.ImageField(
        label='顔写真ファイル',
        help_text='2MB以下のJPEGまたはPNG画像を選択してください。',
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': 'image/jpeg,image/png',
        })
    )

    # クロップデータ保持用
    crop_x = forms.FloatField(widget=forms.HiddenInput(), required=False)
    crop_y = forms.FloatField(widget=forms.HiddenInput(), required=False)
    crop_width = forms.FloatField(widget=forms.HiddenInput(), required=False)
    crop_height = forms.FloatField(widget=forms.HiddenInput(), required=False)

    def clean_face_image(self):
        image = self.cleaned_data.get('face_image')
        if image:
            # ファイルサイズチェック（2MB制限）
            if image.size > 2 * 1024 * 1024:
                raise forms.ValidationError('ファイルサイズは2MB以下にしてください。')
        return image
