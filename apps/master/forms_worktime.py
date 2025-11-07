from django import forms
from .models import WorkTimePattern, WorkTimePatternWork, WorkTimePatternBreak, PhraseTemplate


class WorkTimePatternForm(forms.ModelForm):
    """就業時間パターンフォーム"""
    class Meta:
        model = WorkTimePattern
        fields = ['name', 'memo', 'display_order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'memo': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class WorkTimePatternWorkForm(forms.ModelForm):
    """就業時間パターン勤務時間フォーム"""
    class Meta:
        model = WorkTimePatternWork
        fields = ['time_name', 'start_time', 'start_time_next_day', 'end_time', 'end_time_next_day', 'display_order']
        widgets = {
            'time_name': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control form-control-sm', 'type': 'time'}),
            'start_time_next_day': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control form-control-sm', 'type': 'time'}),
            'end_time_next_day': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
        }

    def __init__(self, *args, **kwargs):
        self.worktime_pattern = kwargs.pop('worktime_pattern', None)
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.worktime_pattern = self.instance.worktime_pattern
        
        # PhraseTemplateから時間名称を取得
        self.fields['time_name'].queryset = PhraseTemplate.get_active_by_title_key('WORKTIME_NAME')
        self.fields['time_name'].label_from_instance = lambda obj: obj.content
        self.fields['time_name'].empty_label = '選択してください'
        self.fields['time_name'].required = True


class WorkTimePatternBreakForm(forms.ModelForm):
    """就業時間パターン休憩時間フォーム"""
    class Meta:
        model = WorkTimePatternBreak
        fields = ['start_time', 'start_time_next_day', 'end_time', 'end_time_next_day', 'display_order']
        widgets = {
            'start_time': forms.TimeInput(attrs={'class': 'form-control form-control-sm', 'type': 'time'}),
            'start_time_next_day': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control form-control-sm', 'type': 'time'}),
            'end_time_next_day': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
        }

    def __init__(self, *args, **kwargs):
        self.work_time = kwargs.pop('work_time', None)
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.work_time = self.instance.work_time
