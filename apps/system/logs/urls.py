from django.urls import path
from . import views

app_name = 'logs'

urlpatterns = [
    path('mail/', views.mail_log_list, name='mail_log_list'),
    path('mail/<int:pk>/', views.mail_log_detail, name='mail_log_detail'),
]