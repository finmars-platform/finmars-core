# Generated by Django 4.1.3 on 2023-05-05 13:15

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_alter_invitetomasteruser_unique_together_and_more'),
        ('iam', '0002_alter_group_configuration_code_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='memberaccesspolicy',
            name='member',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='iam_access_policies', to='users.member', verbose_name='Member'),
        ),
    ]
