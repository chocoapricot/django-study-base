from django.db import models


class ApiCache(models.Model):
    """
    外部APIのレスポンスをキャッシュするモデル
    """
    key = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="APIリクエストを一意に識別するキー"
    )
    response = models.JSONField(
        help_text="APIからのレスポンスボディ"
    )
    expires_at = models.DateTimeField(
        db_index=True,
        help_text="キャッシュの有効期限"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="レコード作成日時"
    )

    def __str__(self):
        return f"{self.key} - Expires at {self.expires_at}"

    class Meta:
        db_table = 'apps_system_api_cache'
        verbose_name = "APIキャッシュ"
        verbose_name_plural = "APIキャッシュ"
        ordering = ['-created_at']
