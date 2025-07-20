
from django_currentuser.db.models import CurrentUserField
from django.db import models
from django.conf import settings

# Create your models here.
class MyModel(models.Model):
    created_at = models.DateTimeField('作成日時',auto_now_add=True)
    created_by = CurrentUserField(verbose_name="作成者", related_name="created_%(class)s_set")
    updated_at = models.DateTimeField('更新日時',auto_now=True)
    updated_by = CurrentUserField(verbose_name="更新者", related_name="updated_%(class)s_set")
    # version = models.IntegerField(default=0)  # バージョン番号
    class Meta:
        abstract = True

# アプリケーション操作ログ
class AppLog(models.Model):
    ACTION_CHOICES = [
        ('create', '作成'),
        ('update', '編集'),
        ('delete', '削除'),
        ('login', 'ログイン'),
        ('logout', 'ログアウト'),
        ('view', '閲覧'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    object_repr = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.timestamp} {self.user} {self.action} {self.model_name} {self.object_repr}"

# 詳細画面アクセス用のログ記録関数
def log_view_detail(user, instance):
    AppLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action='view',
        model_name=instance.__class__.__name__,
        object_id=str(getattr(instance, 'pk', '')),
        object_repr=f"{instance} の詳細画面を閲覧"
    )


