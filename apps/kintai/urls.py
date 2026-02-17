from django.urls import path
from . import views
from . import views_timerecord

app_name = 'kintai'

urlpatterns = [
    # 月次勤怠
    path('timesheet/', views.timesheet_list, name='timesheet_list'),
    path('timesheet/create/', views.timesheet_create, name='timesheet_create'),
    path('timesheet/<int:pk>/', views.timesheet_detail, name='timesheet_detail'),

    path('timesheet/<int:pk>/delete/', views.timesheet_delete, name='timesheet_delete'),
    
    # 契約検索
    path('contract/search/', views.contract_search, name='contract_search'),
    path('timesheet/preview/<int:contract_pk>/<str:target_month>/', views.timesheet_preview, name='timesheet_preview'),

    # スタッフ検索
    path('staff/search/', views.staff_search, name='staff_search'),
    path('staff/<int:staff_pk>/calendar/<str:target_month>/', views.staff_timecard_calendar, name='staff_timecard_calendar'),

    
    # 日次勤怠
    path('timecard/<int:timesheet_pk>/create/', views.timecard_create, name='timecard_create'),
    path('timecard/create/initial/<int:contract_pk>/<str:target_month>/', views.timecard_create_initial, name='timecard_create_initial'),
    path('timecard/calendar/initial/<int:contract_pk>/<str:target_month>/', views.timecard_calendar_initial, name='timecard_calendar_initial'),
    path('timecard/<int:timesheet_pk>/calendar/', views.timecard_calendar, name='timecard_calendar'),
    path('timecard/<int:pk>/edit/', views.timecard_edit, name='timecard_edit'),
    path('timecard/<int:pk>/delete/', views.timecard_delete, name='timecard_delete'),
    
    # 勤怠CSV取込
    path('timecard/import/', views.timecard_import, name='timecard_import'),
    path('timecard/import/upload/', views.timecard_import_upload, name='timecard_import_upload'),
    path('timecard/import/process/<str:task_id>/', views.timecard_import_process, name='timecard_import_process'),
    path('timecard/import/progress/<str:task_id>/', views.timecard_import_progress, name='timecard_import_progress'),
    
    # スタッフ向けタイムカード登録
    path('staff/timecard/register/', views.staff_timecard_register, name='staff_timecard_register'),
    path('staff/timecard/register/<int:contract_pk>/<str:target_month>/', views.staff_timecard_register_detail, name='staff_timecard_register_detail'),
    
    # 勤怠打刻
    path('timerecord/', views_timerecord.timerecord_list, name='timerecord_list'),
    path('timerecord/calender/', views_timerecord.timerecord_calender, name='timerecord_calender'),
    path('timerecord/punch/', views_timerecord.timerecord_punch, name='timerecord_punch'),
    path('timerecord/action/', views_timerecord.timerecord_action, name='timerecord_action'),
    path('timerecord/apply/', views_timerecord.timerecord_apply, name='timerecord_apply'),
    path('timerecord/withdraw/', views_timerecord.timerecord_withdraw, name='timerecord_withdraw'),
    path('timerecord/reverse_geocode/', views_timerecord.timerecord_reverse_geocode, name='timerecord_reverse_geocode'),
    path('timerecord/create/', views_timerecord.timerecord_create, name='timerecord_create'),
    path('timerecord/<int:pk>/', views_timerecord.timerecord_detail, name='timerecord_detail'),
    path('timerecord/<int:pk>/update/', views_timerecord.timerecord_update, name='timerecord_update'),
    path('timerecord/<int:pk>/delete/', views_timerecord.timerecord_delete, name='timerecord_delete'),
    
    # 休憩時間
    path('timerecord/<int:timerecord_pk>/break/create/', views_timerecord.timerecord_break_create, name='timerecord_break_create'),
    path('timerecord/break/<int:pk>/update/', views_timerecord.timerecord_break_update, name='timerecord_break_update'),
    path('timerecord/break/<int:pk>/delete/', views_timerecord.timerecord_break_delete, name='timerecord_break_delete'),

    # 勤怠打刻承認 (Company側)
    path('timerecord/approval/', views_timerecord.timerecord_approval_list, name='timerecord_approval_list'),
    path('timerecord/approval/<int:pk>/', views_timerecord.timerecord_approval_detail, name='timerecord_approval_detail'),
    path('timerecord/approval/<int:pk>/approve/', views_timerecord.timerecord_approval_approve, name='timerecord_approval_approve'),
    path('timerecord/approval/<int:pk>/reject/', views_timerecord.timerecord_approval_reject, name='timerecord_approval_reject'),
    path('timerecord/approval/<int:pk>/cancel/', views_timerecord.timerecord_approval_cancel, name='timerecord_approval_cancel'),

    # クライアント勤怠
    path('client/contract/search/', views.client_contract_search, name='client_contract_search'),
    path('client/timesheet/create/', views.client_timesheet_create, name='client_timesheet_create'),
    path('client/timesheet/<int:pk>/', views.client_timesheet_detail, name='client_timesheet_detail'),
    path('client/timesheet/<int:pk>/delete/', views.client_timesheet_delete, name='client_timesheet_delete'),
    path('client/timesheet/preview/<int:assignment_pk>/<str:target_month>/', views.client_timesheet_preview, name='client_timesheet_preview'),
    path('client/timecard/<int:timesheet_pk>/create/', views.client_timecard_create, name='client_timecard_create'),
    path('client/timecard/create/initial/<int:assignment_pk>/<str:target_month>/', views.client_timecard_create_initial, name='client_timecard_create_initial'),
    path('client/timecard/<int:pk>/edit/', views.client_timecard_edit, name='client_timecard_edit'),
    path('client/timecard/<int:pk>/delete/', views.client_timecard_delete, name='client_timecard_delete'),
    path('client/timecard/calendar/initial/<int:assignment_pk>/<str:target_month>/', views.client_timecard_calendar_initial, name='client_timecard_calendar_initial'),
    path('client/timecard/<int:pk>/calendar/', views.client_timecard_calendar, name='client_timecard_calendar'),
    
    # 勤怠登録状況管理
    path('status/management/', views.kintai_status_management, name='kintai_status_management'),
]

