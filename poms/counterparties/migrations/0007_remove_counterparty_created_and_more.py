# Generated by Django 4.2.3 on 2024-08-20 10:13

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('counterparties', '0006_counterparty_actual_at_counterparty_deleted_at_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='counterparty',
            old_name='created',
            new_name='created_at',
        ),
        migrations.AlterField(
            model_name='counterparty',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='created at'),
        ),
        migrations.RenameField(
            model_name='counterparty',
            old_name='modified',
            new_name='modified_at',
        ),
        migrations.AlterField(
            model_name='counterparty',
            name='modified_at',
            field=models.DateTimeField(auto_now=True, db_index=True, verbose_name='modified at'),
        ),
        migrations.RenameField(
            model_name='responsible',
            old_name='created',
            new_name='created_at',
        ),
        migrations.AlterField(
            model_name='responsible',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='created at'),
        ),
        migrations.RenameField(
            model_name='responsible',
            old_name='modified',
            new_name='modified_at',
        ),
        migrations.AlterField(
            model_name='responsible',
            name='modified_at',
            field=models.DateTimeField(auto_now=True, db_index=True, verbose_name='modified at'),
        ),
    ]
