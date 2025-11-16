from django.db import migrations


def add_menu_items(apps, schema_editor):
    """勤怠管理メニューを追加"""
    Menu = apps.get_model('settings', 'Menu')
    
    # 親メニュー（勤怠管理）を作成
    parent_menu, created = Menu.objects.get_or_create(
        name='勤怠管理',
        defaults={
            'url': '/kintai/',
            'icon': 'bi-clock-history',
            'icon_style': '',
            'parent': None,
            'level': 0,
            'exact_match': False,
            'required_permission': 'kintai.view_stafftimesheet',
            'disp_seq': 70,
            'active': True,
        }
    )
    
    # 子メニュー（月次勤怠一覧）を作成
    Menu.objects.get_or_create(
        name='月次勤怠一覧',
        parent=parent_menu,
        defaults={
            'url': '/kintai/timesheet/',
            'icon': 'bi-calendar-month',
            'icon_style': '',
            'level': 1,
            'exact_match': False,
            'required_permission': 'kintai.view_stafftimesheet',
            'disp_seq': 10,
            'active': True,
        }
    )


def remove_menu_items(apps, schema_editor):
    """勤怠管理メニューを削除"""
    Menu = apps.get_model('settings', 'Menu')
    Menu.objects.filter(name__in=['勤怠管理', '月次勤怠一覧']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('kintai', '0001_initial'),
        ('settings', '__latest__'),  # settingsアプリの最新マイグレーションに依存
    ]

    operations = [
        migrations.RunPython(add_menu_items, remove_menu_items),
    ]
