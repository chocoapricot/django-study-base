from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    path('', views.home, name='home'),
    path('start/', views.start_page, name='start_page'),
    path('information/list/', views.information_list, name='information_list'),
    path('information/<int:pk>/', views.information_detail, name='information_detail'),
    # セットアップ用エンドポイント
    path('setup/start/', views.setup_start, name='setup_start'),
    path('setup/process/<str:task_id>/', views.setup_process, name='setup_process'),
    path('setup/progress/<str:task_id>/', views.setup_progress, name='setup_progress'),
]
