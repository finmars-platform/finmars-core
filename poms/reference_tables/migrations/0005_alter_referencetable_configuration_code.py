# Generated by Django 4.1.3 on 2023-06-05 09:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reference_tables', '0004_alter_referencetable_unique_together'),
    ]

    operations = [
        migrations.AlterField(
            model_name='referencetable',
            name='configuration_code',
            field=models.CharField(max_length=255, verbose_name='Configuration Code'),
        ),
    ]
