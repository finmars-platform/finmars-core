# Generated by Django 4.2.3 on 2023-12-13 01:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('portfolios', '0016_alter_portfoliohistory_period_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='portfolioregisterrecord',
            name='nav_previous_business_day_valuation_currency',
            field=models.FloatField(default=0.0, verbose_name='nav previous business day valuation currency'),
        ),
    ]
