from django.contrib import admin
from .models import ApiCache


@admin.register(ApiCache)
class ApiCacheAdmin(admin.ModelAdmin):
    """
    ApiCacheモデルのDjango Admin設定
    """
    list_display = ('key', 'expires_at', 'created_at')
    search_fields = ('key',)
    list_filter = ('expires_at',)
    readonly_fields = ('key', 'response', 'expires_at', 'created_at')

    def has_add_permission(self, request):
        # 管理画面からの手動追加を禁止
        return False

    def has_delete_permission(self, request, obj=None):
        # 管理画面からの削除を許可（デバッグ用に）
        return True
