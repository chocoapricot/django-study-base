from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import Dropdowns, Parameter, Menu

# インポート、エクスポート用の定義
class DropdownsResource(resources.ModelResource):
    class Meta:
        model = Dropdowns

# Register your models here.
@admin.register(Dropdowns)
class DropdownsAdmin(ImportExportModelAdmin):
    list_display = ('category', 'name', 'value', 'disp_seq', 'active')
    list_filter = ('category', )
    resource_class = DropdownsResource


# インポート、エクスポート用の定義
class ParameterResource(resources.ModelResource):
    class Meta:
        model = Parameter

@admin.register(Parameter)
class ParameterAdmin(ImportExportModelAdmin):
    list_display = ('category', 'key', 'value', 'disp_seq', 'active')
    resource_class = ParameterResource


# インポート、エクスポート用の定義
class MenuResource(resources.ModelResource):
    class Meta:
        model = Menu

@admin.register(Menu)
class MenuAdmin(ImportExportModelAdmin):
    list_display = ('name', 'url' ,'level', 'disp_seq', 'required_permission', 'exact_match', 'active')
    resource_class = MenuResource