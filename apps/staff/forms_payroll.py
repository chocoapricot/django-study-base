from django import forms
from .models import StaffPayroll

class StaffPayrollForm(forms.ModelForm):
    class Meta:
        model = StaffPayroll
        fields = [
            'basic_pension_number',
            'health_insurance_join_date',
            'health_insurance_non_enrollment_reason',
            'welfare_pension_join_date',
            'pension_insurance_non_enrollment_reason',
            'employment_insurance_join_date',
            'employment_insurance_non_enrollment_reason',
        ]
        widgets = {
            'basic_pension_number': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'placeholder': '例: 1234-567890'}),
            'health_insurance_join_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'health_insurance_non_enrollment_reason': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'welfare_pension_join_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'pension_insurance_non_enrollment_reason': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'employment_insurance_join_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'employment_insurance_non_enrollment_reason': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
        }

    def clean(self):
        """
        給与情報の整合性をチェックする
        """
        cleaned_data = super().clean()
        errors = []
        
        # 健康保険のバリデーション
        try:
            self._validate_insurance_fields(
                cleaned_data,
                'health_insurance_join_date',
                'health_insurance_non_enrollment_reason',
                '健康保険'
            )
        except forms.ValidationError as e:
            errors.extend(e.messages)
        
        # 厚生年金のバリデーション
        try:
            self._validate_insurance_fields(
                cleaned_data,
                'welfare_pension_join_date',
                'pension_insurance_non_enrollment_reason',
                '厚生年金'
            )
        except forms.ValidationError as e:
            errors.extend(e.messages)
        
        # 雇用保険のバリデーション
        try:
            self._validate_insurance_fields(
                cleaned_data,
                'employment_insurance_join_date',
                'employment_insurance_non_enrollment_reason',
                '雇用保険'
            )
        except forms.ValidationError as e:
            errors.extend(e.messages)
        
        # すべてのエラーをまとめて発生させる
        if errors:
            raise forms.ValidationError(errors)
        
        return cleaned_data
    
    def _validate_insurance_fields(self, cleaned_data, date_field, reason_field, insurance_name):
        """
        保険の加入日と非加入理由の整合性をチェックする
        """
        join_date = cleaned_data.get(date_field)
        non_enrollment_reason = cleaned_data.get(reason_field)
        
        # 日付が入っていて非加入理由も入力されている場合はエラー
        if join_date and non_enrollment_reason:
            raise forms.ValidationError(
                f'{insurance_name}の加入日が入力されている場合、非加入理由は入力できません。'
            )
        
        # 日付が入っていないのに非加入理由も入力されていない場合はエラー
        if not join_date and not non_enrollment_reason:
            raise forms.ValidationError(
                f'{insurance_name}の加入日または非加入理由のいずれかを入力してください。'
            )
