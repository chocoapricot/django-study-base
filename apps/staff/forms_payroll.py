from django import forms
from .models import StaffPayroll

class StaffPayrollForm(forms.ModelForm):
    class Meta:
        model = StaffPayroll
        fields = [
            'health_insurance_join_date',
            'welfare_pension_join_date',
            'employment_insurance_join_date',
        ]
        widgets = {
            'health_insurance_join_date': forms.DateInput(attrs={'type': 'date'}),
            'welfare_pension_join_date': forms.DateInput(attrs={'type': 'date'}),
            'employment_insurance_join_date': forms.DateInput(attrs={'type': 'date'}),
        }
