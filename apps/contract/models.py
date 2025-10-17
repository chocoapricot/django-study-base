from django.db import models
from apps.common.models import MyModel
from apps.common.constants import Constants
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

    staff_contracts = models.ManyToManyField(
        'StaffContract',
        through='ContractAssignment',
        related_name='client_contracts',
        verbose_name='関連スタッフ契約'
    )
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
        verbose_name='契約書パターン',
        limit_choices_to={'domain': Constants.DOMAIN.CLIENT},
    )
    contract_number = models.CharField('契約番号', max_length=50, blank=True, null=True)

    contract_status = models.CharField(
        '契約状況',
        max_length=2,
        default=Constants.CONTRACT_STATUS.DRAFT,
        blank=True,
        null=True
    )
    start_date = models.DateField('契約開始日')
    end_date = models.DateField('契約終了日', blank=True, null=True)
    contract_amount = models.DecimalField('契約金額', max_digits=12, decimal_places=0, blank=True, null=True)
    bill_unit = models.CharField('請求単位', max_length=10, blank=True, null=True)
    business_content = models.TextField('業務内容', blank=True, null=True)
    notes = models.TextField('備考', blank=True, null=True)
    memo = models.TextField('メモ', blank=True, null=True)
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
    # 見積書の発行日時・発行者（UI 判定用。履歴は ClientContractPrint に保持）
    quotation_issued_at = models.DateTimeField('見積発行日時', blank=True, null=True)
    quotation_issued_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='issued_client_quotations',
        verbose_name='見積発行者'
    )
    # 抵触日通知書の共有日時・共有者
    teishokubi_notification_issued_at = models.DateTimeField('抵触日通知書共有日時', blank=True, null=True)
    teishokubi_notification_issued_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='issued_teishokubi_notifications',
        verbose_name='抵触日通知書共有者'
    )
    confirmed_at = models.DateTimeField('確認日時', blank=True, null=True)
    confirmed_by = models.ForeignKey(
        ClientUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='confirmed_client_contracts',
        verbose_name='確認者'
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
        permissions = [
            ('confirm_clientcontract', 'クライアント契約を確認できる'),
        ]
    
    def __str__(self):
        return f"{self.client.name} - {self.contract_name}"
    
    @property
    def is_approved_or_later(self):
        """承認済、またはそれ以降のステータスかどうかを判定する"""
        return int(self.contract_status) >= int(Constants.CONTRACT_STATUS.APPROVED)

    @property
    def is_issued_or_later(self):
        """発行済、またはそれ以降のステータスかどうかを判定する"""
        return int(self.contract_status) >= int(Constants.CONTRACT_STATUS.ISSUED)

    def clean(self):
        """バリデーション"""
        from django.core.exceptions import ValidationError
        
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError('契約開始日は終了日より前の日付を入力してください。')

    @property
    def contract_type_display_name(self):
        """表示用の契約種別名を取得する。TTPの場合は「派遣（TTP）」と表示する。"""
        from apps.system.settings.models import Dropdowns
        from django.core.exceptions import ObjectDoesNotExist
        try:
            dropdown = Dropdowns.objects.get(category='client_contract_type', value=self.client_contract_type_code)
            base_name = dropdown.name
        except Dropdowns.DoesNotExist:
            base_name = "不明"

        if self.client_contract_type_code == Constants.CLIENT_CONTRACT_TYPE.DISPATCH:  # 派遣
            try:
                # 関連オブジェクトが存在するかどうかを堅牢にチェック
                if self.haken_info and self.haken_info.ttp_info:
                    return f"{base_name}（TTP）"
            except ObjectDoesNotExist:
                # haken_infoまたはttp_infoが存在しない場合
                pass
        return base_name


class ClientContractPrint(MyModel):
    """
    クライアント契約書の発行履歴を管理するモデル。
    """
    class PrintType(models.TextChoices):
        CONTRACT = '10', '契約書'
        QUOTATION = '20', '見積書'
        TEISHOKUBI_NOTIFICATION = '30', '抵触日通知書'
        DISPATCH_NOTIFICATION = '40', '派遣通知書'

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
    # 発行時点の契約番号を保存（後で契約番号が変更/クリアされても履歴に残す）
    contract_number = models.CharField('契約番号', max_length=50, blank=True, null=True)
    # NOTE: UI の発行判定は ClientContract 側のフィールドで行うため、
    # Print 側に is_active フラグは不要。

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
    staff = models.ForeignKey(
        Staff,
        on_delete=models.CASCADE,
        related_name='contracts',
        verbose_name='スタッフ'
    )
    employment_type = models.ForeignKey(
        'master.EmploymentType',
        on_delete=models.SET_NULL,
        verbose_name='雇用形態',
        blank=True,
        null=True,
        help_text='契約作成時点のスタッフの雇用形態を保存'
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
        verbose_name='契約書パターン',
        limit_choices_to={'domain': Constants.DOMAIN.STAFF},
    )
    contract_number = models.CharField('契約番号', max_length=50, blank=True, null=True)
    contract_status = models.CharField(
        '契約状況',
        max_length=2,
        default=Constants.CONTRACT_STATUS.DRAFT,
        blank=True,
        null=True
    )
    start_date = models.DateField('契約開始日')
    end_date = models.DateField('契約終了日', blank=True, null=True)
    contract_amount = models.DecimalField('契約金額', max_digits=10, decimal_places=0, blank=True, null=True)
    pay_unit = models.CharField('支払単位', max_length=10, blank=True, null=True)
    work_location = models.TextField('就業場所', blank=True, null=True)
    business_content = models.TextField('業務内容', blank=True, null=True)
    notes = models.TextField('備考', blank=True, null=True)
    memo = models.TextField('メモ', blank=True, null=True)
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

    def validate_minimum_wage(self):
        """最低賃金バリデーション"""
        from django.core.exceptions import ValidationError
        if self.pay_unit == Constants.PAY_UNIT.HOURLY and self.contract_amount is not None and self.work_location:
            from apps.master.models import MinimumPay
            from apps.system.settings.models import Dropdowns

            prefectures = Dropdowns.objects.filter(category='pref', active=True)
            found_prefecture = None
            for pref_dropdown in prefectures:
                if pref_dropdown.name in self.work_location:
                    found_prefecture = pref_dropdown
                    break

            if found_prefecture:
                minimum_wage_record = MinimumPay.objects.filter(
                    pref=found_prefecture.value,
                    start_date__lte=self.start_date,
                    is_active=True
                ).order_by('-start_date').first()

                if minimum_wage_record and self.contract_amount < minimum_wage_record.hourly_wage:
                    raise ValidationError(
                        f'{found_prefecture.name}の最低賃金（{minimum_wage_record.hourly_wage}円）を下回っています。'
                    )


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
    # 発行時点の契約番号を保存
    contract_number = models.CharField('契約番号', max_length=50, blank=True, null=True)

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
        choices=[
            (Constants.LIMIT_BY_AGREEMENT.NOT_LIMITED, '限定しない'),
            (Constants.LIMIT_BY_AGREEMENT.LIMITED, '限定する')
        ],
        null=True, blank=True,
    )
    limit_indefinite_or_senior = models.CharField(
        '無期雇用派遣労働者又は60歳以上の者に限定するか否かの別',
        max_length=1,
        choices=[
            (Constants.LIMIT_BY_AGREEMENT.NOT_LIMITED, '限定しない'),
            (Constants.LIMIT_BY_AGREEMENT.LIMITED, '限定する')
        ],
        null=True, blank=True,
    )
    work_location = models.TextField('就業場所', blank=True, null=True)
    responsibility_degree = models.CharField('責任の程度', max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'apps_contract_client_haken'
        verbose_name = 'クライアント契約派遣情報'
        verbose_name_plural = 'クライアント契約派遣情報'

    def __str__(self):
        return f"{self.client_contract}"


class ClientContractTtp(MyModel):
    """
    クライアント契約紹介予定派遣情報
    """
    haken = models.OneToOneField(
        ClientContractHaken,
        on_delete=models.CASCADE,
        related_name='ttp_info',
        verbose_name='クライアント契約派遣情報'
    )
    contract_period = models.TextField('契約期間', blank=True, null=True)
    probation_period = models.TextField('試用期間に関する事項', blank=True, null=True)
    business_content = models.TextField('業務内容', blank=True, null=True)
    work_location = models.TextField('就業場所', blank=True, null=True)
    working_hours = models.TextField('始業・終業', blank=True, null=True)
    break_time = models.TextField('休憩時間', blank=True, null=True)
    overtime = models.TextField('所定時間外労働', blank=True, null=True)
    holidays = models.TextField('休日', blank=True, null=True)
    vacations = models.TextField('休暇', blank=True, null=True)
    wages = models.TextField('賃金', blank=True, null=True)
    insurances = models.TextField('各種保険の加入', blank=True, null=True)
    employer_name = models.TextField('雇用しようとする者の名称', blank=True, null=True)
    other = models.TextField('その他', blank=True, null=True)

    class Meta:
        db_table = 'apps_contract_client_ttp'
        verbose_name = 'クライアント契約紹介予定派遣情報'
        verbose_name_plural = 'クライアント契約紹介予定派遣情報'

    def __str__(self):
        return f"{self.haken.client_contract}"


class ContractAssignment(MyModel):
    """
    クライアント契約とスタッフ契約の関連付けを管理するモデル。
    """
    client_contract = models.ForeignKey(
        ClientContract,
        on_delete=models.CASCADE,
        verbose_name='クライアント契約'
    )
    staff_contract = models.ForeignKey(
        'StaffContract',
        on_delete=models.CASCADE,
        verbose_name='スタッフ契約'
    )
    assigned_at = models.DateTimeField('アサイン日時', auto_now_add=True)

    class Meta:
        db_table = 'apps_contract_assignment'
        verbose_name = '契約アサイン'
        verbose_name_plural = '契約アサイン'
        unique_together = ('client_contract', 'staff_contract')

    def __str__(self):
        return f"{self.client_contract} - {self.staff_contract}"

    def clean(self):
        """
        バリデーション：割当終了日が抵触日を超えていないかチェック
        """
        from django.core.exceptions import ValidationError
        from datetime import date
        from .teishokubi_calculator import TeishokubiCalculator

        # 外国籍情報チェック
        self._validate_foreign_staff_assignment()

        # 派遣契約かつ派遣社員(有期)かつ60歳未満の場合のみチェック
        if (self.client_contract.client_contract_type_code == Constants.CLIENT_CONTRACT_TYPE.DISPATCH and
                self.staff_contract.employment_type and self.staff_contract.employment_type.is_fixed_term):

            # 割当開始日時点で60歳未満かチェック
            staff = self.staff_contract.staff
            assignment_start_date = max(self.client_contract.start_date, self.staff_contract.start_date)
            
            is_under_60 = True  # デフォルトは60歳未満として扱う
            if staff.birth_date:
                age_at_assignment_start = assignment_start_date.year - staff.birth_date.year - \
                    ((assignment_start_date.month, assignment_start_date.day) < (staff.birth_date.month, staff.birth_date.day))
                if age_at_assignment_start >= 60:
                    is_under_60 = False

            if is_under_60:
                staff_email = staff.email
                client_corporate_number = self.client_contract.client.corporate_number

                if hasattr(self.client_contract, 'haken_info') and self.client_contract.haken_info and self.client_contract.haken_info.haken_unit:
                    organization_name = self.client_contract.haken_info.haken_unit.name

                    calculator = TeishokubiCalculator(
                        staff_email=staff_email,
                        client_corporate_number=client_corporate_number,
                        organization_name=organization_name
                    )

                    # この割当を追加した場合の抵触日を計算
                    conflict_date = calculator.calculate_conflict_date_without_update(new_assignment_instance=self)

                    if conflict_date:
                        # 割当終了日を計算
                        assignment_end_date = min(
                            self.client_contract.end_date if self.client_contract.end_date else date.max,
                            self.staff_contract.end_date if self.staff_contract.end_date else date.max
                        )

                        if assignment_end_date > conflict_date:
                            raise ValidationError(
                                f'割当終了日（{assignment_end_date}）が抵触日（{conflict_date}）を超えています。'
                            )

        # 無期雇用派遣労働者又は60歳以上の者に限定する場合のチェック
        if (hasattr(self.client_contract, 'haken_info') and self.client_contract.haken_info and
                self.client_contract.haken_info.limit_indefinite_or_senior == Constants.LIMIT_BY_AGREEMENT.LIMITED):

            staff = self.staff_contract.staff
            contract_start_date = self.client_contract.start_date

            # 条件1: 無期雇用か
            is_indefinite_employment = not self.staff_contract.employment_type.is_fixed_term

            # 条件2: 契約開始日時点で60歳以上か
            is_over_60 = False
            if staff.birth_date:
                age_at_start = contract_start_date.year - staff.birth_date.year - \
                    ((contract_start_date.month, contract_start_date.day) < (staff.birth_date.month, staff.birth_date.day))
                if age_at_start >= 60:
                    is_over_60 = True

            if not (is_indefinite_employment or is_over_60):
                raise ValidationError(
                    f'この契約は無期雇用派遣労働者又は60歳以上の者に限定されています。スタッフ「{staff.name}」は条件を満たしていません。'
                )

    def _validate_foreign_staff_assignment(self):
        """外国籍スタッフの契約アサインバリデーション"""
        from django.core.exceptions import ValidationError
        from datetime import date

        staff = self.staff_contract.staff
        
        # 外国籍情報が登録されているかチェック
        try:
            international_info = staff.international
        except:
            # 外国籍情報が登録されていない場合は何もしない
            return

        # 外国籍情報が登録されている場合のチェック
        if international_info:
            # 1. 割当終了日より前に在留期限がある場合にはエラー
            assignment_end_date = min(
                self.client_contract.end_date if self.client_contract.end_date else date.max,
                self.staff_contract.end_date if self.staff_contract.end_date else date.max
            )
            
            if assignment_end_date != date.max and international_info.residence_period_to and assignment_end_date > international_info.residence_period_to:
                raise ValidationError(
                    f'割当終了日（{assignment_end_date}）が在留期限（{international_info.residence_period_to}）を超えています。'
                    f'在留期限内の日付を設定してください。'
                )

            # 2. 職種が特定技能外国人受入該当になっていなければエラー
            if not self.staff_contract.job_category:
                raise ValidationError(
                    f'外国籍スタッフ「{staff.name_last} {staff.name_first}」の契約では、'
                    f'特定技能外国人受入該当の職種を選択してください。'
                )
            elif not self.staff_contract.job_category.is_specified_skilled_worker:
                raise ValidationError(
                    f'外国籍スタッフ「{staff.name_last} {staff.name_first}」の契約では、'
                    f'特定技能外国人受入該当の職種を選択してください。'
                )

            # 3. クライアント契約が派遣の場合、職種が農業漁業派遣該当になっていなければエラー
            if (self.client_contract.client_contract_type_code == Constants.CLIENT_CONTRACT_TYPE.DISPATCH and
                self.staff_contract.job_category and not self.staff_contract.job_category.is_agriculture_fishery_dispatch):
                raise ValidationError(
                    f'外国籍スタッフ「{staff.name_last} {staff.name_first}」の派遣契約では、'
                    f'農業漁業派遣該当の職種を選択してください。'
                )


class StaffContractTeishokubi(MyModel):
    """
    スタッフの個人抵触日を管理するモデル。
    """
    staff_email = models.EmailField('スタッフメールアドレス', blank=True, null=True)
    client_corporate_number = models.CharField('クライアント法人番号', max_length=13, blank=True, null=True)
    organization_name = models.CharField('組織名', max_length=255)
    dispatch_start_date = models.DateField('派遣開始日')
    conflict_date = models.DateField('抵触日')

    class Meta:
        db_table = 'apps_contract_staff_teishokubi'
        verbose_name = '個人抵触日'
        verbose_name_plural = '個人抵触日'
        ordering = ['-dispatch_start_date', 'staff_email']

    def __str__(self):
        return f"{self.staff_email} - {self.organization_name}"


class StaffContractTeishokubiDetail(MyModel):
    """
    スタッフの個人抵触日の算出詳細を管理するモデル。
    """
    teishokubi = models.ForeignKey(
        StaffContractTeishokubi,
        on_delete=models.CASCADE,
        related_name='details',
        verbose_name='個人抵触日'
    )
    assignment_start_date = models.DateField('割当開始日')
    assignment_end_date = models.DateField('割当終了日')
    is_calculated = models.BooleanField('算出対象', default=True)
    is_manual = models.BooleanField('手動作成', default=False)

    class Meta:
        db_table = 'apps_contract_staff_teishokubi_detail'
        verbose_name = '個人抵触日算出詳細'
        verbose_name_plural = '個人抵触日算出詳細'
        ordering = ['assignment_start_date']

    def __str__(self):
        return f"{self.teishokubi} - {self.assignment_start_date}"
