from django.urls import path
from . import views

app_name = 'contract'

urlpatterns = [
    # 契約管理トップ
    path('', views.contract_index, name='contract_index'),
    
    # クライアント契約
    path('client/', views.client_contract_list, name='client_contract_list'),
    path('client/create/', views.client_contract_create, name='client_contract_create'),
    path('client/<int:pk>/', views.client_contract_detail, name='client_contract_detail'),
    path('client/<int:pk>/update/', views.client_contract_update, name='client_contract_update'),
    path('client/<int:pk>/delete/', views.client_contract_delete, name='client_contract_delete'),
    path('client/<int:pk>/pdf/', views.client_contract_pdf, name='client_contract_pdf'),
    path('client/<int:pk>/change_history/', views.client_contract_change_history_list, name='client_contract_change_history_list'),
    path('client/print/<int:pk>/download/', views.download_client_contract_pdf, name='download_client_contract_pdf'),
    path('client/confirm/', views.client_contract_confirm_list, name='client_contract_confirm_list'),
    path('client/<int:pk>/request_approval/', views.client_contract_request_approval, name='client_contract_request_approval'),
    path('client/<int:pk>/approve/', views.client_contract_approve, name='client_contract_approve'),
    path('client/<int:pk>/issue/', views.client_contract_issue, name='client_contract_issue'),
    path('client/<int:pk>/issue_quotation/', views.issue_quotation, name='issue_quotation'),
    path('client/<int:pk>/confirm/', views.client_contract_confirm, name='client_contract_confirm'),
    path('client/export/', views.client_contract_export, name='client_contract_export'),
    path('client/<int:pk>/draft_pdf/', views.client_contract_draft_pdf, name='client_contract_draft_pdf'),
    path('client/<int:pk>/draft_quotation/', views.client_contract_draft_quotation, name='client_contract_draft_quotation'),
    
    # スタッフ契約
    path('staff/', views.staff_contract_list, name='staff_contract_list'),
    path('staff/create/', views.staff_contract_create, name='staff_contract_create'),
    path('staff/confirm/', views.staff_contract_confirm_list, name='staff_contract_confirm_list'),
    path('staff/<int:pk>/', views.staff_contract_detail, name='staff_contract_detail'),
    path('staff/<int:pk>/update/', views.staff_contract_update, name='staff_contract_update'),
    path('staff/<int:pk>/delete/', views.staff_contract_delete, name='staff_contract_delete'),
    path('staff/<int:pk>/pdf/', views.staff_contract_pdf, name='staff_contract_pdf'),
    path('staff/<int:pk>/change_history/', views.staff_contract_change_history_list, name='staff_contract_change_history_list'),
    path('staff/print/<int:pk>/download/', views.download_staff_contract_pdf, name='download_staff_contract_pdf'),
    path('staff/<int:pk>/approve/', views.staff_contract_approve, name='staff_contract_approve'),
    path('staff/<int:pk>/issue/', views.staff_contract_issue, name='staff_contract_issue'),
    path('staff/export/', views.staff_contract_export, name='staff_contract_export'),
    path('staff/<int:pk>/draft_pdf/', views.staff_contract_draft_pdf, name='staff_contract_draft_pdf'),
    
    # 選択用画面
    path('client-select/', views.client_select, name='client_select'),
    path('staff-select/', views.staff_select, name='staff_select'),

]