from django.db import models
from apps.common.models import MyModel


class ClientRegistStatus(MyModel):
    """
    クライアント登録状況マスタ
    """
    name = models.CharField('名称', max_length=100)
    display_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 'apps_master_client_regist_status'
        verbose_name = 'クライアント登録状況'
        verbose_name_plural = 'クライアント登録状況'
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['display_order']),
        ]

    def __str__(self):
        return self.name
