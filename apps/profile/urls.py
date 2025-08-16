from django.urls import path
from . import views

app_name = 'profile'

urlpatterns = [
    path('', views.profile_detail, name='detail'),
    path('edit/', views.profile_edit, name='edit'),
    path('delete/', views.profile_delete, name='delete'),
]