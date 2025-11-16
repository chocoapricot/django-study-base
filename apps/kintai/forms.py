from django import forms
from .models import StaffTimesheet, StaffTimecard
from apps.contract.models import StaffContract


class StaffTimesheetForm(forms.ModelForm):
    """月次勤怠フォーム"""
    
    class Meta:
        model = StaffTimesheet
        fields = ['staff_contract', 'year', 'month', 'memo']
        widgets = {
            'staff_contract': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'year': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': 2020, 'max': 2099}),
            'month': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': 1, 'max': 12}),
            'memo': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # スタッフ契約の選択肢を有効な契約のみに絞る
        self.fields['staff_contract'].queryset = StaffContract.objects.filter(
            start_date__isnull=False
        ).select_related('staff').order_by('-start_date')


class StaffTimecardForm(forms.ModelForm):
    """日次勤怠フォーム"""
    
    class Meta:
        model = StaffTimecard
        fields = ['work_date', 'work_type', 'start_time', 'start_time_next_day', 'end_time', 'end_time_next_day', 'break_minutes', 'paid_leave_days', 'memo']
        widgets = {
            'work_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'work_type': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control form-control-sm', 'type': 'time'}),
            'start_time_next_day': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control form-control-sm', 'type': 'time'}),
            'end_time_next_day': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'break_minutes': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': 0, 'value': 0}),
            'paid_leave_days': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': 0, 'max': 1, 'step': 0.5, 'value': 0}),
            'memo': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
        }
