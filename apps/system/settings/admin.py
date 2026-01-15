from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from django.utils.html import format_html
from .models import Dropdowns, Parameter, Menu
from .forms import MenuForm

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
    form = MenuForm
    list_display = ('name', 'url', 'icon', 'icon_style_display' ,'level', 'disp_seq', 'required_permission', 'exact_match', 'active')
    list_filter = ('level', 'active')
    search_fields = ('name', 'url', 'icon')
    resource_class = MenuResource

    def icon_style_display(self, obj):
        if not obj.icon:
            return ""
        return format_html(
            '<i class="bi {}" style="font-size: 1.2rem; {}"></i> <span style="margin-left: 8px;">{}</span>',
            obj.icon, obj.icon_style, obj.icon_style
        )
    icon_style_display.short_description = 'アイコンプレビュー'

    class Media:
        css = {
            'all': ('https://cdnjs.cloudflare.com/ajax/libs/bootstrap-icons/1.11.0/font/bootstrap-icons.min.css',)
        }