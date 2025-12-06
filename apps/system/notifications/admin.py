from django.contrib import admin
from .models import Notification
from import_export.admin import ImportExportModelAdmin


@admin.register(Notification)
class NotificationAdmin(ImportExportModelAdmin):
    """通知の管理画面"""
    
    list_display = [
        'id',
        'user',
        'title',
        'notification_type',
        'is_read',
        'created_at',
        'read_at',
    ]
    
    list_filter = [
        'is_read',
        'notification_type',
        'created_at',
    ]
    
    search_fields = [
        'user__username',
        'user__email',
        'title',
        'message',
    ]
    
    readonly_fields = [
        'read_at',
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('基本情報', {
            'fields': ('user', 'title', 'message', 'notification_type')
        }),
        ('リンク情報', {
            'fields': ('link_url',)
        }),
        ('ステータス', {
            'fields': ('is_read', 'read_at')
        }),
        ('タイムスタンプ', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        """関連するユーザー情報を事前に取得してクエリを最適化"""
        qs = super().get_queryset(request)
        return qs.select_related('user')
