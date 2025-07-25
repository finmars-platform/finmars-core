# Generated by Django 4.2.3 on 2024-09-29 18:45

import django.contrib.postgres.fields
from django.db import migrations, models
import poms.iam.models


class Migration(migrations.Migration):

    dependencies = [
        ("iam", "0017_remove_accesspolicy_resource_group_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="accesspolicy",
            name="resource_groups",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=1024),
                default=poms.iam.models.default_list,
                size=None,
                verbose_name="List of ResourceGroup user_codes",
            ),
        ),
    ]
