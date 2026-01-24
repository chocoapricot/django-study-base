import json
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

class Command(BaseCommand):
    help = 'Exports group permissions to the format used in _sample_data/group_permissions.json'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            dest='output',
            help='Specifies the output file path.',
        )

    def handle(self, *args, **options):
        data = {}
        # Get all groups order by name for consistency
        groups = Group.objects.all().order_by('name')
        
        for group in groups:
            perms = []
            # Get permissions for the group, sorted to ensure deterministic output
            for p in group.permissions.all().select_related('content_type').order_by('content_type__app_label', 'codename'):
                perms.append(f"{p.content_type.app_label}.{p.codename}")
            
            data[group.name] = perms
        
        json_output = json.dumps(data, indent=4, ensure_ascii=False)
        
        output_file = options['output']
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(json_output)
            self.stdout.write(self.style.SUCCESS(f'Successfully exported group permissions to {output_file}'))
        else:
            self.stdout.write(json_output)
