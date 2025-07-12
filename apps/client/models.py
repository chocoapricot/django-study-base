from django.db import models

from ..common.models import MyModel

class Client(MyModel):
    corporate_number=models.CharField('法人番号',max_length=13, unique=True, blank=True, null=True)
    name = models.TextField('会社名')
    name_furigana = models.TextField('会社名カナ')
    postal_code = models.CharField('郵便番号',blank=True, null=True,max_length=7)
    address_kana = models.TextField('住所カナ',blank=True, null=True)
    address = models.TextField('住所',blank=True, null=True)
    # phone = models.TextField('電話番号',blank=True, null=True)
    # email = models.CharField('E-MAIL',max_length=255, blank=True, null=True)
    url = models.TextField('URL',blank=True, null=True)
    memo = models.TextField('メモ',blank=True, null=True)
    regist_form_client = models.IntegerField('登録区分',blank=True, null=True)

    class Meta:
        db_table = 'apps_client'  # 既存のテーブル名を指定
        verbose_name = 'クライアント'

    def __str__(self):
        return self.name


# クライアント連絡履歴モデル
class ClientContacted(MyModel):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='contacted_histories', verbose_name='クライアント')
    contacted_at = models.DateTimeField('連絡日時', auto_now_add=True)
    content = models.CharField('対応内容', max_length=255, blank=False, null=False)
    detail = models.TextField('対応詳細', blank=True, null=True)
    contact_type = models.IntegerField('連絡種別', blank=True, null=True)

    class Meta:
        db_table = 'apps_client_contacted'
        verbose_name = 'クライアント連絡履歴'
        verbose_name_plural = 'クライアント連絡履歴'
        ordering = ['-contacted_at']

    def __str__(self):
        return f"{self.client} {self.contacted_at:%Y-%m-%d %H:%M} {self.content[:20]}"