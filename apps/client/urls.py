# urls.py
from django.urls import path
from .views import client_list, client_create, client_detail, client_update, client_delete #, get_company_info

urlpatterns = [
    path('', client_list, name='client_list'),
    path('client/create/', client_create, name='client_create'),
    path('client/detail/<int:pk>/', client_detail, name='client_detail'),
    path('client/update/<int:pk>/', client_update, name='client_update'),
    path('client/delete/<int:pk>/', client_delete, name='client_delete'),
    # path("get_company_info/", get_company_info, name="get_company_info"),
]

