# Generated by Django 4.1.3 on 2023-04-28 17:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('configuration', '0006_newmembersetupconfiguration'),
    ]

    operations = [
        migrations.AddField(
            model_name='newmembersetupconfiguration',
            name='target_configuration_is_package',
            field=models.BooleanField(default=False),
        ),
    ]
