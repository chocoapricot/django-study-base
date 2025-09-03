from django.urls import path
from . import views

app_name = 'connect'

urlpatterns = [
    path('', views.connect_index, name='index'),
    path('staff/', views.connect_staff_list, name='staff_list'),
    path('staff/<int:pk>/approve/', views.connect_staff_approve, name='staff_approve'),
    path('staff/<int:pk>/unapprove/', views.connect_staff_unapprove, name='staff_unapprove'),
    path('staff/<int:pk>/agree/', views.staff_agree, name='staff_agree'),
    path('client/', views.connect_client_list, name='client_list'),
    path('client/<int:pk>/approve/', views.connect_client_approve, name='client_approve'),
    path('client/<int:pk>/unapprove/', views.connect_client_unapprove, name='client_unapprove'),
]