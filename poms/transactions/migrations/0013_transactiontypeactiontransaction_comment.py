# Generated by Django 4.1.3 on 2023-04-05 07:40

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("transactions", "0012_transaction_comment"),
    ]

    operations = [
        migrations.AddField(
            model_name="transactiontypeactiontransaction",
            name="comment",
            field=models.CharField(
                blank=True, default="", max_length=4096, verbose_name="comment"
            ),
        ),
    ]
