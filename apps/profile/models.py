from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from apps.common.models import MyModel
from django_currentuser.db.models import CurrentUserField

User = get_user_model()


def residence_card_path(instance, filename):
    """
    アップロード先のパスを生成する
    'profile-files/<user_id>/<filename>'
    """
    user_id = instance.user.id
    return f'profile-files/{user_id}/{filename}'


def validate_mynumber(value):
    """マイナンバーのバリデーション関数"""
    if not value:
        return
    
    try:
        from stdnum.jp import in_
        if not in_.is_valid(value):
            raise ValidationError('正しいマイナンバーを入力してください。')
    except ImportError:
        # python-stdnumがインストールされていない場合は基本的なチェックのみ
        import re
        if not re.match(r'^\d{12}$', value):
            raise ValidationError('マイナンバーは12桁の数字で入力してください。')
    except Exception:
        raise ValidationError('正しいマイナンバーを入力してください。')


class StaffProfile(MyModel):
    """
    スタッフ（ユーザー）のプロフィール情報を管理するモデル。
    Userモデルと1対1で連携し、詳細な個人情報（住所、連絡先など）を保持する。
    """
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        verbose_name='ユーザー',
        related_name='staff_profile'
    )
    name_last = models.CharField(
        max_length=50, 
        verbose_name='姓',
        help_text='姓を入力してください'
    )
    name_first = models.CharField(
        max_length=50, 
        verbose_name='名',
        help_text='名を入力してください'
    )
    name_kana_last = models.CharField(
        max_length=50, 
        verbose_name='姓（カナ）',
        help_text='姓をカタカナで入力してください'
    )
    name_kana_first = models.CharField(
        max_length=50, 
        verbose_name='名（カナ）',
        help_text='名をカタカナで入力してください'
    )
    birth_date = models.DateField(
        verbose_name='生年月日',
        null=True,
        blank=True,
        help_text='生年月日を入力してください'
    )
    sex = models.IntegerField(
        verbose_name='性別',
        null=True,
        blank=True,
        help_text='性別を選択してください'
    )
    postal_code = models.CharField(
        max_length=7,
        verbose_name='郵便番号',
        null=True,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\d{7}$',
                message='郵便番号は7桁の数字で入力してください（ハイフンなし）'
            )
        ],
        help_text='郵便番号を7桁の数字で入力してください（ハイフンなし）'
    )
    address1 = models.CharField(
        max_length=100,
        verbose_name='都道府県',
        null=True,
        blank=True,
        help_text='都道府県を入力してください'
    )
    address2 = models.CharField(
        max_length=100,
        verbose_name='市区町村',
        null=True,
        blank=True,
        help_text='市区町村を入力してください'
    )
    address3 = models.CharField(
        max_length=200,
        verbose_name='番地・建物名',
        null=True,
        blank=True,
        help_text='番地・建物名を入力してください'
    )
    phone = models.CharField(
        max_length=15,
        verbose_name='電話番号',
        null=True,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^[\d\-]+$',
                message='電話番号は数字とハイフンのみ入力可能です'
            )
        ],
        help_text='電話番号を入力してください'
    )
    email = models.EmailField(
        verbose_name='メールアドレス',
        help_text='メールアドレス（ログインユーザーと同じ）'
    )
    

    
    class Meta:
        verbose_name = 'スタッフプロフィール'
        verbose_name_plural = 'スタッフプロフィール'
        db_table = 'apps_profile_staff'
    
    def __str__(self):
        return f"{self.name_last} {self.name_first}"
    
    @property
    def full_name(self):
        """フルネームを返す"""
        return f"{self.name_last} {self.name_first}"
    
    @property
    def full_name_kana(self):
        """フルネーム（カナ）を返す"""
        return f"{self.name_kana_last} {self.name_kana_first}"
    
    @property
    def full_address(self):
        """完全な住所を返す"""
        address_parts = [self.address1, self.address2, self.address3]
        return ''.join([part for part in address_parts if part])
    
    @property
    def sex_display(self):
        """性別の表示名を返す"""
        if not self.sex:
            return ''
        
        from apps.system.settings.models import Dropdowns
        try:
            dropdown = Dropdowns.objects.get(category='sex', value=self.sex, active=True)
            return dropdown.name
        except Dropdowns.DoesNotExist:
            return self.sex

    def __init__(self, *args, **kwargs):
        """新規インスタンス作成時にユーザーの姓・名で初期化する"""
        super().__init__(*args, **kwargs)
        # 新規作成（DB上にまだ存在しない）かつ user が指定されている場合に初期化
        try:
            if not getattr(self, 'pk', None) and getattr(self, 'user', None):
                user_obj = None
                # user がモデルインスタンスか主キーかを判定
                if isinstance(self.user, User):
                    user_obj = self.user
                else:
                    # user に主キーが入っている場合は取得を試みる
                    user_obj = User.objects.filter(pk=self.user).first()

                if user_obj:
                    if not self.name_last and getattr(user_obj, 'last_name', ''):
                        self.name_last = user_obj.last_name
                    if not self.name_first and getattr(user_obj, 'first_name', ''):
                        self.name_first = user_obj.first_name
        except Exception:
            # 初期化で失敗しても落とさない
            pass

    def save(self, *args, **kwargs):
        # ユーザーのメールアドレスと同期
        if self.user:
            self.email = self.user.email
            # プロフィールの姓・名をDjangoのUserモデルに上書きして保存
            try:
                # self.user がインスタンスでない場合は取得
                if not isinstance(self.user, User):
                    user_obj = User.objects.filter(pk=self.user).first()
                else:
                    user_obj = self.user

                if user_obj:
                    updated = False
                    if (user_obj.first_name or '') != (self.name_first or ''):
                        user_obj.first_name = self.name_first or ''
                        updated = True
                    if (user_obj.last_name or '') != (self.name_last or ''):
                        user_obj.last_name = self.name_last or ''
                        updated = True
                    if updated:
                        # 名前のみ更新する
                        user_obj.save(update_fields=['first_name', 'last_name'])
            except Exception:
                # 同期処理で失敗してもプロフィール保存は続ける
                pass

        super().save(*args, **kwargs)


