from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates an initial superuser for data loading'

    def handle(self, *args, **options):
        if not User.objects.filter(username='admin').exists():
            # Create a user with pk=1
            user = User(pk=1, username='admin', is_staff=True, is_superuser=True)
            user.set_password('password')
            user.save()
            self.stdout.write(self.style.SUCCESS('Successfully created superuser "admin" with pk=1'))
        else:
            self.stdout.write(self.style.WARNING('Superuser "admin" already exists.'))
