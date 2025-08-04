from django.contrib import admin
from .models import CompanyDepartment, Company

@admin.register(CompanyDepartment)
class CompanyDepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'department_code', 'accounting_code', 'display_order', 'created_at', 'updated_at')
    search_fields = ('name', 'department_code', 'accounting_code')
    list_editable = ('display_order',)
    ordering = ('display_order', 'name')

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'corporate_number', 'phone_number', 'url', 'created_at', 'updated_at')
    search_fields = ('name', 'corporate_number')
