import csv
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress
from django.db import transaction
from apps.connect.utils import (
    grant_profile_permissions,
    grant_staff_contract_confirmation_permission,
    grant_client_contract_confirmation_permission
)

User = get_user_model()

class Command(BaseCommand):
    help = 'Imports users from a CSV file. CSV format: username,password,email,last_name,first_name,user_type'

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
                        # 空行や不完全な行をスキップ
                        if not row or len(row) < 5:
                            continue
                        
                        # 空白のみの行をスキップ
                        if all(not cell.strip() for cell in row):
                            continue
                        
                        # 後方互換性のため、5列または6列に対応
                        username = row[0]
                        password = row[1]
                        email = row[2]
                        last_name = row[3]
                        first_name = row[4]
                        user_type = row[5].strip().lower() if len(row) > 5 else ''

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
                        
                        # user_typeに応じて権限を付与
                        if user_type == 'staff':
                            # スタッフ接続承認時と同じ権限を付与
                            grant_profile_permissions(user)
                            grant_staff_contract_confirmation_permission(user)
                            self.stdout.write(self.style.SUCCESS(f'Successfully created staff user "{username}" with permissions.'))
                        elif user_type == 'client':
                            # クライアント接続承認時と同じ権限を付与
                            grant_client_contract_confirmation_permission(user)
                            self.stdout.write(self.style.SUCCESS(f'Successfully created client user "{username}" with permissions.'))
                        else:
                            # 管理者または権限付与不要なユーザー
                            self.stdout.write(self.style.SUCCESS(f'Successfully created user "{username}".'))

        except FileNotFoundError:
            raise CommandError(f'File "{csv_file_path}" does not exist.')
        except Exception as e:
            raise CommandError(f'An error occurred: {e}')
