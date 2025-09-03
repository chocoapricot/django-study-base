from django.urls import path
from . import views

app_name = 'logs'

urlpatterns = [
    path('mail/', views.mail_log_list, name='mail_log_list'),
    path('mail/export/', views.mail_log_export, name='mail_log_export'),
    path('mail/<int:pk>/', views.mail_log_detail, name='mail_log_detail'),
    path('app/', views.app_log_list, name='app_log_list'),
    path('app/export/', views.app_log_export, name='app_log_export'),
    path('url/', views.access_log_list, name='access_log_list'),
]