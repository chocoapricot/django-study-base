from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.
class MyUser(AbstractUser):
    phone_number = models.CharField('電話番号',max_length=15, blank=True, null=True,help_text='ハイフン付きで入力')
