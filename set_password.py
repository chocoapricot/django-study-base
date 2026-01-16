
import os
import django
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.settings')
django.setup()

from allauth.account.models import EmailAddress

User = get_user_model()
user = User.objects.get(username='admin')
user.set_password('password')
user.save()

EmailAddress.objects.create(user=user, email='admin@test.com', primary=True, verified=True)
