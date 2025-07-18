# Generated by Django 4.1.3 on 2023-05-15 13:53

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('ui', '0010_rename_transactionuserfieldmodel_complextransactionuserfield_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='instrumentuserfield',
            name='created',
            field=models.DateTimeField(auto_now_add=True, db_index=True, default=django.utils.timezone.now, verbose_name='created'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='instrumentuserfield',
            name='modified',
            field=models.DateTimeField(auto_now=True, db_index=True, verbose_name='modified'),
        ),
        migrations.AddField(
            model_name='transactionuserfield',
            name='created',
            field=models.DateTimeField(auto_now_add=True, db_index=True, default=django.utils.timezone.now, verbose_name='created'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='transactionuserfield',
            name='modified',
            field=models.DateTimeField(auto_now=True, db_index=True, verbose_name='modified'),
        ),
        migrations.AlterField(
            model_name='complextransactionuserfield',
            name='user_code',
            field=models.CharField(blank=True, max_length=1024, null=True, verbose_name='User Code'),
        ),
        migrations.AlterField(
            model_name='instrumentuserfield',
            name='user_code',
            field=models.CharField(blank=True, max_length=1024, null=True, verbose_name='User Code'),
        ),
        migrations.AlterField(
            model_name='transactionuserfield',
            name='user_code',
            field=models.CharField(blank=True, max_length=1024, null=True, verbose_name='User Code'),
        ),
    ]
