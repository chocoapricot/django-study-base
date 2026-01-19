from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress

User = get_user_model()

class Command(BaseCommand):
    help = 'Updates the first and last name and email of the superuser with username=admin'

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username='admin')
            user.first_name = '太郎'
            user.last_name = '管理者'
            user.save(update_fields=['first_name', 'last_name'])

            # Create EmailAddress for allauth
            if not EmailAddress.objects.filter(user=user, email='admin@example.com').exists():
                EmailAddress.objects.create(
                    user=user,
                    email='admin@example.com',
                    primary=True,
                    verified=True
                )
                self.stdout.write(self.style.SUCCESS('Successfully created EmailAddress.'))

            self.stdout.write(self.style.SUCCESS('Successfully updated superuser name.'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('Superuser with pk=1 does not exist.'))
