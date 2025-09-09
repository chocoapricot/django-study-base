from django.urls import path
from . import views

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

    # 契約パターン管理
    path('contract-pattern/', views.contract_pattern_list, name='contract_pattern_list'),
    path('contract-pattern/create/', views.contract_pattern_create, name='contract_pattern_create'),
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

    # メールテンプレート管理
    path('mail-template/', views.mail_template_list, name='mail_template_list'),
    path('mail-template/<int:pk>/', views.mail_template_detail, name='mail_template_detail'),
    path('mail-template/<int:pk>/update/', views.mail_template_update, name='mail_template_update'),
    path('mail-template/history/', views.mail_template_change_history_list, name='mail_template_change_history_list'),
]