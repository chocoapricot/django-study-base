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
        fields = ['time_name', 'start_time', 'end_time', 'display_order']
        widgets = {
            'time_name': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control form-control-sm', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control form-control-sm', 'type': 'time'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
        }

    def __init__(self, *args, **kwargs):
        self.worktime_pattern = kwargs.pop('worktime_pattern', None)
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.worktime_pattern = self.instance.worktime_pattern
        
        # PhraseTemplateから時間名称を取得
        time_name_choices = [('', '選択してください（任意）')]
        phrases = PhraseTemplate.get_active_by_title_key('WORKTIME_NAME')
        time_name_choices.extend([
            (phrase.content, phrase.content) for phrase in phrases
        ])
        self.fields['time_name'] = forms.ChoiceField(
            choices=time_name_choices,
            label='時間名称',
            required=False,
            widget=forms.Select(attrs={'class': 'form-control form-control-sm'})
        )


class WorkTimePatternBreakForm(forms.ModelForm):
    """就業時間パターン休憩時間フォーム"""
    class Meta:
        model = WorkTimePatternBreak
        fields = ['start_time', 'end_time', 'display_order']
        widgets = {
            'start_time': forms.TimeInput(attrs={'class': 'form-control form-control-sm', 'type': 'time'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control form-control-sm', 'type': 'time'}),
            'display_order': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
        }

    def __init__(self, *args, **kwargs):
        self.work_time = kwargs.pop('work_time', None)
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.work_time = self.instance.work_time
