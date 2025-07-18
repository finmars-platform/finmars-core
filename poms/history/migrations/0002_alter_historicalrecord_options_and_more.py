# Generated by Django 4.1.3 on 2023-02-04 20:22

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('history', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='historicalrecord',
            options={'ordering': ['-created'], 'verbose_name': 'history record', 'verbose_name_plural': 'history records'},
        ),
        migrations.AlterIndexTogether(
            name='historicalrecord',
            index_together={('user_code', 'content_type')},
        ),
    ]
