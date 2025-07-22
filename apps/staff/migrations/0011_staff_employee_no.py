from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("staff", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="staff",
            name="employee_no",
            field=models.CharField(
                "社員番号", max_length=10, blank=True, null=True, help_text="半角英数字10文字まで"
            ),
        ),
    ]
