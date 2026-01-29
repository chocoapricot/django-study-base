from django.urls import path
from .views import (
    client_list, client_create, client_detail, client_update, client_delete, client_export,
    client_contacted_create, client_contacted_list, client_contacted_update, client_contacted_delete, client_contacted_detail,
    client_contact_schedule_create, client_contact_schedule_list, client_contact_schedule_detail, client_contact_schedule_update, client_contact_schedule_delete,
    client_change_history_list,
    client_department_create, client_department_list, client_department_update, client_department_delete, client_department_detail, client_department_change_history_list, issue_teishokubi_notification_from_department,
    client_user_create, client_user_list, client_user_detail, client_user_update, client_user_delete, client_user_mail_send,
    client_file_list, client_file_create, 
    client_file_delete, client_file_download,
    client_tag_edit
)

app_name = 'client'

urlpatterns = [
    path('', client_list, name='client_list'),
    path('export/', client_export, name='client_export'),
    path('client/create/', client_create, name='client_create'),
    path('client/detail/<int:pk>/', client_detail, name='client_detail'),
    path('client/update/<int:pk>/', client_update, name='client_update'),
    path('client/delete/<int:pk>/', client_delete, name='client_delete'),
    path('client/tag/edit/<int:pk>/', client_tag_edit, name='client_tag_edit'),
    # クライアント連絡履歴
    path('client/<int:client_pk>/contacted/create/', client_contacted_create, name='client_contacted_create'),
    path('client/<int:client_pk>/contacted/list/', client_contacted_list, name='client_contacted_list'),
    path('client/contacted/<int:pk>/detail/', client_contacted_detail, name='client_contacted_detail'),
    path('client/contacted/<int:pk>/update/', client_contacted_update, name='client_contacted_update'),
    path('client/contacted/<int:pk>/delete/', client_contacted_delete, name='client_contacted_delete'),
    # クライアント連絡予定
    path('client/<int:client_pk>/contact_schedule/create/', client_contact_schedule_create, name='client_contact_schedule_create'),
    path('client/<int:client_pk>/contact_schedule/list/', client_contact_schedule_list, name='client_contact_schedule_list'),
    path('client/contact_schedule/<int:pk>/detail/', client_contact_schedule_detail, name='client_contact_schedule_detail'),
    path('client/contact_schedule/<int:pk>/update/', client_contact_schedule_update, name='client_contact_schedule_update'),
    path('client/contact_schedule/<int:pk>/delete/', client_contact_schedule_delete, name='client_contact_schedule_delete'),
    # 変更履歴
    path('client/<int:pk>/change_history/', client_change_history_list, name='client_change_history_list'),
    # クライアント組織
    path('client/<int:client_pk>/department/create/', client_department_create, name='client_department_create'),
    path('client/<int:client_pk>/department/list/', client_department_list, name='client_department_list'),
    path('client/department/<int:pk>/detail/', client_department_detail, name='client_department_detail'),
    path('client/department/<int:pk>/issue_teishokubi_notification/', issue_teishokubi_notification_from_department, name='issue_teishokubi_notification_from_department'),
    path('client/department/<int:pk>/update/', client_department_update, name='client_department_update'),
    path('client/department/<int:pk>/delete/', client_department_delete, name='client_department_delete'),
    path('client/department/<int:pk>/change_history/', client_department_change_history_list, name='client_department_change_history_list'),
    # クライアント担当者
    path('client/<int:client_pk>/user/create/', client_user_create, name='client_user_create'),
    path('client/<int:client_pk>/user/list/', client_user_list, name='client_user_list'),
    path('client/user/<int:pk>/detail/', client_user_detail, name='client_user_detail'),
    path('client/user/<int:pk>/update/', client_user_update, name='client_user_update'),
    path('client/user/<int:pk>/delete/', client_user_delete, name='client_user_delete'),
    path('client/user/<int:pk>/mail_send/', client_user_mail_send, name='client_user_mail_send'),
    
    # ファイル管理
    path('client/<int:client_pk>/file/', client_file_list, name='client_file_list'),
    path('client/<int:client_pk>/file/create/', client_file_create, name='client_file_create'),
    path('client/file/<int:pk>/delete/', client_file_delete, name='client_file_delete'),
    path('client/file/<int:pk>/download/', client_file_download, name='client_file_download'),
]

