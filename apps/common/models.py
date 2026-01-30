from django_currentuser.db.models import CurrentUserField
from django.db import models
from django.conf import settings

# Create your models here.
class MyModel(models.Model):
    """
    プロジェクト共通の抽象ベースモデル。
    バージョン管理、作成・更新日時、作成・更新者を自動で記録する。
    """
    from concurrency.fields import IntegerVersionField
    version = IntegerVersionField()
    created_at = models.DateTimeField('作成日時',auto_now_add=True)
    created_by = CurrentUserField(verbose_name="作成者", related_name="created_%(class)s_set")
    updated_at = models.DateTimeField('更新日時',auto_now=True)
    updated_by = CurrentUserField(verbose_name="更新者", related_name="updated_%(class)s_set")
    class Meta:
        abstract = True

class TenantManager(models.Manager):
    """
    テナントIDでフィルタリングを行うカスタムマネージャー。
    """
    def get_queryset(self):
        from apps.common.middleware import get_current_tenant_id, is_in_request

        # リクエスト外（テスト、シェル、コマンド等）ではフィルタリングしない
        if not is_in_request():
            return super().get_queryset()

        tenant_id = get_current_tenant_id()
        if tenant_id is None:
            # リクエスト中でテナントIDが設定されていない場合は空のクエリセットを返す
            # （ユーザーの要求：セッションにテナントがなければデータなしと同じ扱い）
            return super().get_queryset().none()
        return super().get_queryset().filter(tenant_id=tenant_id)

    def unfiltered(self):
        """
        テナントによるフィルタリングを行わずにクエリセットを取得する。
        """
        return super().get_queryset()

class MyTenantModel(MyModel):
    """
    テナントIDを持つ抽象ベースモデル。
    """
    tenant_id = models.PositiveIntegerField('テナントID', blank=True, null=True, db_index=True)

    class Meta:
        abstract = True

# 旧AppLogモデルは削除されました
# 新しいログシステムは apps.system.logs.models.AppLog を使用してください

# 旧log_view_detail関数は削除されました
# 新しいログシステムは apps.system.logs.utils.log_view_detail を使用してください
