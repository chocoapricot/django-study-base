from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    path('', views.home, name='home'),
    path('information/list/', views.information_list, name='information_list'),
    path('information/<int:pk>/', views.information_detail, name='information_detail'),
]
