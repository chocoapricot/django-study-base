from django.db import models
from django.core.validators import RegexValidator
from ..common.models import MyTenantModel, TenantManager
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
    basic_pension_number = models.CharField(
        '基礎年金番号',
        max_length=12,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r'^[\d-]{10,12}$',
                message='基礎年金番号は10桁の数字（ハイフン可）で入力してください'
            )
        ],
        help_text='10桁の数字で入力してください（ハイフンも含められます）'
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
