# Generated by Django 4.1.3 on 2023-05-15 12:32

from django.db import migrations, models


def forwards_func(apps, schema_editor):
    # print("forwards_func")

    pass

    # from poms.reference_tables.models import ReferenceTable
    #
    # items = ReferenceTable.objects.all()
    #
    # for item in items:
    #
    #     if not item.user_code:
    #
    #         # item.configuration_code = 'com.finmars.local'
    #         from poms.configuration.utils import get_default_configuration_code
    #         item.configuration_code = get_default_configuration_code()
    #
    #         item.user_code = item.configuration_code + ':' + item.name.replace(' ', '_').lower()
    #
    #         item.save()


def reverse_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('reference_tables', '0002_referencetable_configuration_code_and_more'),
    ]



    operations = [
        migrations.RunPython(forwards_func, reverse_func),
    ]
