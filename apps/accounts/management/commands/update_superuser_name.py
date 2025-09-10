from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Updates the first and last name of the superuser with pk=1'

    def handle(self, *args, **options):
        try:
            user = User.objects.get(pk=1)
            user.first_name = '太郎'
            user.last_name = '管理者'
            user.save(update_fields=['first_name', 'last_name'])
            self.stdout.write(self.style.SUCCESS('Successfully updated superuser name.'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('Superuser with pk=1 does not exist.'))
