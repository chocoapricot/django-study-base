import csv
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress
from django.db import transaction

User = get_user_model()

class Command(BaseCommand):
    help = 'Imports users from a CSV file. CSV format: username,password,email,last_name,first_name'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='The path to the CSV file.')

    def handle(self, *args, **options):
        csv_file_path = options['csv_file']

        try:
            with open(csv_file_path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                # Skip header row if it exists
                # next(reader, None)

                with transaction.atomic():
                    for row in reader:
                        username, password, email, last_name, first_name = row

                        if User.objects.filter(username=username).exists():
                            self.stdout.write(self.style.WARNING(f'User "{username}" already exists. Skipping.'))
                            continue

                        if User.objects.filter(email=email).exists():
                            self.stdout.write(self.style.WARNING(f'Email "{email}" already in use. Skipping.'))
                            continue

                        # Create user
                        user = User.objects.create_user(
                            username=username,
                            password=password,
                            email=email,
                            last_name=last_name,
                            first_name=first_name
                        )

                        # Create EmailAddress for allauth
                        EmailAddress.objects.create(
                            user=user,
                            email=email,
                            primary=True,
                            verified=True
                        )
                        self.stdout.write(self.style.SUCCESS(f'Successfully created user "{username}".'))

        except FileNotFoundError:
            raise CommandError(f'File "{csv_file_path}" does not exist.')
        except Exception as e:
            raise CommandError(f'An error occurred: {e}')
