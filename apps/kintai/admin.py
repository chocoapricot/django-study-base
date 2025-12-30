from django.contrib import admin
from .models import StaffTimerecord, StaffTimerecordBreak


class StaffTimerecordBreakInline(admin.TabularInline):
    """休憩時間のインライン編集"""
    model = StaffTimerecordBreak
    extra = 1
    fields = ['break_start', 'break_end', 'start_latitude', 'start_longitude', 'end_latitude', 'end_longitude']


@admin.register(StaffTimerecord)
class StaffTimerecordAdmin(admin.ModelAdmin):
    """勤怠打刻の管理画面"""
    list_display = ['staff', 'work_date', 'start_time', 'end_time', 'work_hours_display', 'created_at']
    list_filter = ['work_date', 'created_at']
    search_fields = ['staff__name_last', 'staff__name_first', 'staff__staff_id']
    date_hierarchy = 'work_date'
    inlines = [StaffTimerecordBreakInline]
    
    fieldsets = (
        ('基本情報', {
            'fields': ('staff', 'work_date')
        }),
        ('打刻時刻', {
            'fields': ('start_time', 'end_time')
        }),
        ('位置情報', {
            'fields': (
                ('start_latitude', 'start_longitude'),
                ('end_latitude', 'end_longitude')
            ),
            'classes': ('collapse',)
        }),
        ('備考', {
            'fields': ('memo',)
        }),
    )
    
    readonly_fields = []
    
    def get_readonly_fields(self, request, obj=None):
        """作成後はスタッフと勤務日を変更不可にする"""
        if obj:  # 編集時
            return ['staff', 'work_date'] + self.readonly_fields
        return self.readonly_fields


@admin.register(StaffTimerecordBreak)
class StaffTimerecordBreakAdmin(admin.ModelAdmin):
    """休憩時間の管理画面"""
    list_display = ['timerecord', 'break_start', 'break_end', 'break_hours_display']
    list_filter = ['break_start']
    search_fields = ['timerecord__staff__name_last', 'timerecord__staff__name_first']
    
    fieldsets = (
        ('基本情報', {
            'fields': ('timerecord',)
        }),
        ('休憩時刻', {
            'fields': ('break_start', 'break_end')
        }),
        ('位置情報', {
            'fields': (
                ('start_latitude', 'start_longitude'),
                ('end_latitude', 'end_longitude')
            ),
            'classes': ('collapse',)
        }),
    )
