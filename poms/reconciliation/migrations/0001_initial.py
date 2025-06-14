# Generated by Django 4.1.3 on 2022-12-07 21:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('transactions', '0001_initial'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TransactionTypeReconField',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reference_name', models.CharField(max_length=255, verbose_name='reference name ')),
                ('description', models.TextField(blank=True, null=True, verbose_name='description')),
                ('value_string', models.CharField(blank=True, default='', max_length=4096, verbose_name='value string')),
                ('value_float', models.CharField(blank=True, default='', max_length=4096, verbose_name='value float')),
                ('value_date', models.CharField(blank=True, default='', max_length=4096, verbose_name='value date')),
                ('transaction_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recon_fields', to='transactions.transactiontype', verbose_name='transaction type')),
            ],
        ),
        migrations.CreateModel(
            name='ReconciliationNewBankFileField',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_id', models.CharField(blank=True, max_length=30, null=True, verbose_name='source id')),
                ('reference_name', models.CharField(max_length=255, verbose_name='reference name ')),
                ('description', models.TextField(blank=True, null=True, verbose_name='description')),
                ('value_string', models.TextField(blank=True, null=True, verbose_name='value string')),
                ('value_float', models.FloatField(blank=True, null=True, verbose_name='value float')),
                ('value_date', models.DateField(blank=True, db_index=True, null=True, verbose_name='value date')),
                ('is_canceled', models.BooleanField(db_index=True, default=False, verbose_name='is canceled')),
                ('file_name', models.TextField(blank=True, null=True, verbose_name='file name')),
                ('import_scheme_name', models.TextField(blank=True, null=True, verbose_name='import scheme name')),
                ('reference_date', models.DateField(blank=True, db_index=True, null=True, verbose_name='value date')),
                ('master_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.masteruser', verbose_name='master user')),
            ],
            options={
                'verbose_name': 'reconciliation new bank file field',
                'verbose_name_plural': 'reconciliation new bank file fields',
            },
        ),
        migrations.CreateModel(
            name='ReconciliationComplexTransactionField',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reference_name', models.CharField(max_length=255, verbose_name='reference name ')),
                ('description', models.TextField(blank=True, null=True, verbose_name='description')),
                ('value_string', models.TextField(blank=True, null=True, verbose_name='value string')),
                ('value_float', models.FloatField(blank=True, null=True, verbose_name='value float')),
                ('value_date', models.DateField(blank=True, db_index=True, null=True, verbose_name='value date')),
                ('status', models.PositiveSmallIntegerField(choices=[(1, 'Matched'), (2, 'Unmatched'), (3, 'Auto Matched'), (4, 'Ignore')], db_index=True, default=2, verbose_name='status')),
                ('match_date', models.DateField(blank=True, db_index=True, null=True, verbose_name='value date')),
                ('notes', models.TextField(blank=True, null=True, verbose_name='notes')),
                ('complex_transaction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recon_fields', to='transactions.complextransaction', verbose_name='complex transaction')),
                ('master_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.masteruser', verbose_name='master user')),
            ],
            options={
                'verbose_name': 'reconciliation complex transaction field',
                'verbose_name_plural': 'reconciliation complex transaction fields',
            },
        ),
        migrations.CreateModel(
            name='ReconciliationBankFileField',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_id', models.CharField(blank=True, max_length=30, null=True, verbose_name='source id')),
                ('reference_name', models.CharField(max_length=255, verbose_name='reference name ')),
                ('description', models.TextField(blank=True, null=True, verbose_name='description')),
                ('value_string', models.TextField(blank=True, null=True, verbose_name='value string')),
                ('value_float', models.FloatField(blank=True, null=True, verbose_name='value float')),
                ('value_date', models.DateField(blank=True, db_index=True, null=True, verbose_name='value date')),
                ('is_canceled', models.BooleanField(db_index=True, default=False, verbose_name='is canceled')),
                ('status', models.PositiveSmallIntegerField(choices=[(1, 'Matched'), (2, 'Conflict'), (3, 'Resolved'), (4, 'Ignore'), (5, 'Auto Matched')], db_index=True, default=2, verbose_name='status')),
                ('file_name', models.TextField(blank=True, null=True, verbose_name='file name')),
                ('import_scheme_name', models.TextField(blank=True, null=True, verbose_name='import scheme name')),
                ('reference_date', models.DateField(blank=True, db_index=True, null=True, verbose_name='value date')),
                ('notes', models.TextField(blank=True, null=True, verbose_name='notes')),
                ('linked_complex_transaction_field', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bank_file_fields', to='reconciliation.reconciliationcomplextransactionfield', verbose_name='linked complex transaction field')),
                ('master_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='users.masteruser', verbose_name='master user')),
            ],
            options={
                'verbose_name': 'reconciliation bank file field',
                'verbose_name_plural': 'reconciliation bank file fields',
                'unique_together': {('master_user', 'source_id', 'reference_name', 'import_scheme_name')},
            },
        ),
    ]
