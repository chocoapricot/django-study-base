from django.urls import path
from . import views

app_name = 'company'

urlpatterns = [
    # 会社情報
    path('', views.company_detail, name='company_detail'),
    path('edit/', views.company_edit, name='company_edit'),
    
    # 部署管理
    path('departments/', views.department_list, name='department_list'),
    path('departments/create/', views.department_create, name='department_create'),
    path('departments/<int:pk>/', views.department_detail, name='department_detail'),
    path('departments/<int:pk>/edit/', views.department_edit, name='department_edit'),
    path('departments/<int:pk>/delete/', views.department_delete, name='department_delete'),
    
    # 変更履歴
    path('change-history/', views.change_history_list, name='change_history_list'),
]