class StaffProfileQualification(MyModel):
    """
    スタッフが保有する資格情報を管理するモデル。
    StaffProfileとQualificationマスターを紐付ける。
    """
    staff_profile = models.ForeignKey(
        'profile.StaffProfile',
        on_delete=models.CASCADE,
        related_name='qualifications',
        verbose_name='スタッフプロフィール'
    )
    qualification = models.ForeignKey(
        'master.Qualification',
        on_delete=models.CASCADE,
        verbose_name='資格'
    )
    acquired_date = models.DateField('取得日', blank=True, null=True)
    expiry_date = models.DateField('有効期限', blank=True, null=True)
    certificate_number = models.CharField('証明書番号', max_length=100, blank=True, null=True)
    memo = models.TextField('メモ', blank=True, null=True)
    score = models.IntegerField('点数', blank=True, null=True, help_text='TOEICの点数など')

    class Meta:
        db_table = 'apps_profile_staff_qualification'
        verbose_name = 'プロフィールスタッフ資格'
        verbose_name_plural = 'プロフィールスタッフ資格'
        unique_together = ['staff_profile', 'qualification']
        ordering = ['-acquired_date']

    def __str__(self):
        return f"{self.staff_profile} - {self.qualification}"


def profile_files_path(instance, filename):
    """
    プロフィールの添付ファイルのアップロード先パスを生成する。
    MEDIA_ROOT/profile-files/<user_id>/<filename>
    """
    return f'profile-files/{instance.user.id}/{filename}'


class StaffProfileSkill(MyModel):
    """
    スタッフが保有する技能（スキル）情報を管理するモデル。
    StaffProfileとSkillマスターを紐付ける。
    """
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

