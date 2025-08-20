from django.db import models
from datetime import date
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError

from ..common.models import MyModel
from concurrency.fields import IntegerVersionField

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

class Staff(MyModel):
    """
    スタッフ（従業員、契約社員など）の基本情報を管理するモデル。
    個人情報、連絡先、社内情報（社員番号、所属部署など）を保持する。
    """
    name_last = models.CharField('名前(姓)',max_length=30,help_text='')
    name_first = models.CharField('名前(名)',max_length=30,help_text='')
    name_kana_last = models.CharField('カナ(姓)',max_length=30,help_text='')
    name_kana_first = models.CharField('カナ(名)',max_length=30,help_text='')
    name = models.TextField('名前',blank=True, null=True)
    birth_date = models.DateField('生年月日',blank=True, null=True)
    sex = models.IntegerField('性別',blank=True, null=True)
    age = models.PositiveIntegerField('年齢', default=0)
    postal_code = models.CharField('郵便番号',blank=True, null=True,max_length=7)
    address_kana = models.TextField('住所カナ',blank=True, null=True)
    address1 = models.TextField('住所１',blank=True, null=True)
    address2 = models.TextField('住所２',blank=True, null=True)
    address3 = models.TextField('住所３',blank=True, null=True)
    phone = models.TextField('電話番号',blank=True, null=True)
    email = models.CharField('E-MAIL',max_length=255, unique=True, blank=True, null=True)
    regist_form_code = models.IntegerField('登録区分', blank=True, null=True)
    employment_type = models.CharField('雇用形態', max_length=10, blank=True, null=True, help_text='dropdowns employment_type')
    employee_no = models.CharField('社員番号', max_length=10, blank=True, null=True, help_text='半角英数字10文字まで')
    # 入社・退職・所属情報
    hire_date = models.DateField('入社日', blank=True, null=True)
    resignation_date = models.DateField('退職日', blank=True, null=True)
    department_code = models.CharField('所属部署コード', max_length=20, blank=True, null=True, help_text='会社部署の部署コードを参照')
    memo = models.TextField('メモ', blank=True, null=True)

    class Meta:
        db_table = 'apps_staff'  # 既存のテーブル名を指定
        verbose_name = 'スタッフ'

    def save(self, *args, **kwargs):
        # 姓と名を結合して full_name に保存
        self.name = f"{self.name_last}{self.name_first}"
        # 年齢を計算して保存
        if self.birth_date:
            today = date.today()
            self.age = today.year - self.birth_date.year - (
                (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
            )
        super().save(*args, **kwargs)  # 親クラスの save を呼び出す

    def get_department_name(self, date=None):
        """指定日時点での所属部署名を取得"""
        if not self.department_code:
            return None
        
        from apps.company.models import CompanyDepartment
        from django.utils import timezone
        
        if date is None:
            date = timezone.now().date()
        
        try:
            # 指定日時点で有効な部署を取得
            department = CompanyDepartment.objects.filter(
                department_code=self.department_code
            ).filter(
                models.Q(valid_from__isnull=True) | models.Q(valid_from__lte=date)
            ).filter(
                models.Q(valid_to__isnull=True) | models.Q(valid_to__gte=date)
            ).first()
            
            return department.name if department else f"{self.department_code} (無効)"
        except Exception:
            return f"部署コード: {self.department_code} (エラー)"
    
    def get_current_department_name(self):
        """現在の所属部署名を取得"""
        return self.get_department_name()
    
    def is_active_employee(self, date=None):
        """指定日時点で在職中かどうかを判定"""
        from django.utils import timezone
        
        if date is None:
            date = timezone.now().date()
        
        # 入社日チェック
        if self.hire_date and date < self.hire_date:
            return False
        
        # 退職日チェック
        if self.resignation_date and date > self.resignation_date:
            return False
        
        return True
    
    def get_employment_status(self, date=None):
        """指定日時点での雇用状況を取得"""
        from django.utils import timezone
        
        if date is None:
            date = timezone.now().date()
        
        if not self.hire_date:
            return "入社日未設定"
        
        if date < self.hire_date:
            return "入社前"
        
        if self.resignation_date:
            if date > self.resignation_date:
                return "退職済み"
            elif date == self.resignation_date:
                return "退職日"
        
        return "在職中"

    def __str__(self):
        return self.name_last + " " + self.name_first

    @property
    def has_mynumber(self):
        """マイナンバーが登録されているかどうかを返す"""
        return hasattr(self, 'mynumber')


from apps.common.models import MyModel
import uuid
import os

def staff_file_upload_path(instance, filename):
    """スタッフファイルのアップロードパスを生成"""
    # ファイル拡張子を取得
    ext = filename.split('.')[-1]
    # UUIDを使ってユニークなファイル名を生成
    filename = f"{uuid.uuid4()}.{ext}"
    # staff_files/staff_id/filename の形式で保存
    return f'staff_files/{instance.staff.pk}/{filename}'

class StaffFile(MyModel):
    """
    スタッフに関連する添付ファイルを管理するモデル。
    履歴書や職務経歴書などのドキュメントを想定。
    """
    
    staff = models.ForeignKey(
        Staff, 
        on_delete=models.CASCADE, 
        related_name='files',
        verbose_name='スタッフ'
    )
    file = models.FileField(
        'ファイル',
        upload_to=staff_file_upload_path,
        help_text='添付ファイル（最大10MB）'
    )
    original_filename = models.CharField(
        '元ファイル名',
        max_length=255,
        help_text='アップロード時の元のファイル名'
    )
    file_size = models.PositiveIntegerField(
        'ファイルサイズ',
        help_text='バイト単位'
    )
    description = models.CharField(
        '説明',
        max_length=255,
        blank=True,
        null=True,
        help_text='ファイルの説明（任意）'
    )
    uploaded_at = models.DateTimeField(
        'アップロード日時',
        auto_now_add=True
    )
    
    class Meta:
        db_table = 'apps_staff_file'
        verbose_name = 'スタッフファイル'
        verbose_name_plural = 'スタッフファイル'
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['staff']),
            models.Index(fields=['uploaded_at']),
        ]
    
    def save(self, *args, **kwargs):
        # 元ファイル名とファイルサイズを自動設定
        if self.file:
            self.original_filename = self.file.name
            self.file_size = self.file.size
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.staff} - {self.original_filename}"
    
    @property
    def file_extension(self):
        """ファイル拡張子を取得"""
        return os.path.splitext(self.original_filename)[1].lower()
    
    @property
    def is_image(self):
        """画像ファイルかどうか判定"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        return self.file_extension in image_extensions
    
    @property
    def is_document(self):
        """ドキュメントファイルかどうか判定"""
        doc_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt']
        return self.file_extension in doc_extensions
    
    @property
    def file_size_mb(self):
        """ファイルサイズをMB単位で取得"""
        return round(self.file_size / (1024 * 1024), 2)

class StaffContacted(MyModel):
    """
    スタッフへの連絡履歴を管理するモデル。
    面談や電話、メールなどのやり取りを記録する。
    """
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='contacted_histories', verbose_name='スタッフ')
    contacted_at = models.DateTimeField('連絡日時')
    content = models.CharField('対応内容', max_length=255, blank=False, null=False)
    detail = models.TextField('対応詳細', blank=True, null=True)
    contact_type = models.IntegerField('連絡種別', blank=True, null=True)

    class Meta:
        db_table = 'apps_staff_contacted'
        verbose_name = 'スタッフ連絡履歴'
        verbose_name_plural = 'スタッフ連絡履歴'
        ordering = ['-contacted_at']

    def __str__(self):
        return f"{self.staff} {self.contacted_at:%Y-%m-%d %H:%M} {self.content[:20]}"


class StaffQualification(MyModel):
    """
    スタッフが保有する資格情報を管理するモデル。
    StaffモデルとQualificationマスターを紐付ける中間テーブル。
    """
    
    staff = models.ForeignKey(
        Staff, 
        on_delete=models.CASCADE, 
        related_name='qualifications',
        verbose_name='スタッフ'
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
        db_table = 'apps_staff_qualification'
        verbose_name = 'スタッフ資格'
        verbose_name_plural = 'スタッフ資格'
        unique_together = ['staff', 'qualification']
        ordering = ['-acquired_date']
        indexes = [
            models.Index(fields=['staff']),
            models.Index(fields=['qualification']),
            models.Index(fields=['acquired_date']),
            models.Index(fields=['expiry_date']),
        ]
    
    def __str__(self):
        return f"{self.staff} - {self.qualification}"
    
    @property
    def is_expired(self):
        """資格が期限切れかどうか"""
        if not self.expiry_date:
            return False
        from django.utils import timezone
        return self.expiry_date < timezone.now().date()
    
    @property
    def is_expiring_soon(self, days=30):
        """資格が間もなく期限切れかどうか（デフォルト30日以内）"""
        if not self.expiry_date:
            return False
        from django.utils import timezone
        from datetime import timedelta
        return self.expiry_date <= timezone.now().date() + timedelta(days=days)


class StaffSkill(MyModel):
    """
    スタッフが保有する技能（スキル）情報を管理するモデル。
    StaffモデルとSkillマスターを紐付ける中間テーブル。
    """
    
    staff = models.ForeignKey(
        Staff, 
        on_delete=models.CASCADE, 
        related_name='skills',
        verbose_name='スタッフ'
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
        db_table = 'apps_staff_skill'
        verbose_name = 'スタッフ技能'
        verbose_name_plural = 'スタッフ技能'
        unique_together = ['staff', 'skill']
        ordering = ['-acquired_date']
        indexes = [
            models.Index(fields=['staff']),
            models.Index(fields=['skill']),
            models.Index(fields=['acquired_date']),
        ]
    
    def __str__(self):
        return f"{self.staff} - {self.skill}"


class StaffMynumber(MyModel):
    """
    スタッフのマイナンバー情報を管理するモデル。
    Staffモデルと1対1で連携し、暗号化して保存することを想定（要追加実装）。
    """

    staff = models.OneToOneField(
        Staff,
        on_delete=models.CASCADE,
        verbose_name='スタッフ',
        related_name='mynumber'
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
        db_table = 'apps_staff_mynumber'

    def __str__(self):
        return f"{self.staff} - マイナンバー"