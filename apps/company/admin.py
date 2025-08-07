from django.contrib import admin
from .models import CompanyDepartment, Company

# @admin.register(CompanyDepartment)
# class CompanyDepartmentAdmin(admin.ModelAdmin):
#     list_display = ('name', 'department_code', 'accounting_code', 'valid_from', 'valid_to', 'is_valid_now', 'display_order', 'created_at', 'updated_at')
#     search_fields = ('name', 'department_code', 'accounting_code')
#     list_editable = ('display_order',)
#     list_filter = ('valid_from', 'valid_to', 'created_at')
#     ordering = ('display_order', 'name')
    
#     def is_valid_now(self, obj):
#         """現在有効かどうかを表示"""
#         return obj.is_valid_on_date()
#     is_valid_now.boolean = True
#     is_valid_now.short_description = '現在有効'

# @admin.register(Company)
# class CompanyAdmin(admin.ModelAdmin):
#     list_display = ('name', 'corporate_number', 'phone_number', 'url', 'created_at', 'updated_at')
#     search_fields = ('name', 'corporate_number')
