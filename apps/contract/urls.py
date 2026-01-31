from django.urls import path
from . import views
from .views_client import client_staff_assignment_detail_list
from .views_assignment import contract_assignment_haken_view, contract_assignment_haken_delete

app_name = 'contract'

urlpatterns = [
    path('', views.contract_index, name='contract_index'),
    
    # クライアント契約
    path('client/', views.client_contract_list, name='client_contract_list'),
    path('client/create/', views.client_contract_create, name='client_contract_create'),
    path('client/<int:pk>/', views.client_contract_detail, name='client_contract_detail'),
    path('client/<int:pk>/update/', views.client_contract_update, name='client_contract_update'),
    path('client/<int:pk>/delete/', views.client_contract_delete, name='client_contract_delete'),
    path('client/<int:pk>/extend/', views.client_contract_extend, name='client_contract_extend'),
    path('client/<int:pk>/approve/', views.client_contract_approve, name='client_contract_approve'),
    path('client/<int:pk>/issue/', views.client_contract_issue, name='client_contract_issue'),
    path('client/<int:pk>/issue_quotation/', views.issue_quotation, name='issue_quotation'),
    path('client/<int:pk>/issue_teishokubi_notification/', views.issue_teishokubi_notification, name='issue_teishokubi_notification'),
    path('client/<int:pk>/issue_dispatch_ledger/', views.issue_dispatch_ledger, name='issue_dispatch_ledger'),
    path('client/<int:pk>/confirm/', views.client_contract_confirm, name='client_contract_confirm'),
    path('client/confirm_list/', views.client_contract_confirm_list, name='client_contract_confirm_list'),
    path('client/<int:pk>/pdf/', views.client_contract_pdf, name='client_contract_pdf'),
    path('client/<int:pk>/draft_pdf/', views.client_contract_draft_pdf, name='client_contract_draft_pdf'),
    path('client/<int:pk>/draft_quotation/', views.client_contract_draft_quotation, name='client_contract_draft_quotation'),
    path('client/<int:pk>/draft_haken_notification/', views.client_contract_draft_haken_notification, name='client_contract_draft_haken_notification'),
    path('client/<int:pk>/draft_dispatch_ledger/', views.client_contract_draft_dispatch_ledger, name='client_contract_draft_dispatch_ledger'),
    path('client/<int:pk>/teishokubi_notification_pdf/', views.client_teishokubi_notification_pdf, name='client_teishokubi_notification_pdf'),
    path('client/<int:pk>/dispatch_ledger_pdf/', views.client_dispatch_ledger_pdf, name='client_dispatch_ledger_pdf'),
    path('client/export/', views.client_contract_export, name='client_contract_export'),
    path('client/<int:pk>/ai_check/', views.client_contract_ai_check, name='client_contract_ai_check'),

    # クライアント契約フラッグ管理
    path('client/<int:contract_pk>/flag/', views.client_contract_flag_list, name='client_contract_flag_list'),
    path('client/<int:contract_pk>/flag/create/', views.client_contract_flag_create, name='client_contract_flag_create'),
    path('client/flag/<int:pk>/update/', views.client_contract_flag_update, name='client_contract_flag_update'),
    path('client/flag/<int:pk>/delete/', views.client_contract_flag_delete, name='client_contract_flag_delete'),

    # スタッフ契約
    path('staff/', views.staff_contract_list, name='staff_contract_list'),
    path('staff/create/', views.staff_contract_create, name='staff_contract_create'),
    path('staff/<int:pk>/', views.staff_contract_detail, name='staff_contract_detail'),
    path('staff/<int:pk>/update/', views.staff_contract_update, name='staff_contract_update'),
    path('staff/<int:pk>/delete/', views.staff_contract_delete, name='staff_contract_delete'),
    path('staff/<int:pk>/extend/', views.staff_contract_extend, name='staff_contract_extend'),
    path('staff/<int:pk>/approve/', views.staff_contract_approve, name='staff_contract_approve'),
    path('staff/<int:pk>/issue/', views.staff_contract_issue, name='staff_contract_issue'),
    path('staff/confirm_list/', views.staff_contract_confirm_list, name='staff_contract_confirm_list'),
    path('staff/<int:pk>/pdf/', views.staff_contract_pdf, name='staff_contract_pdf'),
    path('staff/<int:pk>/draft_pdf/', views.staff_contract_draft_pdf, name='staff_contract_draft_pdf'),
    path('staff/<int:pk>/ai_check/', views.staff_contract_ai_check, name='staff_contract_ai_check'),
    path('staff/export/', views.staff_contract_export, name='staff_contract_export'),
    path('staff/expire_list/', views.staff_contract_expire_list, name='staff_contract_expire_list'),
    path('staff/teishokubi/', views.staff_contract_teishokubi_list, name='staff_contract_teishokubi_list'),
    path('staff/teishokubi/<int:pk>/', views.staff_contract_teishokubi_detail, name='staff_contract_teishokubi_detail'),
    path('staff/teishokubi/<int:pk>/detail/create/', views.staff_contract_teishokubi_detail_create, name='staff_contract_teishokubi_detail_create'),

    # 履歴
    path('client/<int:pk>/issue_history/', views.client_contract_issue_history_list, name='client_contract_issue_history_list'),
    path('client/<int:pk>/change_history/', views.client_contract_change_history_list, name='client_contract_change_history_list'),
    path('staff/<int:pk>/issue_history/', views.staff_contract_issue_history_list, name='staff_contract_issue_history_list'),
    path('staff/<int:pk>/change_history/', views.staff_contract_change_history_list, name='staff_contract_change_history_list'),
    path('view/client/<int:pk>/', views.view_client_contract_pdf, name='view_client_contract_pdf'),
    path('view/staff/<int:pk>/', views.view_staff_contract_pdf, name='view_staff_contract_pdf'),
    path('download/client/<int:pk>/', views.download_client_contract_pdf, name='download_client_contract_pdf'),
    path('download/staff/<int:pk>/', views.download_staff_contract_pdf, name='download_staff_contract_pdf'),

    
    # 選択画面
    path('client-select/', views.client_select, name='client_select'),
    path('staff-select/', views.staff_select, name='staff_select'),
    
    # API
    path('api/contract-patterns-by-employment/', views.get_contract_patterns_by_employment_type, name='get_contract_patterns_by_employment_type'),

    # 紹介予定派遣
    path('client/ttp/view/<int:haken_pk>/', views.client_contract_ttp_view, name='client_contract_ttp_view'),
    path('client/ttp/create/<int:haken_pk>/', views.client_contract_ttp_create, name='client_contract_ttp_create'),
    path('client/ttp/<int:pk>/detail/', views.client_contract_ttp_detail, name='client_contract_ttp_detail'),
    path('client/ttp/<int:pk>/update/', views.client_contract_ttp_update, name='client_contract_ttp_update'),
    path('client/ttp/<int:pk>/delete/', views.client_contract_ttp_delete, name='client_contract_ttp_delete'),

    # 派遣抵触日制限外
    path('client/haken-exempt/view/<int:haken_pk>/', views.client_contract_haken_exempt_view, name='client_contract_haken_exempt_view'),
    path('client/haken-exempt/create/<int:haken_pk>/', views.client_contract_haken_exempt_create, name='client_contract_haken_exempt_create'),
    path('client/haken-exempt/<int:pk>/detail/', views.client_contract_haken_exempt_detail, name='client_contract_haken_exempt_detail'),
    path('client/haken-exempt/<int:pk>/update/', views.client_contract_haken_exempt_update, name='client_contract_haken_exempt_update'),
    path('client/haken-exempt/<int:pk>/delete/', views.client_contract_haken_exempt_delete, name='client_contract_haken_exempt_delete'),

    # 事業所抵触日
    path('client/teishokubi/', views.client_teishokubi_list, name='client_teishokubi_list'),

    # 契約アサイン
    path('client/<int:pk>/assign/', views.client_contract_assignment_view, name='client_contract_assignment'),
    path('client/<int:pk>/staff-assignment-detail/', client_staff_assignment_detail_list, name='client_staff_assignment_detail_list'),
    path('staff/<int:pk>/assign/', views.staff_contract_assignment_view, name='staff_contract_assignment'),

    # アサイン情報詳細画面
    path('assignment/<int:assignment_pk>/detail/', views.contract_assignment_detail, name='contract_assignment_detail'),
    path('assignment/<int:assignment_pk>/employment-conditions-issue/', views.assignment_employment_conditions_issue, name='assignment_employment_conditions_issue'),
    path('assignment/<int:assignment_pk>/ai_check/', views.assignment_ai_check, name='assignment_ai_check'),
    path('view/assignment-haken-print/<int:pk>/', views.view_assignment_haken_print_pdf, name='view_assignment_haken_print_pdf'),
    path('download/assignment-haken-print/<int:pk>/', views.download_assignment_haken_print_pdf, name='download_assignment_haken_print_pdf'),
    path('assignment/<int:assignment_pk>/haken-print-history/', views.assignment_haken_print_history_list, name='assignment_haken_print_history_list'),
    
    # 契約アサイン延長確認
    path('assignment/<int:assignment_pk>/confirm/', views.contract_assignment_confirm_view, name='contract_assignment_confirm'),
    path('assignment/<int:assignment_pk>/confirm/delete/', views.contract_assignment_confirm_delete, name='contract_assignment_confirm_delete'),
    
    # 契約アサイン派遣雇用安定措置
    path('assignment/<int:assignment_pk>/haken/', views.contract_assignment_haken_view, name='contract_assignment_haken'),
    path('assignment/<int:assignment_pk>/haken/delete/', views.contract_assignment_haken_delete, name='contract_assignment_haken_delete'),
    
    # 就業条件明示書
    path('assignment/<int:assignment_pk>/employment-conditions/', views.assignment_employment_conditions_pdf, name='assignment_employment_conditions_pdf'),
    path('staff/<int:contract_pk>/assignment/<int:assignment_pk>/employment-conditions-issue/', views.staff_contract_assignment_employment_conditions_issue, name='staff_contract_assignment_employment_conditions_issue'),

    path('assign/confirm/client/', views.client_assignment_confirm, name='client_assignment_confirm'),
    path('assign/confirm/staff/', views.staff_assignment_confirm, name='staff_assignment_confirm'),
    path('assign/confirm/staff/from-create/', views.staff_assignment_confirm_from_create, name='staff_assignment_confirm_from_create'),
    path('assign/clear-session/', views.clear_assignment_session, name='clear_assignment_session'),
    path('assign/create/', views.create_contract_assignment_view, name='create_contract_assignment'),
    path('assign/<int:assignment_pk>/delete/', views.delete_contract_assignment, name='delete_contract_assignment'),
]