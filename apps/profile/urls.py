from django.urls import path
from . import views

app_name = 'profile'

urlpatterns = [
    path('', views.profile_detail, name='detail'),
    path('edit/', views.profile_edit, name='edit'),
    path('delete/', views.profile_delete, name='delete'),
    path('mynumber/', views.mynumber_detail, name='mynumber_detail'),
    path('mynumber/edit/', views.mynumber_edit, name='mynumber_edit'),
    path('mynumber/delete/', views.mynumber_delete, name='mynumber_delete'),
]