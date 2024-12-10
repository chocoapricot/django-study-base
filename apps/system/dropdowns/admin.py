from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import Dropdowns

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


