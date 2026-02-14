from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.common.models import MyModel
from apps.common.constants import Constants, get_connect_status_choices, get_request_status_choices
from apps.staff.models import Staff
from apps.profile.models import StaffProfileMynumber, StaffProfile, StaffProfileInternational, StaffProfileBank, StaffProfileDisability, StaffProfileContact, StaffProfilePayroll
from apps.master.models import StaffAgreement

class ConnectStaff(MyModel):
    """
    外部のスタッフがシステムにアクセスするための接続申請を管理するモデル。
    法人番号とメールアドレスをキーに、承認ステータスを管理する。
    """
    
    STATUS_CHOICES = get_connect_status_choices()
    
    corporate_number = models.CharField('法人番号', max_length=13, help_text='会社の法人番号')
    email = models.EmailField('メールアドレス', help_text='スタッフのメールアドレス')
    status = models.CharField('ステータス', max_length=20, choices=STATUS_CHOICES, default=Constants.CONNECT_STATUS.PENDING)
    approved_at = models.DateTimeField('承認日時', null=True, blank=True)
    approved_by = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='approved_staff_connections', verbose_name='承認者')
    
    class Meta:
        db_table = 'apps_connect_staff'
        verbose_name = 'スタッフ接続'
        verbose_name_plural = 'スタッフ接続'
        unique_together = ['corporate_number', 'email']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.corporate_number} - {self.email} ({self.get_status_display()})"
    
    @property
    def is_approved(self):
        """承認済みかどうか"""
        return self.status == Constants.CONNECT_STATUS.APPROVED
    
    def approve(self, user):
        """承認する"""
        User = get_user_model()
        self.status = Constants.CONNECT_STATUS.APPROVED
        self.approved_at = timezone.now()
        self.approved_by = user
        self.save()

        try:
            user_instance = User.objects.filter(email=self.email).first()
            if not user_instance:
                return

            staff_instance = Staff.objects.filter(email=self.email).first()
            if not staff_instance:
                return

            # マイナンバーの比較と申請
            profile_mynumber_obj = getattr(user_instance, 'staff_mynumber', None)
            if profile_mynumber_obj:
                staff_mynumber_obj = getattr(staff_instance, 'mynumber', None)
                profile_mynumber = profile_mynumber_obj.mynumber
                staff_mynumber = staff_mynumber_obj.mynumber if staff_mynumber_obj else None
                if profile_mynumber != staff_mynumber:
                    MynumberRequest.objects.get_or_create(
                        connect_staff=self,
                        profile_mynumber=profile_mynumber_obj
                    )

            # プロフィールの比較と申請
            staff_profile_obj = getattr(user_instance, 'staff_profile', None)
            if staff_profile_obj and self._is_profile_different(staff_profile_obj, staff_instance):
                ProfileRequest.objects.get_or_create(
                    connect_staff=self,
                    staff_profile=staff_profile_obj
                )

            # 連絡先の比較と申請
            profile_contact_obj = getattr(user_instance, 'staff_contact', None)
            if profile_contact_obj:
                staff_contact_obj = getattr(staff_instance, 'contact', None)
                if self._is_contact_different(profile_contact_obj, staff_contact_obj):
                    ContactRequest.objects.get_or_create(
                        connect_staff=self,
                        staff_profile_contact=profile_contact_obj
                    )

            # 銀行情報の比較と申請
            profile_bank_obj = getattr(user_instance, 'staff_bank', None)
            if profile_bank_obj:
                staff_bank_obj = getattr(staff_instance, 'bank', None)
                if self._is_bank_different(profile_bank_obj, staff_bank_obj):
                    BankRequest.objects.get_or_create(
                        connect_staff=self,
                        staff_bank_profile=profile_bank_obj
                    )

            # 障害者情報の比較と申請
            profile_disability_obj = getattr(user_instance, 'staff_disability', None)
            if profile_disability_obj:
                staff_disability_obj = getattr(staff_instance, 'disability', None)
                if self._is_disability_different(profile_disability_obj, staff_disability_obj):
                    DisabilityRequest.objects.get_or_create(
                        connect_staff=self,
                        profile_disability=profile_disability_obj
                    )

            # 外国籍情報の比較と申請
            profile_international_obj = getattr(user_instance, 'staff_international', None)
            if profile_international_obj:
                staff_international_obj = getattr(staff_instance, 'international', None)
                if self._is_international_different(profile_international_obj, staff_international_obj):
                    ConnectInternationalRequest.objects.get_or_create(
                        connect_staff=self,
                        profile_international=profile_international_obj
                    )

            # 給与情報の比較と申請
            profile_payroll_obj = getattr(user_instance, 'staff_payroll', None)
            if profile_payroll_obj:
                staff_payroll_obj = getattr(staff_instance, 'payroll', None)
                if self._is_payroll_different(profile_payroll_obj, staff_payroll_obj):
                    PayrollRequest.objects.get_or_create(
                        connect_staff=self,
                        staff_payroll_profile=profile_payroll_obj
                    )

        except Exception:
            # It is recommended to add logging in a production environment.
            pass

    def _is_profile_different(self, staff_profile, staff):
        """スタッフプロフィールとスタッフマスターを比較する"""
        fields_to_compare = [
            'name_last', 'name_first', 'name_kana_last', 'name_kana_first',
            'birth_date', 'sex', 'postal_code', 'address1', 'address2', 'address3', 'phone'
        ]

        for field in fields_to_compare:
            profile_value = getattr(staff_profile, field, None)
            staff_value = getattr(staff, field, None)

            # Note: This is a simple comparison. Depending on the data types and formats,
            # more specific comparisons might be needed (e.g., for dates or normalized strings).
            if str(profile_value or '') != str(staff_value or ''):
                return True # Found a difference

        return False # No differences found

    def _is_contact_different(self, profile_contact, staff_contact):
        """スタッフプロフィール連絡先とスタッフ連絡先を比較する"""
        fields_to_compare = [
            'emergency_contact', 'relationship', 'postal_code',
            'address1', 'address2', 'address3'
        ]

        for field in fields_to_compare:
            profile_value = getattr(profile_contact, field, None)
            staff_value = getattr(staff_contact, field, None)

            if str(profile_value or '') != str(staff_value or ''):
                return True

        return False

    def _is_bank_different(self, profile_bank, staff_bank):
        """スタッフプロフィール銀行情報とスタッフ銀行情報を比較する"""
        fields_to_compare = [
            'bank_code', 'branch_code', 'account_type', 'account_number', 'account_holder'
        ]

        for field in fields_to_compare:
            profile_value = getattr(profile_bank, field, None)
            staff_value = getattr(staff_bank, field, None)

            if str(profile_value or '') != str(staff_value or ''):
                return True

        return False

    def _is_disability_different(self, profile_disability, staff_disability):
        """スタッフプロフィール障害者情報とスタッフ障害者情報を比較する"""
        fields_to_compare = [
            'disability_type', 'disability_grade'
        ]

        for field in fields_to_compare:
            profile_value = getattr(profile_disability, field, None)
            staff_value = getattr(staff_disability, field, None)

            if str(profile_value or '') != str(staff_value or ''):
                return True

        return False

    def _is_international_different(self, profile_international, staff_international):
        """スタッフプロフィール外国籍情報とスタッフ外国籍情報を比較する"""
        fields_to_compare = [
            'residence_card_number', 'residence_status', 'residence_period_from', 'residence_period_to',
            'residence_card_front', 'residence_card_back'
        ]

        for field in fields_to_compare:
            profile_value = getattr(profile_international, field, None)
            staff_value = getattr(staff_international, field, None)

            if str(profile_value or '') != str(staff_value or ''):
                return True

        return False

    def _is_payroll_different(self, profile_payroll, staff_payroll):
        """スタッフプロフィール給与情報とスタッフ給与情報を比較する"""
        fields_to_compare = [
            'basic_pension_number',
            'employment_insurance_number',
            'previous_job_company_name',
            'previous_job_retirement_date',
        ]

        for field in fields_to_compare:
            profile_value = getattr(profile_payroll, field, None)
            staff_value = getattr(staff_payroll, field, None)

            if str(profile_value or '') != str(staff_value or ''):
                return True

        return False

    def unapprove(self):
        """未承認に戻す"""
        self.status = Constants.CONNECT_STATUS.PENDING
        self.approved_at = None
        self.approved_by = None
        self.save()

        # 関連する申請をすべて削除
        self.mynumberrequest_set.all().delete()
        self.profilerequest_set.all().delete()
        self.bankrequest_set.all().delete()
        self.contactrequest_set.all().delete()
        self.disabilityrequest_set.all().delete()
        self.connectinternationalrequest_set.all().delete()
        self.payrollrequest_set.all().delete()




