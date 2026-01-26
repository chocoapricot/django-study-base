import json
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

class Command(BaseCommand):
    help = 'Imports group permissions from a JSON file.'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='The path to the JSON file.')

    def handle(self, *args, **options):
        json_file_path = options['json_file']

        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f'File not found: {json_file_path}'))
            return
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR(f'Invalid JSON format: {json_file_path}'))
            return

        for group_name, permissions in data.items():
            try:
                group = Group.objects.get(name=group_name)
                group.permissions.clear()

                for perm_str in permissions:
                    app_label, codename = perm_str.split('.')

                    try:
                        permission = Permission.objects.get(content_type__app_label=app_label, codename=codename)
                        group.permissions.add(permission)
                    except Permission.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f'Permission not found: {perm_str}'))

                self.stdout.write(self.style.SUCCESS(f'Successfully updated permissions for group: {group_name}'))

            except Group.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'Group not found: {group_name}'))
