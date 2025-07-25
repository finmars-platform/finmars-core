# Generated by Django 4.2.3 on 2024-08-20 10:13

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('csv_import', '0012_csvimportscheme_deleted_at'),
    ]

    operations = [
        migrations.RenameField(
            model_name='csvimportscheme',
            old_name='created',
            new_name='created_at',
        ),
        migrations.AlterField(
            model_name='csvimportscheme',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='created at'),
        ),
        migrations.RenameField(
            model_name='csvimportscheme',
            old_name='modified',
            new_name='modified_at',
        ),
        migrations.AlterField(
            model_name='csvimportscheme',
            name='modified_at',
            field=models.DateTimeField(auto_now=True, db_index=True, verbose_name='modified at'),
        ),
    ]