class BankRequest(MyModel):
    """
    銀行情報の提出を要求するためのモデル。
    """

    STATUS_CHOICES = get_request_status_choices()

    connect_staff = models.ForeignKey(
        ConnectStaff,
        on_delete=models.CASCADE,
        verbose_name='スタッフ接続',
        help_text='関連するスタッフ接続'
    )
    staff_bank_profile = models.ForeignKey(
        StaffProfileBank,
        on_delete=models.CASCADE,
        verbose_name='スタッフ銀行プロフィール',
        help_text='関連するスタッフ銀行プロフィール'
    )
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=STATUS_CHOICES,
        default=Constants.REQUEST_STATUS.PENDING,
        help_text='申請の現在のステータス'
    )

    class Meta:
        db_table = 'apps_connect_bank_request'
        verbose_name = '銀行情報申請'
        verbose_name_plural = '銀行情報申請'
        unique_together = ['connect_staff', 'staff_bank_profile']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.connect_staff} - {self.staff_bank_profile} ({self.get_status_display()})"


class ContactRequest(MyModel):
    """
    連絡先情報の提出を要求するためのモデル。
    """

    STATUS_CHOICES = get_request_status_choices()

    connect_staff = models.ForeignKey(
        ConnectStaff,
        on_delete=models.CASCADE,
        verbose_name='スタッフ接続',
        help_text='関連するスタッフ接続'
    )
    staff_profile_contact = models.ForeignKey(
        StaffProfileContact,
        on_delete=models.CASCADE,
        verbose_name='スタッフ連絡先情報プロフィール',
        help_text='関連するスタッフ連絡先情報プロフィール'
    )
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=STATUS_CHOICES,
        default=Constants.REQUEST_STATUS.PENDING,
        help_text='申請の現在のステータス'
    )

    class Meta:
        db_table = 'apps_connect_contact_request'
        verbose_name = '連絡先情報接続申請'
        verbose_name_plural = '連絡先情報接続申請'
        unique_together = ['connect_staff', 'staff_profile_contact']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.connect_staff} - {self.staff_profile_contact} ({self.get_status_display()})"


