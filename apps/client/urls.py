from django.urls import path
from .views import (
    client_list, client_create, client_detail, client_update, client_delete,
    client_contacted_create, client_contacted_list, client_contacted_update, client_contacted_delete, client_contacted_detail,
    client_change_history_list,
    client_department_create, client_department_list, client_department_update, client_department_delete,
    client_user_create, client_user_list, client_user_update, client_user_delete,
    client_file_list, client_file_create, client_file_detail, 
    client_file_update, client_file_delete, client_file_download
)

app_name = 'client'

urlpatterns = [
    path('', client_list, name='client_list'),
    path('client/create/', client_create, name='client_create'),
    path('client/detail/<int:pk>/', client_detail, name='client_detail'),
    path('client/update/<int:pk>/', client_update, name='client_update'),
    path('client/delete/<int:pk>/', client_delete, name='client_delete'),
    # クライアント連絡履歴
    path('client/<int:client_pk>/contacted/create/', client_contacted_create, name='client_contacted_create'),
    path('client/<int:client_pk>/contacted/list/', client_contacted_list, name='client_contacted_list'),
    path('client/contacted/<int:pk>/detail/', client_contacted_detail, name='client_contacted_detail'),
    path('client/contacted/<int:pk>/update/', client_contacted_update, name='client_contacted_update'),
    path('client/contacted/<int:pk>/delete/', client_contacted_delete, name='client_contacted_delete'),
    # 変更履歴
    path('client/<int:pk>/change_history/', client_change_history_list, name='client_change_history_list'),
    # クライアント組織
    path('client/<int:client_pk>/department/create/', client_department_create, name='client_department_create'),
    path('client/<int:client_pk>/department/list/', client_department_list, name='client_department_list'),
    path('client/department/<int:pk>/update/', client_department_update, name='client_department_update'),
    path('client/department/<int:pk>/delete/', client_department_delete, name='client_department_delete'),
    # クライアント担当者
    path('client/<int:client_pk>/user/create/', client_user_create, name='client_user_create'),
    path('client/<int:client_pk>/user/list/', client_user_list, name='client_user_list'),
    path('client/user/<int:pk>/update/', client_user_update, name='client_user_update'),
    path('client/user/<int:pk>/delete/', client_user_delete, name='client_user_delete'),
    
    # ファイル管理
    path('client/<int:client_pk>/file/', client_file_list, name='client_file_list'),
    path('client/<int:client_pk>/file/create/', client_file_create, name='client_file_create'),
    path('client/file/<int:pk>/detail/', client_file_detail, name='client_file_detail'),
    path('client/file/<int:pk>/update/', client_file_update, name='client_file_update'),
    path('client/file/<int:pk>/delete/', client_file_delete, name='client_file_delete'),
    path('client/file/<int:pk>/download/', client_file_download, name='client_file_download'),
]

