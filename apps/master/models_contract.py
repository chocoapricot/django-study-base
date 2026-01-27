from django.db import models
from apps.common.models import MyTenantModel
from apps.system.settings.models import Dropdowns


class ContractPattern(MyTenantModel):
    """
    契約書パターンマスタ
    """
    name = models.CharField('名称', max_length=100)
    domain = models.CharField(
        '対象',
        max_length=2,
        choices=[('1', 'スタッフ'), ('10', 'クライアント')],
        default='1',
    )
    contract_type_code = models.CharField('契約種別', max_length=2, blank=True, null=True)
    employment_type = models.ForeignKey(
        'EmploymentType',
        on_delete=models.SET_NULL,
        verbose_name='雇用形態',
        blank=True,
        null=True
    )
    memo = models.TextField('メモ', blank=True, null=True)
    display_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 'apps_master_contract_pattern'
        verbose_name = '契約書パターン'
        verbose_name_plural = '契約書パターン'
        ordering = ['domain', 'display_order']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['display_order']),
        ]

    def __str__(self):
        return self.name


class ContractTerms(MyTenantModel):
    """
    契約文言マスタ
    """
    contract_pattern = models.ForeignKey(
        ContractPattern,
        on_delete=models.CASCADE,
        verbose_name='契約書パターン',
        related_name='terms'
    )
    contract_clause = models.TextField('契約条項')
    contract_terms = models.TextField('契約文言')
    POSITION_CHOICES = [
        (1, '前文'),
        (2, '本文'),
        (3, '末文'),
    ]
    display_position = models.IntegerField(
        '表示場所',
        choices=POSITION_CHOICES,
        default=2,
    )
    memo = models.CharField('メモ', max_length=255, blank=True, null=True)
    display_order = models.IntegerField('表示順', default=0)

    class Meta:
        db_table = 'apps_master_contract_terms'
        verbose_name = '契約文言'
        verbose_name_plural = '契約文言'
        ordering = ['display_position', 'display_order']
        indexes = [
            models.Index(fields=['display_position']),
            models.Index(fields=['display_order']),
        ]

    def __str__(self):
        return f"{self.contract_pattern.name} - {self.id}"


class JobCategory(MyTenantModel):
    """
    職種マスタ
    """
    name = models.CharField('名称', max_length=100)
    display_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)
    is_manufacturing_dispatch = models.BooleanField('製造派遣該当', default=False, help_text='この職種が製造業務への労働者派遣に該当する場合にチェックします。')
    is_agriculture_fishery_dispatch = models.BooleanField('農業漁業派遣該当', default=False, help_text='この職種が農業・漁業への労働者派遣に該当する場合にチェックします。')
    is_specified_skilled_worker = models.BooleanField('特定技能外国人受入該当', default=False, help_text='この職種が特定技能外国人の受入れに該当する場合にチェックします。')
    jobs_kourou = models.ForeignKey(
        Dropdowns,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='職業分類(厚労省)',
        related_name='job_category_kourou',
        limit_choices_to={'category': 'jobs_kourou', 'active': True}
    )
    jobs_soumu = models.ForeignKey(
        Dropdowns,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='職業分類(総務省)',
        related_name='job_category_soumu',
        limit_choices_to={'category': 'jobs_soumu', 'active': True}
    )
    jobs_seirei = models.ForeignKey(
        Dropdowns,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='派遣政令業務',
        related_name='job_category_seirei',
        limit_choices_to={'category': 'jobs_seirei', 'active': True}
    )

    class Meta:
        db_table = 'apps_master_job_category'
        verbose_name = '職種マスタ'
        verbose_name_plural = '職種マスタ'
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['display_order']),
        ]

    def __str__(self):
        return self.name






class EmploymentType(MyTenantModel):
    """
    雇用形態マスタ
    """
    name = models.CharField('名称', max_length=100)
    display_order = models.IntegerField('表示順', default=0)
    is_fixed_term = models.BooleanField('有期', default=True)
    worktime_pattern = models.ForeignKey(
        'WorkTimePattern',
        on_delete=models.SET_NULL,
        verbose_name='就業時間パターン',
        blank=True,
        null=True,
        related_name='employment_types'
    )
    overtime_pattern = models.ForeignKey(
        'OvertimePattern',
        on_delete=models.SET_NULL,
        verbose_name='時間外算出パターン',
        blank=True,
        null=True,
        related_name='employment_types'
    )
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 'apps_master_employment_type'
        verbose_name = '雇用形態'
        verbose_name_plural = '雇用形態'
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['display_order']),
        ]

    def __str__(self):
        return self.name




