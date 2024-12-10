from django_currentuser.db.models import CurrentUserField
from django.db import models

# Create your models here.
class MyModel(models.Model):
    created_at = models.DateTimeField('作成日時',auto_now_add=True)
    created_by = CurrentUserField(verbose_name="作成者", related_name="created_%(class)s_set")
    updated_at = models.DateTimeField('更新日時',auto_now=True)
    updated_by = CurrentUserField(verbose_name="更新者", related_name="updated_%(class)s_set")
    # version = models.IntegerField(default=0)  # バージョン番号
    
    class Meta:
        abstract = True


