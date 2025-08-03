from django.contrib import admin
from .models import CompanyDepartment, Company

@admin.register(CompanyDepartment)
class CompanyDepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at', 'updated_at')
    search_fields = ('name', 'description')

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'corporate_number', 'phone_number', 'url', 'created_at', 'updated_at')
    search_fields = ('name', 'corporate_number')
