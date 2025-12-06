from django.urls import path
from . import views

app_name = 'system_notifications'

urlpatterns = [
    path('', views.notification_list, name='notification_list'),
    path('<int:pk>/', views.notification_detail, name='notification_detail'),
    path('count/', views.notification_count, name='notification_count'),
    path('mark-all-read/', views.mark_all_as_read, name='mark_all_as_read'),
]
