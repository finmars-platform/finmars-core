# Generated by Django 4.2.8 on 2024-04-18 21:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("configuration", "0010_newmembersetupconfiguration_owner"),
    ]

    operations = [
        migrations.AddField(
            model_name="configuration",
            name="channel",
            field=models.CharField(
                choices=[["stable", "Stable"], ["rc", "Release Candidate"]],
                default="stable",
                max_length=255,
            ),
        ),
    ]
