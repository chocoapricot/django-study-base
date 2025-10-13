# Generated manually

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contract', '0049_staffcontract_employment_type'),
        ('master', '0034_employmenttype'),
    ]

    operations = [
        migrations.AlterField(
            model_name='staffcontract',
            name='employment_type',
            field=models.ForeignKey(blank=True, help_text='契約作成時点のスタッフの雇用形態を保存', null=True, on_delete=django.db.models.deletion.SET_NULL, to='master.employmenttype', verbose_name='雇用形態'),
        ),
    ]