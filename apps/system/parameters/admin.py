from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import Parameter

# インポート、エクスポート用の定義
class ParameterResource(resources.ModelResource):
    class Meta:
        model = Parameter

# Register your models here.
@admin.register(Parameter)
class ParameterAdmin(ImportExportModelAdmin):
    list_display = ('category', 'key', 'value', 'disp_seq', 'active')
    resource_class = ParameterResource

