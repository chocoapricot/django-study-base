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
]