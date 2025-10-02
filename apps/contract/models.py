from django.db import models
from apps.common.models import MyModel
from apps.client.models import Client, ClientUser, ClientDepartment
from apps.staff.models import Staff
from django.contrib.auth import get_user_model
from apps.company.models import CompanyUser

User = get_user_model()

class ClientContract(MyModel):
    """
    クライアント（取引先企業）との契約情報を管理するモデル。
    契約期間、金額、契約種別などを記録する。
    """
    class ContractStatus(models.TextChoices):
        DRAFT = '1', '作成中'
        PENDING = '5', '申請中'
        APPROVED = '10', '承認済'
        ISSUED = '20', '発行済'
        CONFIRMED = '30', '確認済'

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='contracts',
        verbose_name='クライアント'
    )
    client_contract_type_code = models.CharField(
        '契約種別',
        max_length=2,
        blank=True,
        null=True
    )
    corporate_number = models.CharField('法人番号', max_length=13, blank=True, null=True)
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
        on_delete=models.PROTECT,
        verbose_name='契約パターン',
        limit_choices_to={'domain': '10'},
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
    approved_at = models.DateTimeField('承認日時', blank=True, null=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_client_contracts',
        verbose_name='承認者'
    )
    issued_at = models.DateTimeField('発行日時', blank=True, null=True)
    issued_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='issued_client_contracts',
        verbose_name='発行者'
    )
    confirmed_at = models.DateTimeField('確認日時', blank=True, null=True)
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
        permissions = [
            ('confirm_clientcontract', 'クライアント契約を確認できる'),
        ]
    
    def __str__(self):
        return f"{self.client.name} - {self.contract_name}"
    
    
    @property
    def is_approved_or_later(self):
        """承認済、またはそれ以降のステータスかどうかを判定する"""
        return int(self.contract_status) >= int(self.ContractStatus.APPROVED)

    @property
    def is_issued_or_later(self):
        """発行済、またはそれ以降のステータスかどうかを判定する"""
        return int(self.contract_status) >= int(self.ContractStatus.ISSUED)

    def clean(self):
        """バリデーション"""
        from django.core.exceptions import ValidationError
        
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError('契約開始日は終了日より前の日付を入力してください。')


