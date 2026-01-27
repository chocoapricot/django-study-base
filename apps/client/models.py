from django.db import models
import uuid
import os

from ..common.models import MyTenantModel

def client_file_upload_path(instance, filename):
    """クライアントファイルのアップロードパスを生成"""
    # ファイル拡張子を取得
    ext = filename.split('.')[-1]
    # UUIDを使ってユニークなファイル名を生成
    filename = f"{uuid.uuid4()}.{ext}"
    # client_files/client_id/filename の形式で保存
    return f'client_files/{instance.client.pk}/{filename}'

class Client(MyTenantModel):
    """取引先企業（クライアント）の基本情報を管理するモデル。"""
    corporate_number=models.CharField('法人番号',max_length=13, unique=True, blank=True, null=True)
    name = models.TextField('会社名')
    name_furigana = models.TextField('会社名カナ')
    postal_code = models.CharField('郵便番号',blank=True, null=True,max_length=7)
    address_kana = models.TextField('住所カナ',blank=True, null=True)
    address = models.TextField('住所',blank=True, null=True)
    # phone = models.TextField('電話番号',blank=True, null=True)
    # email = models.CharField('E-MAIL',max_length=255, blank=True, null=True)
    
    memo = models.TextField('メモ',blank=True, null=True)
    regist_status = models.ForeignKey(
        'master.ClientRegistStatus',
        on_delete=models.SET_NULL,
        verbose_name='登録区分',
        blank=True,
        null=True
    )
    basic_contract_date = models.DateField('基本契約締結日(業務委託)', blank=True, null=True)
    basic_contract_date_haken = models.DateField('基本契約締結日(人材派遣)', blank=True, null=True)
    payment_site = models.ForeignKey(
        'master.BillPayment',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='支払いサイト'
    )

    class Meta:
        db_table = 'apps_client'  # 既存のテーブル名を指定
        verbose_name = 'クライアント'

    def __str__(self):
        return self.name

    @property
    def client_code(self):
        """クライアントコードを生成する"""
        if self.corporate_number and len(self.corporate_number) == 13 and self.corporate_number.isdigit():
            # Crockford Base32を参考に、I, L, O, Uを削除し、0-9, A-Zの文字セットを使用
            CHARS = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
            BASE = len(CHARS)
            try:
                # 法人番号の先頭1桁（チェックデジット）を除いた12桁を数値に変換
                num = int(self.corporate_number[1:])

                if num == 0:
                    return CHARS[0] * 8

                result = ""
                while num > 0:
                    num, rem = divmod(num, BASE)
                    result = CHARS[rem] + result

                # 8桁になるように先頭を0で埋める
                return result.rjust(8, CHARS[0])
            except (ValueError, TypeError):
                # 数値変換に失敗した場合は空文字を返す
                return ""
        return ""


class ClientDepartment(MyTenantModel):
    """クライアント企業内の組織（部署）情報を管理するモデル。"""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='departments', verbose_name='クライアント')
    name = models.CharField('組織名', max_length=100)
    department_code = models.CharField('組織コード', max_length=20, blank=True, null=True)
    postal_code = models.CharField('郵便番号', max_length=7, blank=True, null=True)
    address = models.CharField('住所', max_length=500, blank=True, null=True)
    phone_number = models.CharField('電話番号', max_length=20, blank=True, null=True)
    is_haken_office = models.BooleanField('派遣事業所該当', default=False)
    is_haken_unit = models.BooleanField('派遣組織単位該当', default=False)
    haken_unit_manager_title = models.CharField('派遣組織単位長役職', max_length=100, blank=True, null=True)
    haken_jigyosho_teishokubi = models.DateField('派遣事業所抵触日', blank=True, null=True)
    haken_jigyosho_teishokubi_notice_date = models.DateField('事業所抵触日通知日', blank=True, null=True)
    commander = models.ForeignKey(
        'ClientUser',
        on_delete=models.SET_NULL,
        related_name='commander_departments',
        verbose_name='派遣先指揮命令者',
        blank=True,
        null=True
    )
    complaint_officer = models.ForeignKey(
        'ClientUser',
        on_delete=models.SET_NULL,
        related_name='complaint_officer_departments',
        verbose_name='派遣先苦情申出先',
        blank=True,
        null=True
    )
    responsible_person = models.ForeignKey(
        'ClientUser',
        on_delete=models.SET_NULL,
        related_name='responsible_person_departments',
        verbose_name='派遣先責任者',
        blank=True,
        null=True
    )
    display_order = models.PositiveIntegerField('表示順', default=0)
    # 有効期間フィールドを追加
    valid_from = models.DateField('有効期限開始日', blank=True, null=True, help_text='未入力の場合は無期限')
    valid_to = models.DateField('有効期限終了日', blank=True, null=True, help_text='未入力の場合は無期限')

    class Meta:
        db_table = 'apps_client_department'
        verbose_name = 'クライアント組織'
        verbose_name_plural = 'クライアント組織'
        ordering = ['display_order', 'name']

    def clean(self):
        """有効期間と事業所抵触日の妥当性チェック"""
        super().clean()
        from django.core.exceptions import ValidationError
        
        # 開始日と終了日の妥当性チェック
        if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
            raise ValidationError('有効期限開始日は終了日より前の日付を入力してください。')
        
        # 事業所抵触日通知日のバリデーション
        if self.haken_jigyosho_teishokubi_notice_date and not self.haken_jigyosho_teishokubi:
            raise ValidationError('事業所抵触日通知日を入力する場合は、事業所抵触日も入力してください。')

    def is_valid_on_date(self, date=None):
        """指定日時点で有効かどうかを判定"""
        from django.utils import timezone
        if date is None:
            date = timezone.localdate()
        
        # 開始日チェック
        if self.valid_from and date < self.valid_from:
            return False
        
        # 終了日チェック
        if self.valid_to and date > self.valid_to:
            return False
        
        return True

    def __str__(self):
        period_str = ""
        if self.valid_from or self.valid_to:
            start = self.valid_from.strftime('%Y/%m/%d') if self.valid_from else '無期限'
            end = self.valid_to.strftime('%Y/%m/%d') if self.valid_to else '無期限'
            period_str = f" ({start}～{end})"
        return f"{self.client.name} - {self.name}{period_str}"


