# Generated by Django 4.2.8 on 2024-02-02 15:42

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("instruments", "0016_instrument_owner_instrumenttype_owner_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="pricehistory",
            name="error_message",
            field=models.TextField(default="", verbose_name="error message(s)"),
        ),
    ]
