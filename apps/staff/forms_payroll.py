from django import forms
from .models import StaffPayroll

class StaffPayrollForm(forms.ModelForm):
    class Meta:
        model = StaffPayroll
        fields = [
            'health_insurance_join_date',
            'health_insurance_non_enrollment_reason',
            'welfare_pension_join_date',
            'pension_insurance_non_enrollment_reason',
            'employment_insurance_join_date',
            'employment_insurance_non_enrollment_reason',
        ]
        widgets = {
            'health_insurance_join_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'health_insurance_non_enrollment_reason': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'welfare_pension_join_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'pension_insurance_non_enrollment_reason': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'employment_insurance_join_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control form-control-sm'}),
            'employment_insurance_non_enrollment_reason': forms.TextInput(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
        }
