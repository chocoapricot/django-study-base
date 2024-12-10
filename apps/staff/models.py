from django.db import models

from ..common.models import MyModel

class Staff(MyModel):
    name_last = models.CharField('名前(姓)',max_length=30,help_text='')
    name_first = models.CharField('名前(名)',max_length=30,help_text='')
    name_kana_last = models.CharField('カナ(姓)',max_length=30,help_text='')
    name_kana_first = models.CharField('カナ(名)',max_length=30,help_text='')
    name = models.TextField('名前',blank=True, null=True)
    birth_date = models.DateField('生年月日',blank=True, null=True)
    sex = models.IntegerField('性別',blank=True, null=True)
    age = models.IntegerField('年齢')
    postal_code = models.CharField('郵便番号',blank=True, null=True,max_length=7)
    address_kana = models.TextField('住所カナ',blank=True, null=True)
    address1 = models.TextField('住所１',blank=True, null=True)
    address2 = models.TextField('住所２',blank=True, null=True)
    address3 = models.TextField('住所３',blank=True, null=True)
    phone = models.TextField('電話番号',blank=True, null=True)
    email = models.CharField('E-MAIL',max_length=255, unique=True, blank=True, null=True)
    regist_form_code = models.IntegerField('登録区分',blank=True, null=True)

    class Meta:
        db_table = 'apps_staff'  # 既存のテーブル名を指定
        verbose_name = 'スタッフ'

    def save(self, *args, **kwargs):
        # 姓と名を結合して full_name に保存
        self.name = f"{self.name_last}{self.name_first}"
        super().save(*args, **kwargs)  # 親クラスの save を呼び出す

    def __str__(self):
        return self.name_last + " " + self.name_first