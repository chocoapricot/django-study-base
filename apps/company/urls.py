from django.urls import path
from . import views

app_name = 'company'

urlpatterns = [
    # 会社情報
    path('', views.company_detail, name='company_detail'),
    path('edit/', views.company_edit, name='company_edit'),
    path('seal/upload/', views.company_seal_upload, name='company_seal_upload'),
    path('seal/delete/', views.company_seal_delete, name='company_seal_delete'),
    
    # 部署管理
    path('departments/create/', views.department_create, name='department_create'),
    path('departments/<int:pk>/', views.department_detail, name='department_detail'),
    path('departments/<int:pk>/edit/', views.department_edit, name='department_edit'),
    path('departments/<int:pk>/delete/', views.department_delete, name='department_delete'),
    
    # 変更履歴
    path('change-history/', views.change_history_list, name='change_history_list'),

    # 自社担当者
    path('users/create/', views.company_user_create, name='company_user_create'),
    path('users/<int:pk>/', views.company_user_detail, name='company_user_detail'),
    path('users/<int:pk>/edit/', views.company_user_edit, name='company_user_edit'),
    path('users/<int:pk>/delete/', views.company_user_delete, name='company_user_delete'),
]