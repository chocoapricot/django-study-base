# urls.py
from django.urls import path
from .views import get_company_info, get_zipcode_info, search_banks, search_bank_branches, get_client_users

urlpatterns = [
    path("get_company_info/", get_company_info, name="get_company_info"),
    path("get_zipcode_info/", get_zipcode_info, name="get_zipcode_info"),
    path("search_banks/", search_banks, name="search_banks"),
    path("search_bank_branches/", search_bank_branches, name="search_bank_branches"),
    path("client/<int:client_id>/users/", get_client_users, name="get_client_users"),
]
