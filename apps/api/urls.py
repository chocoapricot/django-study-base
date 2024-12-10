# urls.py
from django.urls import path
from .views import get_company_info, get_zipcode_info

urlpatterns = [
    path("get_company_info/", get_company_info, name="get_company_info"),
    path("get_zipcode_info/", get_zipcode_info, name="get_zipcode_info"),
]

