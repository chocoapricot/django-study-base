from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import Menu

# インポート、エクスポート用の定義
class MenuResource(resources.ModelResource):
    class Meta:
        model = Menu

# Register your models here.
@admin.register(Menu)
class MenuAdmin(ImportExportModelAdmin):
    list_display = ('name', 'url', 'disp_seq', 'active')
    resource_class = MenuResource

