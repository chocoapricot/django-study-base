# Generated by Django 5.1.2 on 2024-11-11 14:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('client', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='client',
            name='memo',
            field=models.TextField(blank=True, null=True, verbose_name='メモ'),
        ),
        migrations.AlterField(
            model_name='client',
            name='name',
            field=models.TextField(verbose_name='会社名'),
        ),
        migrations.AlterField(
            model_name='client',
            name='name_furigana',
            field=models.TextField(verbose_name='会社名カナ'),
        ),
        migrations.AlterField(
            model_name='client',
            name='url',
            field=models.TextField(blank=True, null=True, verbose_name='URL'),
        ),
    ]