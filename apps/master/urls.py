from django.urls import path
from . import views
from . import views_kintai

app_name = 'master'

urlpatterns = [
    # マスタ一覧
    path('', views.master_index_list, name='master_index_list'),
    
    # 資格管理
    path('qualification/', views.qualification_list, name='qualification_list'),
    path('qualification/category/create/', views.qualification_category_create, name='qualification_category_create'),
    path('qualification/create/', views.qualification_create, name='qualification_create'),
    path('qualification/<int:pk>/', views.qualification_detail, name='qualification_detail'),
    path('qualification/<int:pk>/update/', views.qualification_update, name='qualification_update'),
    path('qualification/<int:pk>/delete/', views.qualification_delete, name='qualification_delete'),
    
    # 技能管理
    path('skill/', views.skill_list, name='skill_list'),
    path('skill/category/create/', views.skill_category_create, name='skill_category_create'),
    path('skill/create/', views.skill_create, name='skill_create'),
    path('skill/<int:pk>/', views.skill_detail, name='skill_detail'),
    path('skill/<int:pk>/update/', views.skill_update, name='skill_update'),
    path('skill/<int:pk>/delete/', views.skill_delete, name='skill_delete'),
    
    # 変更履歴
    path('qualification/history/', views.qualification_change_history_list, name='qualification_change_history_list'),
    path('skill/history/', views.skill_change_history_list, name='skill_change_history_list'),
    
    # 職種管理
    path('job-category/', views.job_category_list, name='job_category_list'),
    path('job-category/create/', views.job_category_create, name='job_category_create'),
    path('job-category/<int:pk>/update/', views.job_category_update, name='job_category_update'),
    path('job-category/<int:pk>/delete/', views.job_category_delete, name='job_category_delete'),
    path('job-category/history/', views.job_category_change_history_list, name='job_category_change_history_list'),

    # 支払いサイト管理
    path('bill-payment/', views.bill_payment_list, name='bill_payment_list'),
    path('bill-payment/create/', views.bill_payment_create, name='bill_payment_create'),
    path('bill-payment/<int:pk>/update/', views.bill_payment_update, name='bill_payment_update'),
    path('bill-payment/<int:pk>/delete/', views.bill_payment_delete, name='bill_payment_delete'),
    path('bill-payment/history/', views.bill_payment_change_history_list, name='bill_payment_change_history_list'),
    
    # 会社銀行管理
    path('bill-bank/', views.bill_bank_list, name='bill_bank_list'),
    path('bill-bank/create/', views.bill_bank_create, name='bill_bank_create'),
    path('bill-bank/<int:pk>/update/', views.bill_bank_update, name='bill_bank_update'),
    path('bill-bank/<int:pk>/delete/', views.bill_bank_delete, name='bill_bank_delete'),
    path('bill-bank/history/', views.bill_bank_change_history_list, name='bill_bank_change_history_list'),
    
    # 銀行管理（作成・編集・削除のみ）
    path('bank/create/', views.bank_create, name='bank_create'),
    path('bank/<int:pk>/update/', views.bank_update, name='bank_update'),
    path('bank/<int:pk>/delete/', views.bank_delete, name='bank_delete'),
    
    # 銀行支店管理（作成・編集・削除のみ）
    path('bank-branch/create/', views.bank_branch_create, name='bank_branch_create'),
    path('bank-branch/<int:pk>/update/', views.bank_branch_update, name='bank_branch_update'),
    path('bank-branch/<int:pk>/delete/', views.bank_branch_delete, name='bank_branch_delete'),
    
    # 銀行・銀行支店統合管理
    path('bank-management/', views.bank_management, name='bank_management'),
    path('bank-management/history/', views.bank_management_change_history_list, name='bank_management_change_history_list'),
    path('bank/import/', views.bank_import, name='bank_import'),
    path('bank/import/upload/', views.bank_import_upload, name='bank_import_upload'),
    path('bank/import/process/<str:task_id>/', views.bank_import_process, name='bank_import_process'),
    path('bank/import/progress/<str:task_id>/', views.bank_import_progress, name='bank_import_progress'),

    # お知らせ管理
    path('information/', views.information_list, name='information_list'),
    path('information/create/', views.information_create, name='information_create'),
    path('information/<int:pk>/', views.information_detail, name='information_detail'),
    path('information/<int:pk>/update/', views.information_update, name='information_update'),
    path('information/<int:pk>/delete/', views.information_delete, name='information_delete'),
    path('information/history/', views.information_all_change_history_list, name='information_all_change_history_list'),

    # スタッフ同意文言管理
    path('staff-agreement/', views.staff_agreement_list, name='staff_agreement_list'),
    path('staff-agreement/create/', views.staff_agreement_create, name='staff_agreement_create'),
    path('staff-agreement/<int:pk>/', views.staff_agreement_detail, name='staff_agreement_detail'),
    path('staff-agreement/<int:pk>/export-agreed-staff/', views.agreed_staff_export, name='agreed_staff_export'),
    path('staff-agreement/<int:pk>/update/', views.staff_agreement_update, name='staff_agreement_update'),
    path('staff-agreement/<int:pk>/delete/', views.staff_agreement_delete, name='staff_agreement_delete'),
    path('staff-agreement/history/', views.staff_agreement_change_history_list, name='staff_agreement_change_history_list'),

    # 契約書パターン管理
    path('contract-pattern/', views.contract_pattern_list, name='contract_pattern_list'),
    path('contract-pattern/create/', views.contract_pattern_create, name='contract_pattern_create'),
    path('contract-pattern/<int:pk>/copy/', views.contract_pattern_copy, name='contract_pattern_copy'),
    path('contract-pattern/<int:pk>/detail/', views.contract_pattern_detail, name='contract_pattern_detail'),
    path('contract-pattern/<int:pk>/update/', views.contract_pattern_update, name='contract_pattern_update'),
    path('contract-pattern/<int:pk>/delete/', views.contract_pattern_delete, name='contract_pattern_delete'),
    path('contract-pattern/history/', views.contract_pattern_change_history_list, name='contract_pattern_change_history_list'),
    path('contract-pattern/<int:pattern_pk>/term/create/', views.contract_term_create, name='contract_term_create'),
    path('contract-term/<int:pk>/update/', views.contract_term_update, name='contract_term_update'),
    path('contract-term/<int:pk>/delete/', views.contract_term_delete, name='contract_term_delete'),

    # 最低賃金管理
    path('minimum-pay/', views.minimum_pay_list, name='minimum_pay_list'),
    path('minimum-pay/create/', views.minimum_pay_create, name='minimum_pay_create'),
    path('minimum-pay/<int:pk>/update/', views.minimum_pay_update, name='minimum_pay_update'),
    path('minimum-pay/<int:pk>/delete/', views.minimum_pay_delete, name='minimum_pay_delete'),
    path('minimum-pay/history/', views.minimum_pay_change_history_list, name='minimum_pay_change_history_list'),

    # 雇用形態管理
    path('employment-type/', views.employment_type_list, name='employment_type_list'),
    path('employment-type/create/', views.employment_type_create, name='employment_type_create'),
    path('employment-type/<int:pk>/update/', views.employment_type_update, name='employment_type_update'),
    path('employment-type/<int:pk>/delete/', views.employment_type_delete, name='employment_type_delete'),
    path('employment-type/history/', views.employment_type_change_history_list, name='employment_type_change_history_list'),

    # 設定値マスタ
    path('user-parameter/', views.user_parameter_list, name='user_parameter_list'),
    path('user-parameter/<str:pk>/update/', views.user_parameter_update, name='user_parameter_update'),
    path('user-parameter/history/', views.user_parameter_change_history_list, name='user_parameter_change_history_list'),

    # 初期値マスタ
    path('default-value/', views.default_value_list, name='default_value_list'),
    path('default-value/<str:pk>/update/', views.default_value_update, name='default_value_update'),
    path('default-value/history/', views.default_value_change_history_list, name='default_value_change_history_list'),

    # メールテンプレート管理
    path('mail-template/', views.mail_template_list, name='mail_template_list'),
    path('mail-template/<int:pk>/', views.mail_template_detail, name='mail_template_detail'),
    path('mail-template/<int:pk>/update/', views.mail_template_update, name='mail_template_update'),
    path('mail-template/history/', views.mail_template_change_history_list, name='mail_template_change_history_list'),

    # スタッフ登録状況管理
    path('staff-regist-status/', views.staff_regist_status_list, name='staff_regist_status_list'),
    path('staff-regist-status/create/', views.staff_regist_status_create, name='staff_regist_status_create'),
    path('staff-regist-status/<int:pk>/update/', views.staff_regist_status_update, name='staff_regist_status_update'),
    path('staff-regist-status/<int:pk>/delete/', views.staff_regist_status_delete, name='staff_regist_status_delete'),
    path('staff-regist-status/history/', views.staff_regist_status_change_history_list, name='staff_regist_status_change_history_list'),

    # クライアント登録状況管理
    path('client-regist-status/', views.client_regist_status_list, name='client_regist_status_list'),
    path('client-regist-status/create/', views.client_regist_status_create, name='client_regist_status_create'),
    path('client-regist-status/<int:pk>/update/', views.client_regist_status_update, name='client_regist_status_update'),
    path('client-regist-status/<int:pk>/delete/', views.client_regist_status_delete, name='client_regist_status_delete'),
    path('client-regist-status/history/', views.client_regist_status_change_history_list, name='client_regist_status_change_history_list'),

    # 汎用文言テンプレート管理
    path('phrase-template/', views.phrase_template_list, name='phrase_template_list'),
    path('phrase-template/create/', views.phrase_template_create, name='phrase_template_create'),
    path('phrase-template/<int:pk>/update/', views.phrase_template_update, name='phrase_template_update'),
    path('phrase-template/<int:pk>/delete/', views.phrase_template_delete, name='phrase_template_delete'),
    path('phrase-template/history/', views.phrase_template_change_history_list, name='phrase_template_change_history_list'),

    # 就業時間パターン管理
    path('worktime-pattern/', views.worktime_pattern_list, name='worktime_pattern_list'),
    path('worktime-pattern/create/', views.worktime_pattern_create, name='worktime_pattern_create'),
    path('worktime-pattern/<int:pk>/detail/', views.worktime_pattern_detail, name='worktime_pattern_detail'),
    path('worktime-pattern/<int:pk>/update/', views.worktime_pattern_update, name='worktime_pattern_update'),
    path('worktime-pattern/<int:pk>/delete/', views.worktime_pattern_delete, name='worktime_pattern_delete'),
    path('worktime-pattern/history/', views.worktime_pattern_change_history_list, name='worktime_pattern_change_history_list'),
    path('worktime-pattern/select-modal/', views.worktime_pattern_select_modal, name='worktime_pattern_select_modal'),
    path('worktime-pattern/<int:pk>/json/', views.worktime_pattern_detail_json, name='worktime_pattern_detail_json'),
    # 勤務時間管理
    path('worktime-pattern/<int:pattern_pk>/work/create/', views.worktime_pattern_work_create, name='worktime_pattern_work_create'),
    path('worktime-pattern-work/<int:pk>/update/', views.worktime_pattern_work_update, name='worktime_pattern_work_update'),
    path('worktime-pattern-work/<int:pk>/delete/', views.worktime_pattern_work_delete, name='worktime_pattern_work_delete'),
    # 休憩時間管理
    path('worktime-pattern-work/<int:work_pk>/break/create/', views.worktime_pattern_break_create, name='worktime_pattern_break_create'),
    path('worktime-pattern-break/<int:pk>/update/', views.worktime_pattern_break_update, name='worktime_pattern_break_update'),
    path('worktime-pattern-break/<int:pk>/delete/', views.worktime_pattern_break_delete, name='worktime_pattern_break_delete'),

    # 時間外算出パターン管理
    path('overtime-pattern/', views.overtime_pattern_list, name='overtime_pattern_list'),
    path('overtime-pattern/create/', views.overtime_pattern_create, name='overtime_pattern_create'),
    path('overtime-pattern/<int:pk>/update/', views.overtime_pattern_update, name='overtime_pattern_update'),
    path('overtime-pattern/<int:pk>/delete/', views.overtime_pattern_delete, name='overtime_pattern_delete'),
    path('overtime-pattern/history/', views.overtime_pattern_change_history_list, name='overtime_pattern_change_history_list'),
    path('overtime-pattern/select-modal/', views.overtime_pattern_select_modal, name='overtime_pattern_select_modal'),

    # 勤怠打刻マスタ管理
    path('time-punch/', views.time_punch_list, name='time_punch_list'),
    path('time-punch/create/', views.time_punch_create, name='time_punch_create'),
    path('time-punch/<int:pk>/edit/', views.time_punch_edit, name='time_punch_edit'),
    path('time-punch/<int:pk>/delete-confirm/', views.time_punch_delete_confirm, name='time_punch_delete_confirm'),
    path('time-punch/<int:pk>/delete/', views.time_punch_delete, name='time_punch_delete'),
    path('time-punch/history/', views.time_punch_change_history_list, name='time_punch_change_history_list'),
    path('time-punch/modal/', views_kintai.time_punch_select_modal, name='time_punch_select_modal'),
]

