from django.urls import path
from . import views

app_name = 'master'

urlpatterns = [
    # 資格管理
    path('qualification/', views.qualification_list, name='qualification_list'),
    path('qualification/create/', views.qualification_create, name='qualification_create'),
    path('qualification/<int:pk>/', views.qualification_detail, name='qualification_detail'),
    path('qualification/<int:pk>/update/', views.qualification_update, name='qualification_update'),
    path('qualification/<int:pk>/delete/', views.qualification_delete, name='qualification_delete'),
    
    # 技能管理
    path('skill/', views.skill_list, name='skill_list'),
    path('skill/create/', views.skill_create, name='skill_create'),
    path('skill/<int:pk>/', views.skill_detail, name='skill_detail'),
    path('skill/<int:pk>/update/', views.skill_update, name='skill_update'),
    path('skill/<int:pk>/delete/', views.skill_delete, name='skill_delete'),
]