from django.contrib import admin
from .models import Qualification, Skill


@admin.register(Qualification)
class QualificationAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_active', 'display_order']
    list_filter = ['category', 'is_active']
    search_fields = ['name']
    ordering = ['display_order', 'name']
    
    fieldsets = (
        ('基本情報', {
            'fields': ('name', 'category', 'description')
        }),
        ('表示設定', {
            'fields': ('is_active', 'display_order')
        }),
    )


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ['name', 'level_display_name', 'parent', 'is_active', 'display_order']
    list_filter = ['level', 'parent', 'is_active']
    search_fields = ['name']
    ordering = ['level', 'display_order', 'name']
    
    fieldsets = (
        ('基本情報', {
            'fields': ('name', 'level', 'parent', 'description')
        }),
        ('表示設定', {
            'fields': ('is_active', 'display_order')
        }),
    )
    
    def get_queryset(self, request):
        """階層順で表示"""
        return super().get_queryset(request).select_related('parent')