# Generated by Django 4.1.3 on 2023-03-12 13:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('celery_tasks', '0003_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='celerytask',
            name='finished_at',
            field=models.DateTimeField(db_index=True, null=True, verbose_name='finished at'),
        ),
    ]
