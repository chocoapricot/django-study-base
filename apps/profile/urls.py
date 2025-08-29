from django.urls import path
from . import views, views_profile

app_name = 'profile'

urlpatterns = [
    path('', views.profile_index, name='index'),

    # スタッフ情報
    path('staff/', views.profile_detail, name='staff_detail'),
    path('staff/edit/', views.profile_edit, name='staff_edit'),
    path('staff/delete/', views.profile_delete, name='staff_delete'),

    # マイナンバー
    path('mynumber/', views.mynumber_detail, name='mynumber_detail'),
    path('mynumber/edit/', views.mynumber_edit, name='mynumber_edit'),
    path('mynumber/delete/', views.mynumber_delete, name='mynumber_delete'),

    # 外国籍情報
    path('international/', views.international_detail, name='international_detail'),
    path('international/edit/', views.international_edit, name='international_edit'),
    path('international/delete/', views.international_delete, name='international_delete'),

    # 銀行情報
    path('bank/', views.bank_detail, name='bank_detail'),
    path('bank/edit/', views.bank_edit, name='bank_edit'),
    path('bank/delete/', views.bank_delete, name='bank_delete'),

    # 障害者情報
    path('disability/', views.disability_detail, name='disability_detail'),
    path('disability/edit/', views.disability_edit, name='disability_edit'),
    path('disability/delete/', views.disability_delete, name='disability_delete'),

    # 連絡先情報
    path('contact/', views.contact_detail, name='contact_detail'),
    path('contact/edit/', views.contact_edit, name='contact_edit'),
    path('contact/delete/', views.contact_delete, name='contact_delete'),

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