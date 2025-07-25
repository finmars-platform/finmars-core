# Generated by Django 4.2.3 on 2024-07-04 19:13

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="FinmarsFile",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        null=True,
                        verbose_name="created",
                    ),
                ),
                (
                    "modified",
                    models.DateTimeField(
                        auto_now=True, db_index=True, verbose_name="modified"
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        db_index=True,
                        help_text="File name, including extension",
                        max_length=255,
                    ),
                ),
                (
                    "path",
                    models.CharField(
                        db_index=True,
                        help_text="Path to the file in the storage system",
                        max_length=255,
                    ),
                ),
                (
                    "extension",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="File name extension",
                        max_length=255,
                    ),
                ),
                (
                    "size",
                    models.PositiveBigIntegerField(
                        help_text="Size of the file in bytes"
                    ),
                ),
            ],
            options={
                "ordering": ["path", "name"],
            },
        ),
        migrations.AddConstraint(
            model_name="finmarsfile",
            constraint=models.UniqueConstraint(
                fields=("path", "name"), name="unique_file_path"
            ),
        ),
    ]