class MynumberRequest(MyModel):
    """
    マイナンバーの提出を要求するためのモデル。
    """

    STATUS_CHOICES = get_request_status_choices()

    connect_staff = models.ForeignKey(
        ConnectStaff,
        on_delete=models.CASCADE,
        verbose_name='スタッフ接続',
        help_text='関連するスタッフ接続'
    )
    profile_mynumber = models.ForeignKey(
        StaffProfileMynumber,
        on_delete=models.CASCADE,
        verbose_name='プロフィールマイナンバー',
        help_text='関連するプロフィールマイナンバー'
    )
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=STATUS_CHOICES,
        default=Constants.REQUEST_STATUS.PENDING,
        help_text='申請の現在のステータス'
    )

    class Meta:
        db_table = 'apps_connect_mynumber_request'
        verbose_name = 'マイナンバー申請'
        verbose_name_plural = 'マイナンバー申請'
        unique_together = ['connect_staff', 'profile_mynumber']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.connect_staff} - {self.profile_mynumber} ({self.get_status_display()})"


class DisabilityRequest(MyModel):
    """
    障害者情報の提出を要求するためのモデル。
    """

    STATUS_CHOICES = get_request_status_choices()

    connect_staff = models.ForeignKey(
        ConnectStaff,
        on_delete=models.CASCADE,
        verbose_name='スタッフ接続',
        help_text='関連するスタッフ接続'
    )
    profile_disability = models.ForeignKey(
        StaffProfileDisability,
        on_delete=models.CASCADE,
        verbose_name='プロフィール障害者情報',
        help_text='関連するプロフィール障害者情報'
    )
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=STATUS_CHOICES,
        default=Constants.REQUEST_STATUS.PENDING,
        help_text='申請の現在のステータス'
    )

    class Meta:
        db_table = 'apps_connect_disability_request'
        verbose_name = '障害者情報申請'
        verbose_name_plural = '障害者情報申請'
        unique_together = ['connect_staff', 'profile_disability']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.connect_staff} - {self.profile_disability} ({self.get_status_display()})"


