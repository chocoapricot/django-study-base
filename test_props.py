import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.settings')
django.setup()

from apps.staff.models import Staff

staff = Staff(name_last="Test", name_first="User")
print(f"has_international: {staff.has_international}")
print(f"has_disability: {staff.has_disability}")
