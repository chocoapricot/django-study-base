from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from apps.common.models import MyModel

User = get_user_model()


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
    """スタッフプロフィールモデル"""
    
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
    sex = models.CharField(
        max_length=1,
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
    address_kana = models.CharField(
        max_length=200,
        verbose_name='住所（カナ）',
        null=True,
        blank=True,
        help_text='住所をカタカナで入力してください'
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
    
    def save(self, *args, **kwargs):
        # ユーザーのメールアドレスと同期
        if self.user:
            self.email = self.user.email
        super().save(*args, **kwargs)


class StaffMynumber(MyModel):
    """スタッフマイナンバーモデル"""
    
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