class ClientUser(MyTenantModel):
    """クライアント企業の担当者情報を管理するモデル。"""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='users', verbose_name='クライアント')
    department = models.ForeignKey(ClientDepartment, on_delete=models.SET_NULL, blank=True, null=True, related_name='users', verbose_name='所属組織')
    name_last = models.CharField('姓', max_length=50)
    name_first = models.CharField('名', max_length=50)
    name_kana_last = models.CharField('姓カナ', max_length=50, blank=True, null=True)
    name_kana_first = models.CharField('名カナ', max_length=50, blank=True, null=True)
    position = models.CharField('役職', max_length=50, blank=True, null=True)
    phone_number = models.CharField('電話番号', max_length=20, blank=True, null=True)
    email = models.EmailField('メールアドレス', blank=True, null=True)
    memo = models.TextField('メモ', blank=True, null=True)
    display_order = models.PositiveIntegerField('表示順', default=0)

    class Meta:
        db_table = 'apps_client_user'
        verbose_name = 'クライアント担当者'
        verbose_name_plural = 'クライアント担当者'
        ordering = ['display_order', 'name_last', 'name_first']

    @property
    def name(self):
        return f"{self.name_last} {self.name_first}"

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()
        super().save(*args, **kwargs)

    def __str__(self):
        parts = []
        if self.department:
            parts.append(self.department.name)
        if self.position:
            parts.append(self.position)
        parts.append(self.name)
        return ' - '.join(parts)


class ClientContacted(MyTenantModel):
    """クライアント企業への連絡履歴を管理するモデル。"""
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='contacted_histories', verbose_name='クライアント')
    department = models.ForeignKey(ClientDepartment, on_delete=models.SET_NULL, blank=True, null=True, related_name='contacted_histories', verbose_name='組織')
    user = models.ForeignKey(ClientUser, on_delete=models.SET_NULL, blank=True, null=True, related_name='contacted_histories', verbose_name='担当者')
    contacted_at = models.DateTimeField('連絡日時')
    content = models.CharField('対応内容', max_length=255, blank=False, null=False)
    detail = models.TextField('対応詳細', blank=True, null=True)
    contact_type = models.IntegerField('連絡種別', blank=True, null=True)

    class Meta:
        db_table = 'apps_client_contacted'
        verbose_name = 'クライアント連絡履歴'
        verbose_name_plural = 'クライアント連絡履歴'
        ordering = ['-contacted_at']

    def __str__(self):
        return f"{self.client} {self.contacted_at:%Y-%m-%d %H:%M} {self.content[:20]}"


class ClientContactSchedule(MyTenantModel):
    """
    クライアント企業への連絡予定を管理するモデル。
    """
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='contact_schedules', verbose_name='クライアント')
    department = models.ForeignKey(ClientDepartment, on_delete=models.SET_NULL, blank=True, null=True, related_name='contact_schedules', verbose_name='組織')
    user = models.ForeignKey(ClientUser, on_delete=models.SET_NULL, blank=True, null=True, related_name='contact_schedules', verbose_name='担当者')
    contact_date = models.DateField('連絡日')
    content = models.CharField('対応内容', max_length=255, blank=False, null=False)
    detail = models.TextField('対応詳細', blank=True, null=True)
    contact_type = models.IntegerField('連絡種別', blank=True, null=True)

    class Meta:
        db_table = 'apps_client_contact_schedule'
        verbose_name = 'クライアント連絡予定'
        verbose_name_plural = 'クライアント連絡予定'
        ordering = ['-contact_date']

    def __str__(self):
        return f"{self.client} {self.contact_date:%Y-%m-%d} {self.content[:20]}"


class ClientFile(MyTenantModel):
    """クライアントに関連する添付ファイルを管理するモデル。"""
    client = models.ForeignKey(
        Client, 
        on_delete=models.CASCADE, 
        related_name='files',
        verbose_name='クライアント'
    )
    file = models.FileField(
        'ファイル',
        upload_to=client_file_upload_path,
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
        db_table = 'apps_client_file'
        verbose_name = 'クライアントファイル'
        verbose_name_plural = 'クライアントファイル'
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['client']),
            models.Index(fields=['uploaded_at']),
        ]
    
    def save(self, *args, **kwargs):
        # 元ファイル名とファイルサイズを自動設定
        if self.file:
            self.original_filename = self.file.name
            self.file_size = self.file.size
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.client} - {self.original_filename}"
    
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