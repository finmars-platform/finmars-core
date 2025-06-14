# Generated by Django 4.2.16 on 2025-03-04 14:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0015_alter_ecosystemdefault_managers'),
        ('system', '0005_auto_20250304_1419'),
    ]

    operations = [
        migrations.AlterField(
            model_name='whitelabelmodel',
            name='configuration_code',
            field=models.CharField(max_length=255, verbose_name='Configuration Code'),
        ),
        migrations.AlterField(
            model_name='whitelabelmodel',
            name='name',
            field=models.CharField(help_text='Human Readable Name of the object', max_length=255, verbose_name='name'),
        ),
        migrations.AlterField(
            model_name='whitelabelmodel',
            name='owner',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.member', verbose_name='owner'),
        ),
        migrations.AlterField(
            model_name='whitelabelmodel',
            name='company_name',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Company Name'),
        ),
    ]