class StaffProfileMynumber(MyModel):
    """
    スタッフのマイナンバー情報を管理するモデル。
    Userモデルと1対1で連携し、暗号化して保存することを想定（要追加実装）。
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        verbose_name='ユーザー',
        related_name='staff_mynumber'
    )
    email = models.EmailField(
        verbose_name='メールアドレス',
        help_text='メールアドレス（ログインユーザーと同じ）'
    )
    mynumber = models.CharField(
        max_length=12,
        verbose_name='マイナンバー',
        validators=[
            validate_mynumber,
            RegexValidator(
                regex=r'^\d{12}$',
                message='マイナンバーは12桁の数字で入力してください'
            )
        ],
        help_text='マイナンバーを12桁の数字で入力してください'
    )

    # 添付ファイル
    mynumber_card_front = models.ImageField(
        'マイナンバーカード表面',
        upload_to=profile_files_path,
        blank=True,
        null=True,
    )
    mynumber_card_back = models.ImageField(
        'マイナンバーカード裏面',
        upload_to=profile_files_path,
        blank=True,
        null=True,
    )
    identity_document_1 = models.ImageField(
        '本人確認書類１',
        upload_to=profile_files_path,
        blank=True,
        null=True,
    )
    identity_document_2 = models.ImageField(
        '本人確認書類２',
        upload_to=profile_files_path,
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = 'スタッフマイナンバー'
        verbose_name_plural = 'スタッフマイナンバー'
        db_table = 'apps_profile_staff_mynumber'
    
    def __str__(self):
        return f"{self.user.username} - マイナンバー"
    
    def save(self, *args, **kwargs):
        # ユーザーのメールアドレスと同期
        if self.user:
            self.email = self.user.email
        super().save(*args, **kwargs)


class StaffProfileInternational(MyModel):
    """
    スタッフの外国籍情報を管理するモデル。
    Userモデルと1対1で連携し、在留カード情報を保存する。
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        verbose_name='ユーザー',
        related_name='staff_international'
    )
    email = models.EmailField(
        verbose_name='メールアドレス',
        help_text='メールアドレス（ログインユーザーと同じ）',
        default=''
    )
    residence_card_number = models.CharField(
        max_length=20,
        verbose_name='在留カード番号',
        help_text='在留カード番号を入力してください'
    )
    residence_status = models.CharField(
        max_length=100,
        verbose_name='在留資格',
        help_text='在留資格を入力してください'
    )
    residence_period_from = models.DateField(
        verbose_name='在留許可開始日',
        help_text='在留許可の開始日を入力してください'
    )
    residence_period_to = models.DateField(
        verbose_name='在留期限',
        help_text='在留期間の終了日（在留期限）を入力してください'
    )
    residence_card_front = models.FileField(
        verbose_name='在留カード（表面）',
        upload_to=residence_card_path,
        blank=True,
        null=True,
    )
    residence_card_back = models.FileField(
        verbose_name='在留カード（裏面）',
        upload_to=residence_card_path,
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = 'スタッフ外国籍情報'
        verbose_name_plural = 'スタッフ外国籍情報'
        db_table = 'apps_profile_staff_international'

    def __str__(self):
        return f"{self.user.username} - 外国籍情報"
    
    def save(self, *args, **kwargs):
        # ユーザーのメールアドレスと同期
        if self.user:
            self.email = self.user.email
        super().save(*args, **kwargs)



class StaffProfileBank(MyModel):
    """
    スタッフの銀行プロフィール情報を管理するモデル。
    Userと1対1で連携し、振込先銀行情報を保存する。
    """

    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        verbose_name='ユーザー',
        related_name='staff_bank'
    )

    bank_code = models.CharField(
        max_length=4,
        verbose_name='銀行コード',
        help_text='4桁の数字で入力',
        validators=[
            RegexValidator(
                regex=r'^\d{4}$',
                message='銀行コードは4桁の数字で入力してください'
            )
        ]
    )
    branch_code = models.CharField(
        max_length=3,
        verbose_name='支店コード',
        help_text='3桁の数字で入力',
        validators=[
            RegexValidator(
                regex=r'^\d{3}$',
                message='支店コードは3桁の数字で入力してください'
            )
        ]
    )
    account_type = models.CharField(
        max_length=10,
        verbose_name='口座種別',
        help_text='普通、当座など'
    )
    account_number = models.CharField(
        max_length=8,
        verbose_name='口座番号',
        help_text='1-8桁の数字で入力',
        validators=[
            RegexValidator(
                regex=r'^\d{1,8}$',
                message='口座番号は1-8桁の数字で入力してください'
            )
        ]
    )
    account_holder = models.CharField(
        max_length=100,
        verbose_name='口座名義',
        help_text='口座名義人の名前'
    )

    class Meta:
        verbose_name = 'スタッフ銀行プロフィール'
        verbose_name_plural = 'スタッフ銀行プロフィール'
        db_table = 'apps_profile_staff_bank'

    def __str__(self):
        return f"{self.user.username} - 銀行情報"

    @property
    def bank_name(self):
        """銀行名を取得"""
        if not self.bank_code:
            return ''
        try:
            from apps.master.models import Bank
            bank = Bank.objects.get(bank_code=self.bank_code, is_active=True)
            return bank.name
        except Bank.DoesNotExist:
            return f'銀行コード: {self.bank_code}'

    @property
    def branch_name(self):
        """支店名を取得"""
        if not self.bank_code or not self.branch_code:
            return ''
        try:
            from apps.master.models import Bank, BankBranch
            bank = Bank.objects.get(bank_code=self.bank_code, is_active=True)
            branch = BankBranch.objects.get(bank=bank, branch_code=self.branch_code, is_active=True)
            return branch.name
        except (Bank.DoesNotExist, BankBranch.DoesNotExist):
            return f'支店コード: {self.branch_code}'

    @property
    def get_account_type_display(self):
        """口座種別の表示名を取得"""
        if not self.account_type:
            return ''
        try:
            from apps.system.settings.models import Dropdowns
            dropdown = Dropdowns.objects.get(category='bank_account_type', value=self.account_type, active=True)
            return dropdown.name
        except Dropdowns.DoesNotExist:
            return self.account_type

    @property
    def full_bank_info(self):
        """完全な銀行情報"""
        parts = []
        if self.bank_name:
            parts.append(self.bank_name)
        if self.branch_name:
            parts.append(self.branch_name)
        if parts:
            return ' '.join(parts)
        return '銀行情報なし'


