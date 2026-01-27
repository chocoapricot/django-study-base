from django.db import models
from ..common.models import MyTenantModel
from .models_staff import Staff

class StaffPayroll(MyTenantModel):
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
    health_insurance_non_enrollment_reason = models.TextField(
        '健康保険非加入理由',
        blank=True,
        null=True,
        help_text='健康保険に加入しない場合の理由を入力してください'
    )
    welfare_pension_join_date = models.DateField('厚生年金加入日', blank=True, null=True)
    pension_insurance_non_enrollment_reason = models.TextField(
        '厚生年金非加入理由',
        blank=True,
        null=True,
        help_text='厚生年金に加入しない場合の理由を入力してください'
    )
    employment_insurance_join_date = models.DateField('雇用保険加入日', blank=True, null=True)
    employment_insurance_non_enrollment_reason = models.TextField(
        '雇用保険非加入理由',
        blank=True,
        null=True,
        help_text='雇用保険に加入しない場合の理由を入力してください'
    )

    class Meta:
        db_table = 'apps_staff_payroll'
        verbose_name = 'スタッフ給与'
        verbose_name_plural = 'スタッフ給与'

    def __str__(self):
        return f"{self.staff}の給与情報"
