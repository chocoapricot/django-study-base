from django.db import models
from django.conf import settings

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="ユーザー")
    title = models.CharField(max_length=255, verbose_name="タイトル")
    message = models.TextField(verbose_name="メッセージ")
    is_read = models.BooleanField(default=False, verbose_name="既読")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="作成日時")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "通知"
        verbose_name_plural = "通知"
        ordering = ['-created_at']
