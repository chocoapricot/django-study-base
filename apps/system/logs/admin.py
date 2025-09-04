from django.contrib import admin
from .models import MailLog, AppLog, AccessLog

@admin.register(MailLog)
class MailLogAdmin(admin.ModelAdmin):
    """メール送信ログの管理画面"""
    
    list_display = [
        'id', 'mail_type', 'to_email', 'subject', 'status', 
        'sent_at', 'created_at'
    ]
    list_filter = [
        'mail_type', 'status', 'sent_at', 'created_at'
    ]
    search_fields = [
        'to_email', 'subject', 'from_email'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'created_by', 'updated_by'
    ]
    ordering = ['-created_at']
    
    fieldsets = (
        ('基本情報', {
            'fields': ('mail_type', 'status')
        }),
        ('送信者・受信者', {
            'fields': ('from_email', 'to_email', 'recipient_user')
        }),
        ('メール内容', {
            'fields': ('subject', 'body')
        }),
        ('送信情報', {
            'fields': ('sent_at', 'backend', 'message_id', 'error_message')
        }),
        ('システム情報', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """追加権限を無効化（ログは自動生成のため）"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """変更権限を無効化（ログは変更不可）"""
        return False


@admin.register(AccessLog)
class AccessLogAdmin(admin.ModelAdmin):
    """アクセスログの管理画面"""

    list_display = [
        'id', 'timestamp', 'user', 'url'
    ]
    list_filter = [
        'timestamp', 'user'
    ]
    search_fields = [
        'user__username', 'url'
    ]
    readonly_fields = [
        'timestamp', 'user', 'url'
    ]
    ordering = ['-timestamp']

    def has_add_permission(self, request):
        """追加権限を無効化（ログは自動生成のため）"""
        return False

    def has_change_permission(self, request, obj=None):
        """変更権限を無効化（ログは変更不可）"""
        return False


@admin.register(AppLog)
class AppLogAdmin(admin.ModelAdmin):
    """アプリケーション操作ログの管理画面"""
    
    list_display = [
        'id', 'timestamp', 'user', 'action', 'model_name', 
        'object_id', 'object_repr'
    ]
    list_filter = [
        'action', 'model_name', 'timestamp'
    ]
    search_fields = [
        'user__username', 'model_name', 'object_repr'
    ]
    readonly_fields = [
        'user', 'action', 'model_name', 'object_id', 
        'object_repr', 'version', 'timestamp'
    ]
    ordering = ['-timestamp']
    
    fieldsets = (
        ('基本情報', {
            'fields': ('user', 'action', 'timestamp')
        }),
        ('対象オブジェクト', {
            'fields': ('model_name', 'object_id', 'object_repr', 'version')
        }),
    )
    
    def has_add_permission(self, request):
        """追加権限を無効化（ログは自動生成のため）"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """変更権限を無効化（ログは変更不可）"""
        return False