class StaffProfileDisability(MyModel):
    """
    スタッフの障害者情報を管理するモデル。
    Userモデルと1対1で連携する。
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        verbose_name='ユーザー',
        related_name='staff_disability'
    )
    email = models.EmailField(
        verbose_name='メールアドレス',
        help_text='メールアドレス（ログインユーザーと同じ）',
        default=''
    )
    disability_type = models.CharField(
        max_length=100,
        verbose_name='障害の種類',
        blank=True,
        null=True,
    )
    disability_grade = models.CharField(
        max_length=50,
        verbose_name='等級',
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = 'スタッフ障害者情報'
        verbose_name_plural = 'スタッフ障害者情報'
        db_table = 'apps_profile_staff_disability'

    def __str__(self):
        return f"{self.user.username} - 障害者情報"

    def save(self, *args, **kwargs):
        # ユーザーのメールアドレスと同期
        if self.user:
            self.email = self.user.email
        super().save(*args, **kwargs)

    @property
    def disability_type_display(self):
        """障害の種類の表示名を取得"""
        if not self.disability_type:
            return ''

        from apps.system.settings.models import Dropdowns
        try:
            dropdown = Dropdowns.objects.get(category='disability_type', value=self.disability_type, active=True)
            return dropdown.name
        except Dropdowns.DoesNotExist:
            return self.disability_type


class StaffProfileContact(MyModel):
    """
    スタッフ連絡先情報プロフィール
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="staff_contact",
        verbose_name="ユーザー",
    )
    emergency_contact = models.CharField('緊急連絡先', max_length=100, blank=True, null=True)
    relationship = models.CharField('続柄', max_length=100, blank=True, null=True)
    postal_code = models.CharField('郵便番号（住民票）', max_length=7, blank=True, null=True)
    address1 = models.TextField('住所１（住民票）', blank=True, null=True)
    address2 = models.TextField('住所２（住民票）', blank=True, null=True)
    address3 = models.TextField('住所３（住民票）', blank=True, null=True)

    created_by = CurrentUserField(verbose_name="作成者", related_name="created_staff_contact_set", on_delete=models.SET_NULL, null=True, blank=True)
    updated_by = CurrentUserField(verbose_name="更新者", related_name="updated_staff_contact_set", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "apps_profile_staff_contacts"
        verbose_name = "スタッフ連絡先情報プロフィール"
        verbose_name_plural = "スタッフ連絡先情報プロフィール"

    def __str__(self):
        return f"{self.user.username}"