class ProfileRequest(MyModel):
    """
    プロフィールの提出を要求するためのモデル。
    """

    STATUS_CHOICES = get_request_status_choices()

    connect_staff = models.ForeignKey(
        ConnectStaff,
        on_delete=models.CASCADE,
        verbose_name='スタッフ接続',
        help_text='関連するスタッフ接続'
    )
    staff_profile = models.ForeignKey(
        'profile.StaffProfile',
        on_delete=models.CASCADE,
        verbose_name='スタッフプロフィール',
        help_text='関連するスタッフプロフィール',
        null=True,
        blank=True
    )
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=STATUS_CHOICES,
        default=Constants.REQUEST_STATUS.PENDING,
        help_text='申請の現在のステータス'
    )

    class Meta:
        db_table = 'apps_connect_profile_request'
        verbose_name = 'プロフィール申請'
        verbose_name_plural = 'プロフィール申請'
        unique_together = ['connect_staff', 'staff_profile']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.connect_staff} - {self.staff_profile} ({self.get_status_display()})"

    def get_staff(self):
        """関連するスタッフ情報を取得する"""
        try:
            return Staff.objects.get(email=self.connect_staff.email)
        except Staff.DoesNotExist:
            return None

    def approve(self, user):
        """プロフィール申請を承認する"""
        staff = self.get_staff()
        if not staff or not self.staff_profile:
            return False, "スタッフまたはプロフィール情報が見つかりません。"

        # 更新するフィールドを定義
        fields_to_update = [
            'name_last', 'name_first', 'name_kana_last', 'name_kana_first',
            'birth_date', 'sex', 'postal_code', 'address1', 'address2', 'address3',
            'phone',
        ]

        # StaffモデルとStaffProfileモデルのフィールドを更新
        for field in fields_to_update:
            profile_value = getattr(self.staff_profile, field, None)
            setattr(staff, field, profile_value)

        # Staffのnameフィールドを更新
        staff.name = f"{staff.name_last} {staff.name_first}"

        staff.save()

        # 申請ステータスを更新
        self.status = Constants.REQUEST_STATUS.APPROVED
        self.save()
        return True, "プロフィール申請を承認し、スタッフ情報を更新しました。"

    def reject(self, user):
        """プロフィール申請を却下する"""
        self.status = Constants.REQUEST_STATUS.REJECTED
        self.save()
        return True, "プロフィール申請を却下しました。"


