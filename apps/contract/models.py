from django.db import models
from apps.common.models import MyModel
from apps.client.models import Client
from apps.staff.models import Staff


class ClientContract(MyModel):
    """
    クライアント（取引先企業）との契約情報を管理するモデル。
    契約期間、金額、契約種別などを記録する。
    """
    class ContractStatus(models.TextChoices):
        DRAFT = '1', '作成中'
        PENDING = '20', '申請中'
        APPROVED = '30', '承認済'
        ISSUED = '40', '発行済'
        CONTRACTED = '50', '契約済'

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='contracts',
        verbose_name='クライアント'
    )
    contract_name = models.CharField('契約名', max_length=200)
    job_category = models.ForeignKey(
        'master.JobCategory',
        on_delete=models.SET_NULL,
        verbose_name='職種',
        null=True,
        blank=True,
    )
    contract_pattern = models.ForeignKey(
        'master.ContractPattern',
        on_delete=models.SET_NULL,
        verbose_name='契約パターン',
        null=True,
        blank=True,
        limit_choices_to={'contract_type': 'client'},
    )
    contract_number = models.CharField('契約番号', max_length=50, blank=True, null=True)
    contract_status = models.CharField(
        '契約状況',
        max_length=2,
        choices=ContractStatus.choices,
        default=ContractStatus.DRAFT,
        blank=True,
        null=True
    )
    start_date = models.DateField('契約開始日')
    end_date = models.DateField('契約終了日', blank=True, null=True)
    contract_amount = models.DecimalField('契約金額', max_digits=12, decimal_places=0, blank=True, null=True)
    description = models.TextField('契約内容', blank=True, null=True)
    notes = models.TextField('備考', blank=True, null=True)
    payment_site = models.ForeignKey(
        'master.BillPayment',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='支払いサイト'
    )
    class Meta:
        db_table = 'apps_contract_client'
        verbose_name = 'クライアント契約'
        verbose_name_plural = 'クライアント契約'
        ordering = ['-start_date', 'client__name']
        indexes = [
            models.Index(fields=['client']),
            models.Index(fields=['start_date']),
            models.Index(fields=['end_date']),
        ]
    
    def __str__(self):
        return f"{self.client.name} - {self.contract_name}"
    
    
    def clean(self):
        """バリデーション"""
        from django.core.exceptions import ValidationError
        
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError('契約開始日は終了日より前の日付を入力してください。')


class ClientContractPrint(MyModel):
    """
    クライアント契約書の発行履歴を管理するモデル。
    """
    client_contract = models.ForeignKey(
        ClientContract,
        on_delete=models.CASCADE,
        related_name='print_history',
        verbose_name='クライアント契約'
    )
    printed_at = models.DateTimeField('発行日時', auto_now_add=True)
    printed_by = models.ForeignKey(
        'accounts.MyUser',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='発行者'
    )
    pdf_file_path = models.CharField('PDFファイル参照', max_length=255)

    class Meta:
        db_table = 'apps_contract_client_print'
        verbose_name = 'クライアント契約書発行履歴'
        verbose_name_plural = 'クライアント契約書発行履歴'
        ordering = ['-printed_at']

    def __str__(self):
        return f"{self.client_contract} - {self.printed_at}"


class StaffContract(MyModel):
    """
    スタッフ（従業員・フリーランス等）との契約情報を管理するモデル。
    雇用形態、契約期間、金額などを記録する。
    """
    class ContractStatus(models.TextChoices):
        DRAFT = '1', '作成中'
        PENDING = '20', '申請中'
        APPROVED = '30', '承認済'
        ISSUED = '40', '発行済'

    staff = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name='contracts',
        verbose_name='スタッフ'
    )
    contract_name = models.CharField('契約名', max_length=200)
    job_category = models.ForeignKey(
        'master.JobCategory',
        on_delete=models.SET_NULL,
        verbose_name='職種',
        null=True,
        blank=True,
    )
    contract_pattern = models.ForeignKey(
        'master.ContractPattern',
        on_delete=models.SET_NULL,
        verbose_name='契約パターン',
        null=True,
        blank=True,
        limit_choices_to={'contract_type': 'staff'},
    )
    contract_number = models.CharField('契約番号', max_length=50, blank=True, null=True)
    contract_status = models.CharField(
        '契約状況',
        max_length=2,
        choices=ContractStatus.choices,
        default=ContractStatus.DRAFT,
        blank=True,
        null=True
    )
    start_date = models.DateField('契約開始日')
    end_date = models.DateField('契約終了日', blank=True, null=True)
    contract_amount = models.DecimalField('契約金額', max_digits=10, decimal_places=0, blank=True, null=True)
    description = models.TextField('契約内容', blank=True, null=True)
    notes = models.TextField('備考', blank=True, null=True)
    class Meta:
        db_table = 'apps_contract_staff'
        verbose_name = 'スタッフ契約'
        verbose_name_plural = 'スタッフ契約'
        ordering = ['-start_date', 'staff__name_last', 'staff__name_first']
        indexes = [
            models.Index(fields=['staff']),
            models.Index(fields=['start_date']),
            models.Index(fields=['end_date']),
        ]

    def __str__(self):
        return f"{self.staff.name_last} {self.staff.name_first} - {self.contract_name}"


    def clean(self):
        """バリデーション"""
        from django.core.exceptions import ValidationError

        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError('契約開始日は終了日より前の日付を入力してください。')


class StaffContractPrint(MyModel):
    """
    スタッフ契約書の発行履歴を管理するモデル。
    """
    staff_contract = models.ForeignKey(
        StaffContract,
        on_delete=models.CASCADE,
        related_name='print_history',
        verbose_name='スタッフ契約'
    )
    printed_at = models.DateTimeField('発行日時', auto_now_add=True)
    printed_by = models.ForeignKey(
        'accounts.MyUser',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='発行者'
    )
    pdf_file_path = models.CharField('PDFファイル参照', max_length=255)

    class Meta:
        db_table = 'apps_contract_staff_print'
        verbose_name = 'スタッフ契約書発行履歴'
        verbose_name_plural = 'スタッフ契約書発行履歴'
        ordering = ['-printed_at']

    def __str__(self):
        return f"{self.staff_contract} - {self.printed_at}"
