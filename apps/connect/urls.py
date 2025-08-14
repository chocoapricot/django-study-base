from django.urls import path
from . import views

app_name = 'connect'

urlpatterns = [
    path('', views.connect_index, name='index'),
    path('staff/', views.connect_staff_list, name='staff_list'),
    path('staff/<int:pk>/approve/', views.connect_staff_approve, name='staff_approve'),
    path('staff/<int:pk>/unapprove/', views.connect_staff_unapprove, name='staff_unapprove'),
    path('staff/create/', views.create_staff_connection, name='create_staff_connection'),
]