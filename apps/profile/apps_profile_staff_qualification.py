from django.db import models
from django.conf import settings
from apps.common.models import MyModel

class StaffQualification(MyModel):
    """プロフィール用スタッフ資格"""
    staff_profile = models.ForeignKey(
        'profile.StaffProfile',
        on_delete=models.CASCADE,
        related_name='qualifications',
        verbose_name='スタッフプロフィール'
    )
    qualification = models.ForeignKey(
        'master.Qualification',
        on_delete=models.CASCADE,
        verbose_name='資格'
    )
    acquired_date = models.DateField('取得日', blank=True, null=True)
    expiry_date = models.DateField('有効期限', blank=True, null=True)
    certificate_number = models.CharField('証明書番号', max_length=100, blank=True, null=True)
    memo = models.TextField('メモ', blank=True, null=True)
    score = models.IntegerField('点数', blank=True, null=True, help_text='TOEICの点数など')

    class Meta:
        db_table = 'apps_profile_staff_qualification'
        verbose_name = 'プロフィールスタッフ資格'
        verbose_name_plural = 'プロフィールスタッフ資格'
        unique_together = ['staff_profile', 'qualification']
        ordering = ['-acquired_date']

    def __str__(self):
        return f"{self.staff_profile} - {self.qualification}"
