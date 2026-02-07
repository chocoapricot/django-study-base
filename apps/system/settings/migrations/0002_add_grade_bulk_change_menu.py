from django.db import migrations

def add_menu_item(apps, schema_editor):
    Menu = apps.get_model('settings', 'Menu')
    # スタッフメニュー (ID 2) を取得
    try:
        staff_menu = Menu.objects.get(pk=2)
        Menu.objects.create(
            name='スタッフ等級一括変更',
            url='/staff/grade/bulk_change/',
            icon='bi-person-gear',
            icon_style='',
            parent=staff_menu,
            level=1,
            disp_seq=100,
            required_permission='staff.add_staffgrade',
            active=True
        )
    except Menu.DoesNotExist:
        # フォールバック: トップレベルに追加
        Menu.objects.create(
            name='スタッフ等級一括変更',
            url='/staff/grade/bulk_change/',
            icon='bi-person-gear',
            icon_style='',
            level=0,
            disp_seq=100,
            required_permission='staff.add_staffgrade',
            active=True
        )

def remove_menu_item(apps, schema_editor):
    Menu = apps.get_model('settings', 'Menu')
    Menu.objects.filter(name='スタッフ等級一括変更').delete()

class Migration(migrations.Migration):
    dependencies = [
        ('settings', '0001_initial'),
    ]
    operations = [
        migrations.RunPython(add_menu_item, remove_menu_item),
    ]
