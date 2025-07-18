# Generated by Django 4.1.3 on 2023-05-05 13:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_alter_invitetomasteruser_unique_together_and_more'),
        ('iam', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='group',
            name='configuration_code',
            field=models.CharField(default='com.finmars.local', max_length=255, verbose_name='Configuration Code'),
        ),
        migrations.AlterField(
            model_name='memberaccesspolicy',
            name='member',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='access_policies', to='users.member', verbose_name='Member'),
        ),
        migrations.AlterField(
            model_name='role',
            name='configuration_code',
            field=models.CharField(default='com.finmars.local', max_length=255, verbose_name='Configuration Code'),
        ),
    ]
