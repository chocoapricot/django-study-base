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
    
    # スタッフ契約
    path('staff/', views.staff_contract_list, name='staff_contract_list'),
    path('staff/create/', views.staff_contract_create, name='staff_contract_create'),
    path('staff/<int:pk>/', views.staff_contract_detail, name='staff_contract_detail'),
    path('staff/<int:pk>/update/', views.staff_contract_update, name='staff_contract_update'),
    path('staff/<int:pk>/delete/', views.staff_contract_delete, name='staff_contract_delete'),
    path('staff/<int:pk>/pdf/', views.staff_contract_pdf, name='staff_contract_pdf'),
    path('staff/<int:pk>/change_history/', views.staff_contract_change_history_list, name='staff_contract_change_history_list'),
    
    # 選択用画面
    path('client-select/', views.client_select, name='client_select'),
    path('staff-select/', views.staff_select, name='staff_select'),
]