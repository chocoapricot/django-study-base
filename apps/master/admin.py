from django.contrib import admin
from .models import Qualification, Skill, BillPayment, BillBank
from .models_phrase import PhraseTemplate, PhraseTemplateTitle
from .models_other import DefaultValue, UserParameter

# 資格マスタ、技能マスタ、支払いサイト、会社銀行は
# Webインターフェースで管理するため、admin.pyには登録しない


@admin.register(PhraseTemplate)
class PhraseTemplateAdmin(admin.ModelAdmin):
    list_display = ('get_title_name', 'content', 'is_active', 'display_order', 'created_at')
    list_filter = ('title', 'is_active', 'created_at')
    search_fields = ('content',)
    ordering = ('title__display_order', 'display_order', 'id')
    list_per_page = 20
    
    fieldsets = (
        (None, {
            'fields': ('title', 'content', 'is_active', 'display_order')
        }),
        ('システム情報', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    
    def get_title_name(self, obj):
        return obj.title.name
    get_title_name.short_description = '文言タイトル'


@admin.register(PhraseTemplateTitle)
class PhraseTemplateTitleAdmin(admin.ModelAdmin):
    list_display = ('key', 'name', 'get_description_short', 'format_type', 'is_active', 'display_order', 'created_at')
    list_filter = ('format_type', 'is_active', 'created_at')
    search_fields = ('key', 'name', 'description')
    ordering = ('display_order', 'id')
    list_per_page = 20
    
    fieldsets = (
        (None, {
            'fields': ('key', 'name', 'description', 'format_type', 'is_active', 'display_order')
        }),
        ('システム情報', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    
    def get_description_short(self, obj):
        if obj.description:
            return obj.description[:50] + ('...' if len(obj.description) > 50 else '')
        return '-'
    get_description_short.short_description = '補足'


@admin.register(DefaultValue)
class DefaultValueAdmin(admin.ModelAdmin):
    list_display = ('key', 'target_item', 'format', 'get_value_short', 'display_order', 'created_at')
    list_filter = ('format', 'created_at')
    search_fields = ('key', 'target_item', 'value')
    ordering = ('display_order', 'target_item')
    list_per_page = 20
    
    fieldsets = (
        (None, {
            'fields': ('key', 'target_item', 'format', 'value', 'display_order')
        }),
        ('システム情報', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    
    def get_value_short(self, obj):
        if obj.value:
            return obj.value[:100] + ('...' if len(obj.value) > 100 else '')
        return '-'
    get_value_short.short_description = '値'


@admin.register(UserParameter)
class UserParameterAdmin(admin.ModelAdmin):
    list_display = ('key', 'target_item', 'format', 'get_value_short', 'display_order', 'created_at')
    list_filter = ('format', 'created_at')
    search_fields = ('key', 'target_item', 'value')
    ordering = ('display_order', 'target_item')
    list_per_page = 20
    
    fieldsets = (
        (None, {
            'fields': ('key', 'target_item', 'format', 'value', 'display_order')
        }),
        ('システム情報', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')
    
    def get_value_short(self, obj):
        if obj.value:
            return obj.value[:100] + ('...' if len(obj.value) > 100 else '')
        return '-'
    get_value_short.short_description = '値'