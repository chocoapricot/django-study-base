from django import forms
from .models import (
    OvertimePattern,
    TimeRounding,
)
from apps.common.forms import MyRadioSelect
from apps.common.constants import get_break_input_choices


class OvertimePatternForm(forms.ModelForm):
    """時間外算出パターンフォーム"""
    class Meta:
        model = OvertimePattern
        fields = [
            'name', 'calculation_type',
            'daily_overtime_enabled', 'daily_overtime_hours', 'daily_overtime_minutes',
            'weekly_overtime_enabled', 'weekly_overtime_hours', 'weekly_overtime_minutes',
            'monthly_overtime_enabled', 'monthly_overtime_hours',
            'monthly_estimated_enabled', 'monthly_estimated_hours',
            'monthly_range_min', 'monthly_range_max',
            'days_28_hours', 'days_28_minutes',
            'days_29_hours', 'days_29_minutes',
            'days_30_hours', 'days_30_minutes',
            'days_31_hours', 'days_31_minutes',
            'calculate_midnight_premium', 'memo', 'display_order', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'calculation_type': MyRadioSelect(),
            'calculate_midnight_premium': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'daily_overtime_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'daily_overtime_hours': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'daily_overtime_minutes': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0', 'max': '59'}),
            'weekly_overtime_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'weekly_overtime_hours': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'weekly_overtime_minutes': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': '0', 'max': '59'}),
            'monthly_overtime_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'monthly_overtime_hours': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'monthly_estimated_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'monthly_estimated_hours': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'monthly_range_min': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'monthly_range_max': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'days_28_hours': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'days_28_minutes': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'days_29_hours': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'days_29_minutes': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'days_30_hours': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'days_30_minutes': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'days_31_hours': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'days_31_minutes': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'memo': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class TimeRoundingForm(forms.ModelForm):
    """時間丸めマスタフォーム"""

    class Meta:
        model = TimeRounding
        fields = [
            'name', 'description', 'start_time_unit', 'start_time_method',
            'end_time_unit', 'end_time_method', 'break_input',
            'break_start_unit', 'break_start_method',
            'break_end_unit', 'break_end_method',
            'is_active', 'sort_order'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'description': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'start_time_unit': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'start_time_method': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'end_time_unit': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'end_time_method': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'break_input': forms.Select(
                choices=get_break_input_choices(),
                attrs={'class': 'form-control form-control-sm', 'id': 'id_break_input'}
            ),
            'break_start_unit': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'break_start_method': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'break_end_unit': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'break_end_method': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 必須フィールドのラベルにアスタリスクを追加
        required_fields = ['name', 'start_time_unit', 'start_time_method',
                          'end_time_unit', 'end_time_method']
        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].label = f"{self.fields[field_name].label} *"
