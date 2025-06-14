# Generated by Django 4.2.16 on 2025-01-21 19:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("portfolios", "0031_portfolio_client"),
    ]

    operations = [
        migrations.AddField(
            model_name="portfolioreconcilegroup",
            name="last_calculated_at",
            field=models.DateTimeField(default=None, null=True, verbose_name="last time calculation was done"),
        ),
        migrations.AddField(
            model_name="portfolioreconcilegroup",
            name="params",
            field=models.JSONField(default=dict, verbose_name="calculation & reporting parameters"),
        ),
        migrations.AddField(
            model_name="portfolioreconcilehistory",
            name="report_ttl",
            field=models.PositiveIntegerField(default=90, verbose_name="number of days until report expires"),
        ),
    ]
