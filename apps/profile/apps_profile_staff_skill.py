from django.db import models
from django.conf import settings
from apps.common.models import MyModel

class StaffSkill(MyModel):
    """プロフィール用スタッフ技能"""
    staff_profile = models.ForeignKey(
        'profile.StaffProfile',
        on_delete=models.CASCADE,
        related_name='skills',
        verbose_name='スタッフプロフィール'
    )
    skill = models.ForeignKey(
        'master.Skill',
        on_delete=models.CASCADE,
        verbose_name='技能'
    )
    acquired_date = models.DateField('習得日', blank=True, null=True)
    years_of_experience = models.IntegerField('経験年数', blank=True, null=True)
    memo = models.TextField('メモ', blank=True, null=True)

    class Meta:
        db_table = 'apps_profile_staff_skill'
        verbose_name = 'プロフィールスタッフ技能'
        verbose_name_plural = 'プロフィールスタッフ技能'
        unique_together = ['staff_profile', 'skill']
        ordering = ['-acquired_date']

    def __str__(self):
        return f"{self.staff_profile} - {self.skill}"