class ClientContractPrint(MyModel):
    """
    クライアント契約書の発行履歴を管理するモデル。
    """
    class PrintType(models.TextChoices):
        CONTRACT = '10', '契約書'
        QUOTATION = '20', '見積書'

    client_contract = models.ForeignKey(
        ClientContract,
        on_delete=models.CASCADE,
        related_name='print_history',
        verbose_name='クライアント契約'
    )
    print_type = models.CharField(
        '種別',
        max_length=2,
        choices=PrintType.choices,
        default=PrintType.CONTRACT,
    )
    printed_at = models.DateTimeField('発行日時', auto_now_add=True)
    printed_by = models.ForeignKey(
        'accounts.MyUser',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='発行者'
    )
    pdf_file = models.FileField('PDFファイル', upload_to='client_prints/', null=True, blank=True)
    document_title = models.CharField('タイトル', max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'apps_contract_client_print'
        verbose_name = 'クライアント契約書発行履歴'
        verbose_name_plural = 'クライアント契約書発行履歴'
        ordering = ['-printed_at']

    def __str__(self):
        return f"{self.client_contract} - {self.get_print_type_display()} - {self.printed_at}"


class StaffContract(MyModel):
    """
    スタッフ（従業員・フリーランス等）との契約情報を管理するモデル。
    雇用形態、契約期間、金額などを記録する。
    """
    class ContractStatus(models.TextChoices):
        DRAFT = '1', '作成中'
        PENDING = '5', '申請中'
        APPROVED = '10', '承認済'
        ISSUED = '20', '発行済'
        CONFIRMED = '30', '確認済'

    staff = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name='contracts',
        verbose_name='スタッフ'
    )
    corporate_number = models.CharField('法人番号', max_length=13, blank=True, null=True)
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
        limit_choices_to={'domain': '1'},
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
    approved_at = models.DateTimeField('承認日時', blank=True, null=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_staff_contracts',
        verbose_name='承認者'
    )
    issued_at = models.DateTimeField('発行日時', blank=True, null=True)
    issued_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='issued_staff_contracts',
        verbose_name='発行者'
    )
    confirmed_at = models.DateTimeField('確認日時', blank=True, null=True)
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
        permissions = [
            ('confirm_staffcontract', 'スタッフ契約を確認できる'),
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
    pdf_file = models.FileField('PDFファイル', upload_to='staff_prints/', null=True, blank=True)
    document_title = models.CharField('タイトル', max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'apps_contract_staff_print'
        verbose_name = 'スタッフ契約書発行履歴'
        verbose_name_plural = 'スタッフ契約書発行履歴'
        ordering = ['-printed_at']

    def __str__(self):
        return f"{self.staff_contract} - {self.printed_at}"


class ClientContractNumber(MyModel):
    """
    クライアント契約番号を管理するためのモデル。
    クライアントコードと年月をキーに、最新の連番を保持する。
    """
    client_code = models.CharField('クライアントコード', max_length=8, db_index=True)
    year_month = models.CharField('年月', max_length=6, db_index=True)
    last_number = models.PositiveIntegerField('最終番号', default=0)
    corporate_number = models.CharField('法人番号', max_length=13, blank=True, null=True)

    class Meta:
        db_table = 'apps_contract_client_number'
        verbose_name = 'クライアント契約番号管理'
        verbose_name_plural = 'クライアント契約番号管理'
        unique_together = ('client_code', 'year_month')

    def __str__(self):
        return f"{self.client_code}-{self.year_month}-{self.last_number}"


class StaffContractNumber(MyModel):
    """
    スタッフ契約番号を管理するためのモデル。
    社員番号と年月をキーに、最新の連番を保持する。
    """
    employee_no = models.CharField('社員番号', max_length=10, db_index=True)
    year_month = models.CharField('年月', max_length=6, db_index=True)
    last_number = models.PositiveIntegerField('最終番号', default=0)
    corporate_number = models.CharField('法人番号', max_length=13, blank=True, null=True)

    class Meta:
        db_table = 'apps_contract_staff_number'
        verbose_name = 'スタッフ契約番号管理'
        verbose_name_plural = 'スタッフ契約番号管理'
        unique_together = ('employee_no', 'year_month')

    def __str__(self):
        return f"{self.employee_no}-{self.year_month}-{self.last_number}"


class ClientContractHaken(MyModel):
    """
    クライアント契約派遣情報
    """
    client_contract = models.OneToOneField(
        ClientContract,
        on_delete=models.CASCADE,
        related_name='haken_info',
        verbose_name='クライアント契約'
    )
    # 派遣先
    haken_office = models.ForeignKey(
        ClientDepartment,
        on_delete=models.SET_NULL,
        related_name='haken_offices',
        verbose_name='派遣先事業所',
        null=True, blank=True,
    )
    haken_unit = models.ForeignKey(
        ClientDepartment,
        on_delete=models.SET_NULL,
        related_name='haken_units',
        verbose_name='組織単位',
        null=True, blank=True,
    )
    commander = models.ForeignKey(
        ClientUser,
        on_delete=models.SET_NULL,
        related_name='haken_commanders',
        verbose_name='派遣先指揮命令者',
        null=True, blank=True,
    )
    complaint_officer_client = models.ForeignKey(
        ClientUser,
        on_delete=models.SET_NULL,
        related_name='haken_complaint_officers_client',
        verbose_name='派遣先苦情申出先',
        null=True, blank=True,
    )
    responsible_person_client = models.ForeignKey(
        ClientUser,
        on_delete=models.SET_NULL,
        related_name='haken_responsible_persons_client',
        verbose_name='派遣先責任者',
        null=True, blank=True,
    )
    # 派遣元
    complaint_officer_company = models.ForeignKey(
        CompanyUser,
        on_delete=models.SET_NULL,
        related_name='haken_complaint_officers_company',
        verbose_name='派遣元苦情申出先',
        null=True, blank=True,
    )
    responsible_person_company = models.ForeignKey(
        CompanyUser,
        on_delete=models.SET_NULL,
        related_name='haken_responsible_persons_company',
        verbose_name='派遣元責任者',
        null=True, blank=True,
    )
    # 限定の別
    limit_by_agreement = models.CharField(
        '協定対象派遣労働者に限定するか否かの別',
        max_length=1,
        choices=[('0', '限定しない'), ('1', '限定する')],
        null=True, blank=True,
    )
    limit_indefinite_or_senior = models.CharField(
        '無期雇用派遣労働者又は60歳以上の者に限定するか否かの別',
        max_length=1,
        choices=[('0', '限定しない'), ('1', '限定する')],
        null=True, blank=True,
    )
    work_location = models.TextField('就業場所', blank=True, null=True)
    business_content = models.TextField('業務内容', blank=True, null=True)
    responsibility_degree = models.CharField('責任の程度', max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'apps_contract_client_haken'
        verbose_name = 'クライアント契約派遣情報'
        verbose_name_plural = 'クライアント契約派遣情報'

    def __str__(self):
        return f"{self.client_contract}"
