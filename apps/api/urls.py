# urls.py
from django.urls import path
from .views import (
    get_company_info, get_zipcode_info,
    search_banks, search_bank_branches,
    get_client_users, get_client_haken_offices, get_client_haken_units,
    get_client_department_detail
)

urlpatterns = [
    path("get_company_info/", get_company_info, name="get_company_info"),
    path("get_zipcode_info/", get_zipcode_info, name="get_zipcode_info"),
    path("search_banks/", search_banks, name="search_banks"),
    path("search_bank_branches/", search_bank_branches, name="search_bank_branches"),
    path("client/<int:client_id>/users/", get_client_users, name="get_client_users"),
    path("client/<int:client_id>/haken_offices/", get_client_haken_offices, name="get_client_haken_offices"),
    path("client/<int:client_id>/haken_units/", get_client_haken_units, name="get_client_haken_units"),
    path("client_department/<int:department_id>/", get_client_department_detail, name="get_client_department_detail"),
]
