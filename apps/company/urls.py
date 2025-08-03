from django.urls import path
from . import views

app_name = 'company'

urlpatterns = [
    path('', views.company_detail, name='company_detail'),
    path('edit/', views.company_edit, name='company_edit'),
]