# Generated by Django 4.1.3 on 2023-04-03 11:32

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0003_masteruser_journal_status"),
        ("transactions", "0010_alter_complextransaction_user_text_1_and_more"),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name="transaction",
            index_together={
                ("accounting_date", "cash_date"),
                ("master_user", "transaction_code"),
                ("master_user", "transaction_class", "accounting_date"),
            },
        ),
    ]
