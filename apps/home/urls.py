from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    path('', views.home, name='home'),
    path('start/', views.start_page, name='start_page'),
    path('information/list/', views.information_list, name='information_list'),
    path('information/<int:pk>/', views.information_detail, name='information_detail'),
    path('contact_schedule/summary/', views.contact_schedule_summary, name='contact_schedule_summary'),
    # セットアップ用エンドポイント
    path('setup/start/', views.setup_start, name='setup_start'),
    path('setup/process/<str:task_id>/', views.setup_process, name='setup_process'),
    path('setup/progress/<str:task_id>/', views.setup_progress, name='setup_progress'),

    # データ削除
    path('start/delete_data/', views.delete_application_data, name='delete_application_data'),
]
