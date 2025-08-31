from django.db import models
from apps.common.models import MyModel

class InformationFromCompany(MyModel):
    """
    会社からのお知らせを管理するモデル
    """
    TARGET_CHOICES = [
        ('company', '会社'),
        ('staff', 'スタッフ'),
        ('client', 'クライアント'),
    ]

    target = models.CharField(
        '対象',
        max_length=10,
        choices=TARGET_CHOICES,
        default='company',
    )
    title = models.CharField('件名', max_length=200)
    content = models.TextField('内容')
    start_date = models.DateField('開始日', null=True, blank=True)
    end_date = models.DateField('終了日', null=True, blank=True)
    corporate_number = models.CharField('法人番号', max_length=13, blank=True, null=True)

    class Meta:
        ordering = ['-start_date']
        db_table = 'apps_information_from_company'
        verbose_name = 'お知らせ'
        verbose_name_plural = 'お知らせ'

    def __str__(self):
        return self.title
