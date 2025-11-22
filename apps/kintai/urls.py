from django.urls import path
from . import views

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

    
    # 日次勤怠
    path('timecard/<int:timesheet_pk>/create/', views.timecard_create, name='timecard_create'),
    path('timecard/create/initial/<int:contract_pk>/<str:target_month>/', views.timecard_create_initial, name='timecard_create_initial'),
    path('timecard/calendar/initial/<int:contract_pk>/<str:target_month>/', views.timecard_calendar_initial, name='timecard_calendar_initial'),
    path('timecard/<int:timesheet_pk>/calendar/', views.timecard_calendar, name='timecard_calendar'),
    path('timecard/<int:pk>/edit/', views.timecard_edit, name='timecard_edit'),
    path('timecard/<int:pk>/delete/', views.timecard_delete, name='timecard_delete'),
]
