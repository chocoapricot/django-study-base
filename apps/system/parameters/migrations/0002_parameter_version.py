# Generated by Django 5.2.1 on 2025-07-23 15:10

import concurrency.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('parameters', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='parameter',
            name='version',
            field=concurrency.fields.IntegerVersionField(default=0, help_text='record revision number'),
        ),
    ]
