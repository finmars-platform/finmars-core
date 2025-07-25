# Generated by Django 4.2.3 on 2024-08-20 10:13

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('strategies', '0006_strategy1_actual_at_strategy1_deleted_at_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='strategy1',
            old_name='created',
            new_name='created_at',
        ),
        migrations.AlterField(
            model_name='strategy1',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='created at'),
        ),
        migrations.RenameField(
            model_name='strategy1',
            old_name='modified',
            new_name='modified_at',
        ),
        migrations.AlterField(
            model_name='strategy1',
            name='modified_at',
            field=models.DateTimeField(auto_now=True, db_index=True, verbose_name='modified at'),
        ),
        migrations.RenameField(
            model_name='strategy2',
            old_name='created',
            new_name='created_at',
        ),
        migrations.AlterField(
            model_name='strategy2',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='created at'),
        ),
        migrations.RenameField(
            model_name='strategy2',
            old_name='modified',
            new_name='modified_at',
        ),
        migrations.AlterField(
            model_name='strategy2',
            name='modified_at',
            field=models.DateTimeField(auto_now=True, db_index=True, verbose_name='modified at'),
        ),
        migrations.RenameField(
            model_name='strategy3',
            old_name='created',
            new_name='created_at',
        ),
        migrations.AlterField(
            model_name='strategy3',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='created at'),
        ),
        migrations.RenameField(
            model_name='strategy3',
            old_name='modified',
            new_name='modified_at',
        ),
        migrations.AlterField(
            model_name='strategy3',
            name='modified_at',
            field=models.DateTimeField(auto_now=True, db_index=True, verbose_name='modified at'),
        ),
    ]
