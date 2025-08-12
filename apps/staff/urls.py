# urls.py
from django.urls import path
from .views import (
    staff_list, staff_create, staff_detail, staff_update, staff_delete, staff_face, staff_rirekisho, staff_fuyokojo, staff_kyushoku,
    staff_contacted_create, staff_contacted_list, staff_contacted_update, staff_contacted_delete, staff_contacted_detail,
    staff_change_history_list, staff_mail_send,
    staff_qualification_list, staff_qualification_create, staff_qualification_update, staff_qualification_delete,
    staff_skill_list, staff_skill_create, staff_skill_update, staff_skill_delete,
    staff_file_list, staff_file_create, 
    staff_file_delete, staff_file_download
)

app_name = 'staff'

urlpatterns = [
    path('', staff_list, name='staff_list'),
    path('staff/create/', staff_create, name='staff_create'),
    path('staff/detail/<int:pk>/', staff_detail, name='staff_detail'),
    path('staff/face/<int:pk>/'  , staff_face  , name='staff_face'),
    path('staff/update/<int:pk>/', staff_update, name='staff_update'),
    path('staff/delete/<int:pk>/', staff_delete, name='staff_delete'),
    path('staff/rirekisho/<int:pk>/', staff_rirekisho, name='staff_rirekisho'),
    path('staff/kyushoku/<int:pk>/', staff_kyushoku, name='staff_kyushoku'),
    path('staff/fuyokojo/<int:pk>/', staff_fuyokojo, name='staff_fuyokojo'),

    # 連絡履歴
    path('staff/<int:staff_pk>/contacted/create/', staff_contacted_create, name='staff_contacted_create'),
    path('staff/<int:staff_pk>/contacted/list/', staff_contacted_list, name='staff_contacted_list'),
    path('staff/contacted/<int:pk>/detail/', staff_contacted_detail, name='staff_contacted_detail'),
    path('staff/contacted/<int:pk>/update/', staff_contacted_update, name='staff_contacted_update'),
    path('staff/contacted/<int:pk>/delete/', staff_contacted_delete, name='staff_contacted_delete'),
    
    # メール送信
    path('staff/<int:pk>/mail/send/', staff_mail_send, name='staff_mail_send'),

    # 変更履歴
    path('staff/<int:pk>/change_history/', staff_change_history_list, name='staff_change_history_list'),
    
    # 資格管理
    path('staff/<int:staff_pk>/qualification/', staff_qualification_list, name='staff_qualification_list'),
    path('staff/<int:staff_pk>/qualification/create/', staff_qualification_create, name='staff_qualification_create'),
    path('staff/qualification/<int:pk>/update/', staff_qualification_update, name='staff_qualification_update'),
    path('staff/qualification/<int:pk>/delete/', staff_qualification_delete, name='staff_qualification_delete'),
    
    # 技能管理
    path('staff/<int:staff_pk>/skill/', staff_skill_list, name='staff_skill_list'),
    path('staff/<int:staff_pk>/skill/create/', staff_skill_create, name='staff_skill_create'),
    path('staff/skill/<int:pk>/update/', staff_skill_update, name='staff_skill_update'),
    path('staff/skill/<int:pk>/delete/', staff_skill_delete, name='staff_skill_delete'),
    
    # ファイル管理
    path('staff/<int:staff_pk>/file/', staff_file_list, name='staff_file_list'),
    path('staff/<int:staff_pk>/file/create/', staff_file_create, name='staff_file_create'),
    path('staff/file/<int:pk>/delete/', staff_file_delete, name='staff_file_delete'),
    path('staff/file/<int:pk>/download/', staff_file_download, name='staff_file_download'),
]
