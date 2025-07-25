# Generated by Django 4.1.3 on 2023-04-26 09:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('obj_attrs', '0004_alter_genericattributetype_user_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='genericattributetype',
            name='name',
            field=models.CharField(help_text='Human Readable Name of the object', max_length=255, verbose_name='name'),
        ),
        migrations.AlterField(
            model_name='genericattributetype',
            name='notes',
            field=models.TextField(blank=True, help_text='Notes, any useful information about the object', null=True, verbose_name='notes'),
        ),
        migrations.AlterField(
            model_name='genericattributetype',
            name='public_name',
            field=models.CharField(blank=True, help_text='Used if user does not have permissions to view object', max_length=255, null=True, verbose_name='public name'),
        ),
        migrations.AlterField(
            model_name='genericattributetype',
            name='short_name',
            field=models.TextField(blank=True, help_text='Short Name of the object. Used in dropdown menus', null=True, verbose_name='short name'),
        ),
        migrations.AlterField(
            model_name='genericattributetype',
            name='user_code',
            field=models.CharField(blank=True, help_text='Unique Code for this object. Used in Configuration and Permissions Logic', max_length=1024, null=True, verbose_name='user code'),
        ),
    ]
