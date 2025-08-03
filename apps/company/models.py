from django.db import models
from apps.common.models import MyModel

class CompanyDepartment(MyModel):
    name = models.CharField('部署名', max_length=100, unique=True)
    description = models.TextField('説明', blank=True, null=True)
    
    class Meta:
        db_table = 'apps_company_department'
        verbose_name = '部署'
        verbose_name_plural = '部署'

    def __str__(self):
        return self.name


class Company(MyModel):
    name = models.CharField('会社名', max_length=255, unique=True)
    # 会社情報として必要そうなフィールドを追加（例）
    corporate_number = models.CharField('法人番号', max_length=13, blank=True, null=True, unique=True)
    postal_code = models.CharField('郵便番号', max_length=7, blank=True, null=True)
    address = models.TextField('住所', blank=True, null=True)
    phone_number = models.CharField('電話番号', max_length=20, blank=True, null=True)
    url = models.URLField('URL', blank=True, null=True)
    
    class Meta:
        db_table = 'apps_company'
        verbose_name = '会社'
        verbose_name_plural = '会社'

    def __str__(self):
        return self.name
