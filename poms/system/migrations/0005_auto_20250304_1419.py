from django.db import migrations


def fill_required_fields(apps, schema_editor) -> None:
    WhitelabelModel = apps.get_model("system", "WhitelabelModel")
    if WhitelabelModel.objects.count() == 0:
        return

    Member = apps.get_model("users", "Member")
    finmars_bot = Member.objects.get(username="finmars_bot")

    for white_label in WhitelabelModel.objects.all():
        white_label.configuration_code = white_label.theme_code
        white_label.name = white_label.company_name
        white_label.owner = finmars_bot
        white_label.save()

def reverse(apps, schema_editor) -> None:
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('system', '0004_whitelabelmodel_configuration_code_and_more'),
    ]

    operations = [
        migrations.RunPython(fill_required_fields, reverse),
    ]
