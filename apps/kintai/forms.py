from django import forms
from .models import StaffTimesheet, StaffTimecard
from apps.contract.models import StaffContract
from datetime import datetime


class StaffTimesheetForm(forms.ModelForm):
    """月次勤怠フォーム"""
    target_month = forms.CharField(
        label='対象年月',
        widget=forms.DateInput(attrs={'type': 'month', 'class': 'form-control form-control-sm'}),
        required=True
    )
    
    class Meta:
        model = StaffTimesheet
        fields = ['staff_contract']
        widgets = {
            'staff_contract': forms.Select(attrs={'class': 'form-control form-control-sm'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # スタッフ契約の選択肢を有効な契約のみに絞る
        self.fields['staff_contract'].queryset = StaffContract.objects.filter(
            start_date__isnull=False
        ).select_related('staff').order_by('-start_date')

        # instance が存在する場合、target_month の初期値を設定
        if self.instance and self.instance.target_month:
            self.initial['target_month'] = self.instance.target_month.strftime('%Y-%m')

    def clean_target_month(self):
        target_month_str = self.cleaned_data.get('target_month')
        if target_month_str:
            try:
                # YYYY-MM 形式から datetime.date オブジェクトに変換
                selected_date = datetime.strptime(target_month_str, '%Y-%m').date()
                # その月の1日に設定
                return selected_date.replace(day=1)
            except ValueError:
                raise forms.ValidationError('無効な年月形式です。')
        return None

    def clean(self):
        cleaned_data = super().clean()
        staff_contract = cleaned_data.get('staff_contract')
        target_month = cleaned_data.get('target_month')

        if staff_contract and target_month:
            from calendar import monthrange
            from datetime import date
            from django.core.exceptions import ValidationError

            # 契約期間のチェック
            try:
                _, last_day_num = monthrange(target_month.year, target_month.month)
                last_day = date(target_month.year, target_month.month, last_day_num)
            except (ValueError, TypeError):
                last_day = None

            if target_month and last_day:
                sc_start = staff_contract.start_date
                sc_end = staff_contract.end_date

                if sc_start and last_day < sc_start:
                    raise forms.ValidationError('指定した年月はスタッフ契約の契約期間外です。')

                if sc_end and target_month > sc_end:
                    raise forms.ValidationError('指定した年月はスタッフ契約の契約期間外です。')

            # ユニーク制約のチェック
            # 同じスタッフ契約と対象年月を持つ月次勤怠が既に存在しないか確認
            qs = StaffTimesheet.objects.filter(
                staff_contract=staff_contract,
                target_month=target_month
            )
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk) # 編集時は自分自身を除外

            if qs.exists():
                raise forms.ValidationError('このスタッフ契約と年月では、既に月次勤怠が作成されています。')

        return cleaned_data


    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.target_month = self.cleaned_data.get('target_month')
        if commit:
            instance.save()
        return instance


class StaffTimecardForm(forms.ModelForm):
    """日次勤怠フォーム"""

    def __init__(self, *args, **kwargs):
        # Accept optional timesheet kwarg for calendar/bulk edit validation
        self.timesheet = kwargs.pop('timesheet', None)
        super().__init__(*args, **kwargs)
    
    class Meta:
        model = StaffTimecard
        fields = ['work_date', 'work_type', 'start_time', 'start_time_next_day', 'end_time', 'end_time_next_day', 'break_minutes', 'late_night_break_minutes', 'paid_leave_days', 'memo']
        widgets = {
            'work_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'work_type': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'start_time': forms.TimeInput(attrs={'class': 'form-control form-control-sm', 'type': 'time'}),
            'start_time_next_day': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'end_time': forms.TimeInput(attrs={'class': 'form-control form-control-sm', 'type': 'time'}),
            'end_time_next_day': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'break_minutes': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': 0, 'value': 0}),
            'late_night_break_minutes': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': 0, 'value': 0}),
            'paid_leave_days': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': 0, 'max': 1, 'step': 0.5, 'value': 0}),
            'memo': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
        }

    def clean(self):
        cleaned = super().clean()
        work_date = cleaned.get('work_date')

        # Determine timesheet (either passed in or from instance)
        timesheet = self.timesheet
        if not timesheet and hasattr(self, 'instance') and getattr(self.instance, 'timesheet', None):
            timesheet = self.instance.timesheet

        if timesheet and work_date:
            sc = getattr(timesheet, 'staff_contract', None)
            if sc:
                sc_start = sc.start_date
                sc_end = sc.end_date
                if sc_start and work_date < sc_start:
                    raise forms.ValidationError('勤務日はスタッフ契約の契約期間外です。')
                if sc_end and work_date > sc_end:
                    raise forms.ValidationError('勤務日はスタッフ契約の契約期間外です。')

        return cleaned
