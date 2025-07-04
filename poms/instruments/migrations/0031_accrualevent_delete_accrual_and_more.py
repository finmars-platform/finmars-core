# Generated by Django 4.2.16 on 2025-03-16 07:08

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("instruments", "0030_accrual_accrual_calculation_model_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="AccrualEvent",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user_code", models.CharField(max_length=255, verbose_name="User code")),
                ("start_date", models.DateField(verbose_name="Accrual start date")),
                ("end_date", models.DateField(verbose_name="Accrual value date")),
                ("payment_date", models.DateField(verbose_name="Accrual payment date")),
                ("accrual_size", models.FloatField(verbose_name="Accrual size")),
                ("periodicity_n", models.IntegerField(verbose_name="Days between coupons")),
                ("notes", models.TextField(blank=True, default="", verbose_name="Notes")),
                (
                    "accrual_calculation_model",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to="instruments.accrualcalculationmodel",
                        verbose_name="Accrual calculation model",
                    ),
                ),
                (
                    "instrument",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="accrual_events",
                        to="instruments.instrument",
                        verbose_name="Instrument",
                    ),
                ),
            ],
            options={
                "verbose_name": "Accrual",
                "verbose_name_plural": "Accruals",
                "ordering": ["instrument", "end_date"],
            },
        ),
        migrations.DeleteModel(
            name="Accrual",
        ),
        migrations.AddConstraint(
            model_name="accrualevent",
            constraint=models.UniqueConstraint(
                fields=("instrument", "end_date"), name="unique_instrument_accrual_event_date"
            ),
        ),
    ]
