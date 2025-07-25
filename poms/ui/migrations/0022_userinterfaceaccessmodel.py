# Generated by Django 4.2.16 on 2025-01-14 17:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0014_member_deleted_at'),
        ('configuration_sharing', '0002_initial'),
        ('ui', '0021_remove_configurationexportlayout_created_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserInterfaceAccessModel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='created at')),
                ('modified_at', models.DateTimeField(auto_now=True, db_index=True, verbose_name='modified at')),
                ('configuration_code', models.CharField(max_length=255, verbose_name='Configuration Code')),
                ('json_data', models.TextField(blank=True, null=True, verbose_name='json data')),
                ('name', models.CharField(blank=True, db_index=True, default='', max_length=255, verbose_name='name')),
                ('user_code', models.CharField(blank=True, max_length=1024, null=True, verbose_name='user code')),
                ('role', models.CharField(blank=True, max_length=1024, null=True, verbose_name='role user code')),
                ('member', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='member_interface_access', to='users.member', verbose_name='member')),
                ('origin_for_global_layout', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_origins', to='configuration_sharing.sharedconfigurationfile', verbose_name='origin for global layout')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.member', verbose_name='owner')),
                ('sourced_from_global_layout', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_subscribers', to='configuration_sharing.sharedconfigurationfile', verbose_name='sourced for global layout')),
            ],
            options={
                'abstract': False,
                'unique_together': {('member', 'user_code')},
            },
        ),
    ]
