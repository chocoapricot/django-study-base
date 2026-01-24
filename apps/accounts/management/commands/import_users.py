
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from allauth.account.models import EmailAddress
import csv

User = get_user_model()

class Command(BaseCommand):
    help = 'Imports users from a CSV file.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='The CSV file to import users from.')

    def handle(self, *args, **options):
        with open(options['csv_file'], 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                user_type = None
                if len(row) == 6:
                    username, password, email, last_name, first_name, user_type = row
                else:
                    username, password, email, last_name, first_name = row

                try:
                    user, created = User.objects.get_or_create(
                        username=username,
                        defaults={
                            'password': password,
                            'email': email,
                            'first_name': first_name,
                            'last_name': last_name
                        }
                    )
                    if created:
                        user.set_password(password)
                        user.save()

                        EmailAddress.objects.create(
                            user=user,
                            email=email,
                            primary=True,
                            verified=True
                        )

                        if user_type == 'staff':
                            group = Group.objects.get(name='staff')
                            user.groups.add(group)
                            group = Group.objects.get(name='staff_connected')
                            user.groups.add(group)
                            self.stdout.write(self.style.SUCCESS(f'Successfully created staff user "{username}" and added to staff/staff_connected groups.'))
                        elif user_type == 'client':
                            group = Group.objects.get(name='client')
                            user.groups.add(group)
                            group = Group.objects.get(name='client_connected')
                            user.groups.add(group)
                            self.stdout.write(self.style.SUCCESS(f'Successfully created client user "{username}" and added to client/client_connected groups.'))
                        else:
                            self.stdout.write(self.style.SUCCESS(f'Successfully created user "{username}".'))
                    else:
                        self.stdout.write(self.style.WARNING(f'User "{username}" already exists. Skipping.'))

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error creating user "{username}": {e}'))
