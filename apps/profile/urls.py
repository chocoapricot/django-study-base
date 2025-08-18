from django.urls import path
from . import views, views_profile

app_name = 'profile'

urlpatterns = [
    path('', views.profile_detail, name='detail'),
    path('edit/', views.profile_edit, name='edit'),
    path('delete/', views.profile_delete, name='delete'),
    path('mynumber/', views.mynumber_detail, name='mynumber_detail'),
    path('mynumber/edit/', views.mynumber_edit, name='mynumber_edit'),
    path('mynumber/delete/', views.mynumber_delete, name='mynumber_delete'),

    # 資格
    path('qualification/', views_profile.profile_qualification_list, name='qualification_list'),
    path('qualification/create/', views_profile.profile_qualification_create, name='qualification_create'),
    path('qualification/<int:pk>/update/', views_profile.profile_qualification_update, name='qualification_update'),
    path('qualification/<int:pk>/delete/', views_profile.profile_qualification_delete, name='qualification_delete'),

    # 技能
    path('skill/', views_profile.profile_skill_list, name='skill_list'),
    path('skill/create/', views_profile.profile_skill_create, name='skill_create'),
    path('skill/<int:pk>/update/', views_profile.profile_skill_update, name='skill_update'),
    path('skill/<int:pk>/delete/', views_profile.profile_skill_delete, name='skill_delete'),
]