# urls.py
from django.urls import path
from .views import (
    staff_list, staff_create, staff_detail, staff_update, staff_delete, staff_face, staff_rirekisho, staff_fuyokojo, staff_kyushoku,
    staff_export,
    staff_contacted_create, staff_contacted_list, staff_contacted_update, staff_contacted_delete, staff_contacted_detail,
    staff_change_history_list, staff_mail_send,
    staff_qualification_list, staff_qualification_create, staff_qualification_update, staff_qualification_delete,
    staff_skill_list, staff_skill_create, staff_skill_update, staff_skill_delete,
    staff_file_list, staff_file_create,
    staff_file_delete, staff_file_download,
    staff_mynumber_detail, staff_mynumber_create, staff_mynumber_edit, staff_mynumber_delete,
    staff_mynumber_request_detail,
    staff_contact_detail, staff_contact_create, staff_contact_edit, staff_contact_delete,
    staff_contact_request_detail,
    staff_bank_detail, staff_bank_create, staff_bank_edit, staff_bank_delete, staff_bank_request_detail,
    staff_profile_request_detail,
    staff_international_detail, staff_international_create, staff_international_edit, staff_international_delete,
    staff_international_request_detail,
    staff_disability_detail, staff_disability_create, staff_disability_edit, staff_disability_delete,
    staff_disability_request_detail,
)

app_name = 'staff'

urlpatterns = [
    path('', staff_list, name='staff_list'),
    path('export/', staff_export, name='staff_export'),
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

    # マイナンバー管理
    path('staff/<int:staff_id>/mynumber/', staff_mynumber_detail, name='staff_mynumber_detail'),
    path('staff/<int:staff_id>/mynumber/create/', staff_mynumber_create, name='staff_mynumber_create'),
    path('staff/<int:staff_id>/mynumber/edit/', staff_mynumber_edit, name='staff_mynumber_edit'),
    path('staff/<int:staff_id>/mynumber/delete/', staff_mynumber_delete, name='staff_mynumber_delete'),
    path('staff/<int:staff_pk>/mynumber/request/<int:pk>/', staff_mynumber_request_detail, name='staff_mynumber_request_detail'),

    # 連絡先情報管理
    path('staff/<int:staff_id>/contact/', staff_contact_detail, name='staff_contact_detail'),
    path('staff/<int:staff_id>/contact/create/', staff_contact_create, name='staff_contact_create'),
    path('staff/<int:staff_id>/contact/edit/', staff_contact_edit, name='staff_contact_edit'),
    path('staff/<int:staff_id>/contact/delete/', staff_contact_delete, name='staff_contact_delete'),
    path('staff/<int:staff_pk>/contact/request/<int:pk>/', staff_contact_request_detail, name='staff_contact_request_detail'),

    # 銀行情報管理
    path('staff/<int:staff_id>/bank/', staff_bank_detail, name='staff_bank_detail'),
    path('staff/<int:staff_id>/bank/create/', staff_bank_create, name='staff_bank_create'),
    path('staff/<int:staff_id>/bank/edit/', staff_bank_edit, name='staff_bank_edit'),
    path('staff/<int:staff_id>/bank/delete/', staff_bank_delete, name='staff_bank_delete'),
    path('staff/<int:staff_pk>/bank/request/<int:pk>/', staff_bank_request_detail, name='staff_bank_request_detail'),

    # プロフィール申請
    path('staff/<int:staff_pk>/profile/request/<int:pk>/', staff_profile_request_detail, name='staff_profile_request_detail'),

    # 外国籍情報管理
    path('staff/<int:staff_id>/international/', staff_international_detail, name='staff_international_detail'),
    path('staff/<int:staff_id>/international/create/', staff_international_create, name='staff_international_create'),
    path('staff/<int:staff_id>/international/edit/', staff_international_edit, name='staff_international_edit'),
    path('staff/<int:staff_id>/international/delete/', staff_international_delete, name='staff_international_delete'),
    
    # 外国籍情報申請
    path('staff/<int:staff_pk>/international/request/<int:pk>/', staff_international_request_detail, name='staff_international_request_detail'),

    # 障害者情報管理
    path('staff/<int:staff_pk>/disability/', staff_disability_detail, name='staff_disability_detail'),
    path('staff/<int:staff_pk>/disability/create/', staff_disability_create, name='staff_disability_create'),
    path('staff/<int:staff_pk>/disability/edit/', staff_disability_edit, name='staff_disability_edit'),
    path('staff/<int:staff_pk>/disability/delete/', staff_disability_delete, name='staff_disability_delete'),
    path('staff/<int:staff_pk>/disability/request/<int:pk>/', staff_disability_request_detail, name='staff_disability_request_detail'),
]
