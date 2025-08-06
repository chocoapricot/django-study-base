from django.contrib import admin
from .models import Qualification, Skill


@admin.register(Qualification)
class QualificationAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'issuing_organization', 'validity_period', 'is_active', 'display_order']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'issuing_organization']
    ordering = ['display_order', 'name']
    
    fieldsets = (
        ('基本情報', {
            'fields': ('name', 'category', 'description')
        }),
        ('詳細情報', {
            'fields': ('issuing_organization', 'validity_period')
        }),
        ('表示設定', {
            'fields': ('is_active', 'display_order')
        }),
    )


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'required_level', 'is_active', 'display_order']
    list_filter = ['category', 'required_level', 'is_active']
    search_fields = ['name', 'category']
    ordering = ['display_order', 'name']
    
    fieldsets = (
        ('基本情報', {
            'fields': ('name', 'category', 'description')
        }),
        ('レベル設定', {
            'fields': ('required_level',)
        }),
        ('表示設定', {
            'fields': ('is_active', 'display_order')
        }),
    )