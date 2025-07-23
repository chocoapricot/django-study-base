from django.db import models
from datetime import date

from ..common.models import MyModel
from concurrency.fields import IntegerVersionField

class Staff(MyModel):
    version = IntegerVersionField()
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
    regist_form_code = models.IntegerField('登録区分',blank=True, null=True)
    employee_no = models.CharField('社員番号', max_length=10, blank=True, null=True, help_text='半角英数字10文字まで')

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

    def __str__(self):
        return self.name_last + " " + self.name_first


from apps.common.models import MyModel

# スタッフ連絡履歴モデル

class StaffContacted(MyModel):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='contacted_histories', verbose_name='スタッフ')
    contacted_at = models.DateTimeField('連絡日時', auto_now_add=True)
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