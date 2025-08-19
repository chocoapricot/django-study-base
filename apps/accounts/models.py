from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.
class MyUser(AbstractUser):
	"""
	標準のUserモデルを拡張したカスタムユーザーモデル。
	StaffProfileとの連携で、姓・名の同期機能を持つ。
	"""

	def save(self, *args, **kwargs):
		super().save(*args, **kwargs)
		# User保存時にStaffProfileがあればそちらも同期
		try:
			profile = getattr(self, 'staff_profile', None)
			if profile:
				updated = False
				if (profile.name_first or '') != (self.first_name or ''):
					profile.name_first = self.first_name or ''
					updated = True
				if (profile.name_last or '') != (self.last_name or ''):
					profile.name_last = self.last_name or ''
					updated = True
				if updated:
					profile.save(update_fields=['name_first', 'name_last'])
		except Exception:
			pass
