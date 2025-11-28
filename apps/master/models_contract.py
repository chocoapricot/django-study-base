from django.db import models
from apps.common.models import MyModel
from apps.system.settings.models import Dropdowns


class ContractPattern(MyModel):
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


class ContractTerms(MyModel):
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


class JobCategory(MyModel):
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






class EmploymentType(MyModel):
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


class OvertimePattern(MyModel):
    """
    時間外算出パターンマスタ
    """
    name = models.CharField('名称', max_length=100)
    calculate_midnight_premium = models.BooleanField('深夜割増を計算する', default=False)
    memo = models.TextField('メモ', blank=True, null=True)
    
    # 計算方式選択
    CALCULATION_TYPE_CHOICES = [
        ('premium', '割増'),
        ('monthly_range', '月単位時間範囲'),
        ('variable', '1ヶ月単位変形労働'),
    ]
    calculation_type = models.CharField('計算方式', max_length=20, choices=CALCULATION_TYPE_CHOICES, default='premium')
    
    # 割増方式の設定
    daily_overtime_enabled = models.BooleanField('日単位時間外計算', default=False)
    daily_overtime_hours = models.IntegerField('日単位時間外時間', default=8, blank=True, null=True)
    daily_overtime_minutes = models.IntegerField('日単位時間外分', default=0, blank=True, null=True)
    
    weekly_overtime_enabled = models.BooleanField('週単位時間外計算', default=False)
    weekly_overtime_hours = models.IntegerField('週単位時間外時間', default=40, blank=True, null=True)
    weekly_overtime_minutes = models.IntegerField('週単位時間外分', default=0, blank=True, null=True)
    
    monthly_overtime_enabled = models.BooleanField('月単位時間外割増', default=False)
    monthly_overtime_hours = models.IntegerField('月単位時間外割増時間', default=60, blank=True, null=True)
    
    monthly_estimated_enabled = models.BooleanField('月単位見込み残業', default=False)
    monthly_estimated_hours = models.IntegerField('月単位見込み残業時間', default=20, blank=True, null=True)
    
    # 月単位時間範囲方式の設定
    monthly_range_min = models.IntegerField('月単位時間範囲最小', default=140, blank=True, null=True)
    monthly_range_max = models.IntegerField('月単位時間範囲最大', default=160, blank=True, null=True)
    
    # 1ヶ月単位変形労働の設定
    variable_daily_overtime_enabled = models.BooleanField('変形労働日単位時間外計算', default=False)
    variable_daily_overtime_hours = models.IntegerField('変形労働日単位時間外時間', default=8, blank=True, null=True)
    variable_daily_overtime_minutes = models.IntegerField('変形労働日単位時間外分', default=0, blank=True, null=True)
    
    variable_weekly_overtime_enabled = models.BooleanField('変形労働週単位時間外計算', default=False)
    variable_weekly_overtime_hours = models.IntegerField('変形労働週単位時間外時間', default=40, blank=True, null=True)
    variable_weekly_overtime_minutes = models.IntegerField('変形労働週単位時間外分', default=0, blank=True, null=True)
    
    # 28日～31日の設定
    days_28_hours = models.IntegerField('28日時間', default=160)
    days_28_minutes = models.IntegerField('28日分', default=0)
    days_29_hours = models.IntegerField('29日時間', default=165)
    days_29_minutes = models.IntegerField('29日分', default=42)
    days_30_hours = models.IntegerField('30日時間', default=171)
    days_30_minutes = models.IntegerField('30日分', default=25)
    days_31_hours = models.IntegerField('31日時間', default=177)
    days_31_minutes = models.IntegerField('31日分', default=8)
    
    display_order = models.IntegerField('表示順', default=0)
    is_active = models.BooleanField('有効', default=True)

    class Meta:
        db_table = 'apps_master_overtime_pattern'
        verbose_name = '時間外算出パターン'
        verbose_name_plural = '時間外算出パターン'
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['display_order']),
        ]

    def __str__(self):
        return self.name


