from django import forms
from .models import StaffTimesheet, StaffTimecard, StaffTimerecord, StaffTimerecordBreak
from apps.contract.models import StaffContract
from apps.staff.models import Staff
from django.utils import timezone
from datetime import datetime, timedelta


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
        
        # work_time_pattern_workの選択肢を契約の就業時間パターンに絞る
        if self.timesheet and self.timesheet.staff_contract and self.timesheet.staff_contract.worktime_pattern:
            self.fields['work_time_pattern_work'].queryset = self.timesheet.staff_contract.worktime_pattern.work_times.filter(
                time_name__is_active=True
            ).order_by('display_order')
        else:
            # timesheetがない場合は空のクエリセット
            from apps.master.models import WorkTimePatternWork
            self.fields['work_time_pattern_work'].queryset = WorkTimePatternWork.objects.none()
    
    class Meta:
        model = StaffTimecard
        fields = ['work_date', 'work_type', 'work_time_pattern_work', 'start_time', 'start_time_next_day', 'end_time', 'end_time_next_day', 'break_minutes', 'late_night_break_minutes', 'paid_leave_days', 'memo']
        widgets = {
            'work_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'work_type': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'work_time_pattern_work': forms.Select(attrs={'class': 'form-control form-control-sm'}),
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


class StaffTimerecordForm(forms.ModelForm):
    """勤怠打刻フォーム"""
    rounded_start_time = forms.TimeField(
        label='開始時刻',
        widget=forms.TimeInput(attrs={'class': 'form-control form-control-sm', 'type': 'time'}),
        required=False
    )
    rounded_start_time_next_day = forms.BooleanField(
        label='翌日',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        required=False
    )
    rounded_end_time = forms.TimeField(
        label='終了時刻',
        widget=forms.TimeInput(attrs={'class': 'form-control form-control-sm', 'type': 'time'}),
        required=False
    )
    rounded_end_time_next_day = forms.BooleanField(
        label='翌日',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        required=False
    )
    
    class Meta:
        model = StaffTimerecord
        fields = ['staff_contract', 'work_date', 'rounded_start_time', 'rounded_end_time',
                  'start_latitude', 'start_longitude', 'end_latitude', 'end_longitude', 'memo']
        widgets = {
            'staff_contract': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'work_date': forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'start_latitude': forms.HiddenInput(),
            'start_longitude': forms.HiddenInput(),
            'end_latitude': forms.HiddenInput(),
            'end_longitude': forms.HiddenInput(),
            'memo': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # 登録・編集を確実にするため契約を必須にする
        self.fields['staff_contract'].required = True

        # インスタンスがある場合、DateTimeFieldをTimeと翌日フラグに変換
        if self.instance and self.instance.pk:
            if self.instance.rounded_start_time:
                local_start = timezone.localtime(self.instance.rounded_start_time)
                self.initial['rounded_start_time'] = local_start.time()
                self.initial['rounded_start_time_next_day'] = (
                    self.instance.work_date and local_start.date() > self.instance.work_date
                )

            if self.instance.rounded_end_time:
                local_end = timezone.localtime(self.instance.rounded_end_time)
                self.initial['rounded_end_time'] = local_end.time()
                self.initial['rounded_end_time_next_day'] = (
                    self.instance.work_date and local_end.date() > self.instance.work_date
                )

        # ユーザーがスタッフの場合、自分の有効な契約のみ選択可能
        if self.user and self.user.email:
            try:
                # メールアドレスでスタッフを特定
                staff = Staff.objects.get(email=self.user.email)
                
                # 有効な契約（開始日が設定されているもの）かつスタッフ確認済み
                self.fields['staff_contract'].queryset = StaffContract.objects.filter(
                    staff=staff,
                    start_date__isnull=False,
                    confirmed_at__isnull=False
                ).select_related('staff').order_by('-start_date')
                
                # 選択肢が一つしかない場合は自動選択
                if self.fields['staff_contract'].queryset.count() == 1:
                    self.fields['staff_contract'].initial = self.fields['staff_contract'].queryset.first()
            except Staff.DoesNotExist:
                # スタッフが見つからない場合は選択肢を空にする
                self.fields['staff_contract'].queryset = StaffContract.objects.none()
        elif self.user:
             # メールアドレスがない場合なども空にする
             self.fields['staff_contract'].queryset = StaffContract.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        work_date = cleaned_data.get('work_date')

        # 開始時刻の処理
        start_time = cleaned_data.get('rounded_start_time')
        start_next_day = cleaned_data.get('rounded_start_time_next_day')
        if work_date and start_time:
            dt = datetime.combine(work_date, start_time)
            if start_next_day:
                dt += timedelta(days=1)
            cleaned_data['rounded_start_time'] = timezone.make_aware(dt)

        # 終了時刻の処理
        end_time = cleaned_data.get('rounded_end_time')
        end_next_day = cleaned_data.get('rounded_end_time_next_day')
        if work_date and end_time:
            dt = datetime.combine(work_date, end_time)
            if end_next_day:
                dt += timedelta(days=1)
            cleaned_data['rounded_end_time'] = timezone.make_aware(dt)

        start = cleaned_data.get('rounded_start_time')
        end = cleaned_data.get('rounded_end_time')

        if start and end and end <= start:
            raise forms.ValidationError('終了時刻は開始時刻より後の時刻を入力してください。')

        return cleaned_data


class StaffTimerecordBreakForm(forms.ModelForm):
    """休憩時間フォーム"""
    rounded_break_start = forms.TimeField(
        label='休憩開始時刻',
        widget=forms.TimeInput(attrs={'class': 'form-control form-control-sm', 'type': 'time'}),
        required=True
    )
    break_start_next_day = forms.BooleanField(
        label='翌日',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        required=False
    )
    rounded_break_end = forms.TimeField(
        label='休憩終了時刻',
        widget=forms.TimeInput(attrs={'class': 'form-control form-control-sm', 'type': 'time'}),
        required=False
    )
    break_end_next_day = forms.BooleanField(
        label='翌日',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        required=False
    )
    
    class Meta:
        model = StaffTimerecordBreak
        fields = ['rounded_break_start', 'rounded_break_end',
                  'start_latitude', 'start_longitude', 'end_latitude', 'end_longitude']
        widgets = {
            'start_latitude': forms.HiddenInput(),
            'start_longitude': forms.HiddenInput(),
            'end_latitude': forms.HiddenInput(),
            'end_longitude': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        self.timerecord = kwargs.pop('timerecord', None)
        super().__init__(*args, **kwargs)

        # インスタンスがある場合、DateTimeFieldをTimeと翌日フラグに変換
        if self.instance and self.instance.pk:
            work_date = self.instance.timerecord.work_date if self.instance.timerecord else None

            if self.instance.rounded_break_start:
                local_start = timezone.localtime(self.instance.rounded_break_start)
                self.initial['rounded_break_start'] = local_start.time()
                self.initial['break_start_next_day'] = (
                    work_date and local_start.date() > work_date
                )

            if self.instance.rounded_break_end:
                local_end = timezone.localtime(self.instance.rounded_break_end)
                self.initial['rounded_break_end'] = local_end.time()
                self.initial['break_end_next_day'] = (
                    work_date and local_end.date() > work_date
                )

    def clean(self):
        cleaned_data = super().clean()

        # timerecord がない場合は instance から取得を試みる
        timerecord = self.timerecord or (self.instance.timerecord if self.instance.pk else None)
        if not timerecord:
            return cleaned_data

        work_date = timerecord.work_date

        # 開始時刻の処理
        start_time = cleaned_data.get('rounded_break_start')
        start_next_day = cleaned_data.get('break_start_next_day')
        if work_date and start_time:
            dt = datetime.combine(work_date, start_time)
            if start_next_day:
                dt += timedelta(days=1)
            cleaned_data['rounded_break_start'] = timezone.make_aware(dt)

        # 終了時刻の処理
        end_time = cleaned_data.get('rounded_break_end')
        end_next_day = cleaned_data.get('break_end_next_day')
        if work_date and end_time:
            dt = datetime.combine(work_date, end_time)
            if end_next_day:
                dt += timedelta(days=1)
            cleaned_data['rounded_break_end'] = timezone.make_aware(dt)

        start = cleaned_data.get('rounded_break_start')
        end = cleaned_data.get('rounded_break_end')

        if start and end and end <= start:
            raise forms.ValidationError('休憩終了時刻は休憩開始時刻より後の時刻を入力してください。')

        return cleaned_data
