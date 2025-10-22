from django.db import models
from ..common.models import MyModel
from .models_staff import Staff

class StaffPayroll(MyModel):
    """
    スタッフの給与関連情報を管理するモデル。
    """
    staff = models.OneToOneField(
        Staff,
        on_delete=models.CASCADE,
        related_name='payroll',
        verbose_name='スタッフ'
    )
    health_insurance_join_date = models.DateField('健康保険加入日', blank=True, null=True)
    welfare_pension_join_date = models.DateField('厚生年金加入日', blank=True, null=True)
    employment_insurance_join_date = models.DateField('雇用保険加入日', blank=True, null=True)

    class Meta:
        db_table = 'apps_staff_payroll'
        verbose_name = 'スタッフ給与'
        verbose_name_plural = 'スタッフ給与'

    def __str__(self):
        return f"{self.staff}の給与情報"
