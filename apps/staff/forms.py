# forms.py
import os
from django import forms
from django.forms import TextInput
from .models import Staff, StaffContacted, StaffQualification, StaffSkill, StaffFile
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



# 共通カナバリデーション/正規化
from apps.common.forms.fields import to_fullwidth_katakana, validate_kana


class StaffForm(forms.ModelForm):
    def clean_name_kana_last(self):
        value = self.cleaned_data.get('name_kana_last', '')
        validate_kana(value)
        value = to_fullwidth_katakana(value)
        return value

    def clean_name_kana_first(self):
        value = self.cleaned_data.get('name_kana_first', '')
        validate_kana(value)
        value = to_fullwidth_katakana(value)
        return value

    def clean_employee_no(self):
        value = self.cleaned_data.get('employee_no', '')
        if value:
            import re
            if not re.fullmatch(r'^[A-Za-z0-9]{1,10}$', value):
                raise forms.ValidationError('社員番号は半角英数字10文字以内で入力してください。')
        return value
    
    def clean(self):
        cleaned_data = super().clean()
        hire_date = cleaned_data.get('hire_date')
        resignation_date = cleaned_data.get('resignation_date')
        
        # 入社日と退職日の妥当性チェック
        if hire_date and resignation_date and hire_date > resignation_date:
            raise forms.ValidationError('入社日は退職日より前の日付を入力してください。')
        
        return cleaned_data

    sex = forms.ChoiceField(
        choices=[],
        label='性別',  # 日本語ラベル
        required=True,
        #widget=forms.RadioSelect(attrs={'class':'form-check form-check-inline'}),  # ここでラジオボタンを指定(⇒立て並びにしかできない！)
        widget=forms.RadioSelect  # ここでラジオボタンを指定(⇒立て並びにしかできない！)
    )

    regist_form_code = forms.ChoiceField(
        choices=[],
        label='登録区分',  # 日本語ラベル
        widget=forms.Select(attrs={'class':'form-select form-select-sm'}) ,
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
        self.fields['regist_form_code'].choices = [
            (opt.value, opt.name)
            for opt in Dropdowns.objects.filter(active=True, category='regist_form').order_by('disp_seq')
        ]
        
        # 現在有効な部署の選択肢を設定
        current_date = timezone.now().date()
        valid_departments = CompanyDepartment.get_valid_departments(current_date)
        self.fields['department_code'].choices = [('', '選択してください')] + [
            (dept.department_code, f"{dept.name} ({dept.department_code})")
            for dept in valid_departments
        ]
    class Meta:
        model = Staff
        fields = [
            'regist_form_code',
            'employee_no',
            'name_last','name_first','name_kana_last','name_kana_first',
            'birth_date','sex',
            # 'age', ← ここは除外
            'hire_date', 'resignation_date', 'department_code',  # 新しいフィールドを追加
            'postal_code','address1','address2','address3', 'phone', 'email'
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
            'phone': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'email': forms.EmailInput(attrs={'class': 'form-control form-control-sm'}),
            # 'regist_form_code': forms.Select(attrs={'class': 'form-control form-control-sm form-select-sm'}),
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
        super().__init__(*args, **kwargs)
        # 資格のみ（レベル2）を選択肢として設定
        from apps.master.models import Qualification
        qualifications = Qualification.objects.filter(level=2, is_active=True).select_related('parent').order_by('parent__display_order', 'parent__name', 'display_order', 'name')
        self.fields['qualification'].choices = [('', '選択してください')] + [
            (q.pk, f"{q.parent.name} > {q.name}" if q.parent else q.name)
            for q in qualifications
        ]


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
        super().__init__(*args, **kwargs)
        # 技能のみ（レベル2）を選択肢として設定
        from apps.master.models import Skill
        skills = Skill.objects.filter(level=2, is_active=True).select_related('parent').order_by('parent__display_order', 'parent__name', 'display_order', 'name')
        self.fields['skill'].choices = [('', '選択してください')] + [
            (s.pk, f"{s.parent.name} > {s.name}" if s.parent else s.name)
            for s in skills
        ]


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


