import json
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission

class Command(BaseCommand):
    help = 'Import group permissions from a custom JSON file.'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='The path to the JSON file to import.')

    def handle(self, *args, **options):
        json_file_path = options['json_file']

        try:
            with open(json_file_path, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"File not found: {json_file_path}"))
            return
        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR(f"Invalid JSON in file: {json_file_path}"))
            return

        for group_name, permissions_list in data.items():
            try:
                group, created = Group.objects.get_or_create(name=group_name)
                if created:
                    self.stdout.write(self.style.SUCCESS(f"Created group: {group_name}"))

                permissions = []
                for perm_codename in permissions_list:
                    app_label, codename = perm_codename.split('.')
                    try:
                        permission = Permission.objects.get(content_type__app_label=app_label, codename=codename)
                        permissions.append(permission)
                    except Permission.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f"Permission not found: {perm_codename}"))

                group.permissions.set(permissions)
                self.stdout.write(self.style.SUCCESS(f"Successfully assigned {len(permissions)} permissions to group '{group_name}'"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing group {group_name}: {e}"))
