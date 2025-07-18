# Generated by Django 4.2.3 on 2023-11-06 15:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_alter_member_status'),
        ('ui', '0018_colorpalette_owner'),
    ]

    operations = [
        migrations.AddField(
            model_name='bookmark',
            name='owner',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='users.member', verbose_name='owner'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='complextransactionuserfield',
            name='owner',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='users.member', verbose_name='owner'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='configurationexportlayout',
            name='owner',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='users.member', verbose_name='owner'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='contextmenulayout',
            name='owner',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='users.member', verbose_name='owner'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='dashboardlayout',
            name='owner',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='users.member', verbose_name='owner'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='editlayout',
            name='owner',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='users.member', verbose_name='owner'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='instrumentuserfield',
            name='owner',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='users.member', verbose_name='owner'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='listlayout',
            name='owner',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='users.member', verbose_name='owner'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='memberlayout',
            name='owner',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='users.member', verbose_name='owner'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='mobilelayout',
            name='owner',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='users.member', verbose_name='owner'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='templatelayout',
            name='owner',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='users.member', verbose_name='owner'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='transactionuserfield',
            name='owner',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='users.member', verbose_name='owner'),
            preserve_default=False,
        ),
    ]