class ConnectInternationalRequest(MyModel):
    """
    外国籍情報の提出を要求するためのモデル。
    """

    STATUS_CHOICES = get_request_status_choices()

    connect_staff = models.ForeignKey(
        ConnectStaff,
        on_delete=models.CASCADE,
        verbose_name='スタッフ接続',
        help_text='関連するスタッフ接続'
    )
    profile_international = models.ForeignKey(
        StaffProfileInternational,
        on_delete=models.CASCADE,
        verbose_name='プロフィール外国籍情報',
        help_text='関連するプロフィール外国籍情報'
    )
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=STATUS_CHOICES,
        default=Constants.REQUEST_STATUS.PENDING,
        help_text='申請の現在のステータス'
    )

    class Meta:
        db_table = 'apps_connect_international_request'
        verbose_name = '外国籍情報申請'
        verbose_name_plural = '外国籍情報申請'
        unique_together = ['connect_staff', 'profile_international']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.connect_staff} - {self.profile_international} ({self.get_status_display()})"


class PayrollRequest(MyModel):
    """
    給与情報の提出を要求するためのモデル。
    """

    STATUS_CHOICES = get_request_status_choices()

    connect_staff = models.ForeignKey(
        ConnectStaff,
        on_delete=models.CASCADE,
        verbose_name='スタッフ接続',
        help_text='関連するスタッフ接続'
    )
    staff_payroll_profile = models.ForeignKey(
        StaffProfilePayroll,
        on_delete=models.CASCADE,
        verbose_name='スタッフ給与プロフィール',
        help_text='関連するスタッフ給与プロフィール'
    )
    status = models.CharField(
        'ステータス',
        max_length=20,
        choices=STATUS_CHOICES,
        default=Constants.REQUEST_STATUS.PENDING,
        help_text='申請の現在のステータス'
    )

    class Meta:
        db_table = 'apps_connect_payroll_request'
        verbose_name = '給与情報申請'
        verbose_name_plural = '給与情報申請'
        unique_together = ['connect_staff', 'staff_payroll_profile']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.connect_staff} - {self.staff_payroll_profile} ({self.get_status_display()})"


class ConnectClient(MyModel):
    """
    外部のクライアント担当者がシステムにアクセスするための接続申請を管理するモデル。
    現在は将来の拡張用として準備されている。
    """
    
    STATUS_CHOICES = get_connect_status_choices()
    
    corporate_number = models.CharField('法人番号', max_length=13, help_text='会社の法人番号')
    email = models.EmailField('メールアドレス', help_text='クライアントのメールアドレス')
    status = models.CharField('ステータス', max_length=20, choices=STATUS_CHOICES, default=Constants.CONNECT_STATUS.PENDING)
    approved_at = models.DateTimeField('承認日時', null=True, blank=True)
    approved_by = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='approved_client_connections', verbose_name='承認者')
    
    class Meta:
        db_table = 'apps_connect_client'
        verbose_name = 'クライアント接続'
        verbose_name_plural = 'クライアント接続'
        unique_together = ['corporate_number', 'email']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.corporate_number} - {self.email} ({self.get_status_display()})"
    
    @property
    def is_approved(self):
        """承認済みかどうか"""
        return self.status == Constants.CONNECT_STATUS.APPROVED
    
    def approve(self, user):
        """承認する"""
        self.status = Constants.CONNECT_STATUS.APPROVED
        self.approved_at = timezone.now()
        self.approved_by = user
        self.save()
    
    def unapprove(self):
        """未承認に戻す"""
        self.status = Constants.CONNECT_STATUS.PENDING
        self.approved_at = None
        self.approved_by = None
        self.save()

class ConnectStaffAgree(MyModel):
    """
    スタッフの同意情報を管理するモデル。
    """
    email = models.EmailField('メールアドレス')
    corporate_number = models.CharField('法人番号', max_length=13)
    staff_agreement = models.ForeignKey(
        StaffAgreement,
        on_delete=models.CASCADE,
        verbose_name='スタッフ同意文言'
    )
    is_agreed = models.BooleanField('同意有無', default=False)

    class Meta:
        db_table = 'apps_connect_staff_agree'
        verbose_name = 'スタッフ同意'
        verbose_name_plural = 'スタッフ同意'
        unique_together = ['email', 'corporate_number', 'staff_agreement']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.email} - {self.staff_agreement.name}"



