# Generated by Django 4.1.3 on 2022-12-07 21:11

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='EcosystemConfiguration',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, db_index=True, default='', max_length=255, verbose_name='name')),
                ('description', models.TextField(blank=True, null=True, verbose_name='description')),
                ('json_data', models.TextField(blank=True, null=True, verbose_name='json data')),
            ],
            options={
                'ordering': ['name'],
                'unique_together': {('name',)},
            },
        ),
    ]
