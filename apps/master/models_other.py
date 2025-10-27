import os
from uuid import uuid4
from django.db import models
from apps.common.models import MyModel


def information_file_path(instance, filename):
    """
    お知らせ添付ファイルのアップロードパスを生成する。
    media/information_files/<information_id>/<uuid>_<filename>
    """
    filename = os.path.basename(filename)
    return os.path.join(
        'information_files',
        str(instance.information.id),
        f"{uuid4().hex}_{filename}"
    )


class MailTemplate(MyModel):
    """
    メールテンプレートを管理するマスターデータモデル。
    """
    name = models.CharField('日本語名', max_length=255, editable=False, default='')
    template_key = models.CharField(
        'テンプレートキー',
        max_length=255,
        unique=True,
        help_text='プログラム側で識別するためのキー（例: "connect_request_new_user"）',
        editable=False
    )
    subject = models.CharField('件名', max_length=255)
    body = models.TextField('本文')
    remarks = models.TextField('備考', blank=True, null=True, help_text='このテンプレートの説明や変数のリストなど')

    class Meta:
        db_table = 'apps_master_mail_template'
        verbose_name = 'メールテンプレート'
        verbose_name_plural = 'メールテンプレート'
        ordering = ['template_key']

    def __str__(self):
        return self.name


class Information(MyModel):
    """
    お知らせ情報を管理するマスターデータモデル。
    """

    target = models.CharField(
        '対象',
        max_length=10,
        default='1',
    )
    subject = models.CharField('件名', max_length=200)
    content = models.TextField('内容')
    start_date = models.DateField('開始日', null=True, blank=True)
    end_date = models.DateField('終了日', null=True, blank=True)
    corporation_number = models.CharField('法人番号', max_length=13, blank=True, null=True)

    class Meta:
        db_table = 'apps_master_information'
        verbose_name = 'お知らせ'
        verbose_name_plural = 'お知らせ'
        ordering = ['-start_date']

    def __str__(self):
        return self.subject


class InformationFile(MyModel):
    """
    お知らせの添付ファイルを管理するモデル。
    """
    information = models.ForeignKey(
        Information,
        on_delete=models.CASCADE,
        verbose_name='お知らせ',
        related_name='files'
    )
    file = models.FileField('ファイル', upload_to=information_file_path)
    filename = models.CharField('ファイル名', max_length=255, blank=True)

    class Meta:
        db_table = 'apps_master_information_file'
        verbose_name = 'お知らせ添付ファイル'
        verbose_name_plural = 'お知らせ添付ファイル'
        ordering = ['-created_at']

    def __str__(self):
        return self.filename or str(self.file)

    def save(self, *args, **kwargs):
        if not self.filename:
            self.filename = os.path.basename(self.file.name)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # ファイルも削除
        self.file.delete(save=False)
        super().delete(*args, **kwargs)


class DefaultValue(MyModel):
    """
    システムの各項目における初期値を管理するマスターデータ。
    """
    FORMAT_CHOICES = [
        ('text', 'テキスト'),
        ('textarea', 'テキストエリア'),
        ('boolean', '真偽値'),
        ('number', '数値'),
    ]

    key = models.CharField('キー', max_length=255, primary_key=True)
    target_item = models.CharField('対象項目', max_length=255)
    format = models.CharField('形式', max_length=10, choices=FORMAT_CHOICES, default='text')
    value = models.TextField('値', blank=True)
    display_order = models.IntegerField('表示順', default=0)

    class Meta:
        db_table = 'apps_master_default_value'
        verbose_name = '初期値マスタ'
        verbose_name_plural = '初期値マスタ'
        ordering = ['display_order', 'target_item']

    def __str__(self):
        return self.target_item

    def get_boolean_value(self):
        """
        boolean形式の値をPythonのbool型で取得
        """
        if self.format == 'boolean':
            return self.value.lower() == 'true'
        return None

    def get_number_value(self):
        """
        number形式の値をPythonの数値型で取得
        """
        if self.format == 'number':
            try:
                # 小数点が含まれている場合はfloat、そうでなければint
                if '.' in self.value:
                    return float(self.value)
                else:
                    return int(self.value)
            except (ValueError, TypeError):
                return None
        return None

    def get_formatted_value(self):
        """
        形式に応じて適切にフォーマットされた値を取得
        """
        if self.format == 'boolean':
            return self.get_boolean_value()
        elif self.format == 'number':
            return self.get_number_value()
        return self.value
