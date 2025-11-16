from django.urls import path
from . import views

app_name = 'kintai'

urlpatterns = [
    # 月次勤怠
    path('timesheet/', views.timesheet_list, name='timesheet_list'),
    path('timesheet/create/', views.timesheet_create, name='timesheet_create'),
    path('timesheet/<int:pk>/', views.timesheet_detail, name='timesheet_detail'),
    path('timesheet/<int:pk>/edit/', views.timesheet_edit, name='timesheet_edit'),
    path('timesheet/<int:pk>/delete/', views.timesheet_delete, name='timesheet_delete'),
    
    # 日次勤怠
    path('timecard/<int:timesheet_pk>/create/', views.timecard_create, name='timecard_create'),
    path('timecard/<int:timesheet_pk>/calendar/', views.timecard_calendar, name='timecard_calendar'),
    path('timecard/<int:pk>/edit/', views.timecard_edit, name='timecard_edit'),
    path('timecard/<int:pk>/delete/', views.timecard_delete, name='timecard_delete'),
]
