# Generated by Django 4.1.3 on 2023-04-26 09:34

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("currencies", "0005_alter_currency_user_code"),
    ]

    operations = [
        migrations.AlterField(
            model_name="currency",
            name="deleted_user_code",
            field=models.CharField(
                blank=True,
                help_text="Stores original user_code of object. Deleted objects has null user_code which makes it available again.",
                max_length=255,
                null=True,
                verbose_name="deleted user code",
            ),
        ),
        migrations.AlterField(
            model_name="currency",
            name="is_deleted",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="Mark object as deleted. Does not actually delete the object.",
                verbose_name="is deleted",
            ),
        ),
        migrations.AlterField(
            model_name="currency",
            name="name",
            field=models.CharField(
                help_text="Human Readable Name of the object",
                max_length=255,
                verbose_name="name",
            ),
        ),
        migrations.AlterField(
            model_name="currency",
            name="notes",
            field=models.TextField(
                blank=True,
                help_text="Notes, any useful information about the object",
                null=True,
                verbose_name="notes",
            ),
        ),
        migrations.AlterField(
            model_name="currency",
            name="public_name",
            field=models.CharField(
                blank=True,
                help_text="Used if user does not have permissions to view object",
                max_length=255,
                null=True,
                verbose_name="public name",
            ),
        ),
        migrations.AlterField(
            model_name="currency",
            name="short_name",
            field=models.TextField(
                blank=True,
                help_text="Short Name of the object. Used in dropdown menus",
                null=True,
                verbose_name="short name",
            ),
        ),
        migrations.AlterField(
            model_name="currency",
            name="user_code",
            field=models.CharField(
                blank=True,
                help_text="Unique Code for this object. Used in Configuration and Permissions Logic",
                max_length=1024,
                null=True,
                verbose_name="user code",
            ),
        ),
    ]
