from __future__ import unicode_literals

import json

from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.translation import ugettext_lazy

from poms.common.models import NamedModel, AbstractClassModel, EXPRESSION_FIELD_LENGTH
from poms.users.models import MasterUser


class BalanceReportCustomField(models.Model):

    STRING = 10
    NUMBER = 20
    DATE = 40

    VALUE_TYPES = (
        (NUMBER, ugettext_lazy('Number')),
        (STRING, ugettext_lazy('String')),
        (DATE, ugettext_lazy('Date')),
    )

    master_user = models.ForeignKey(MasterUser, related_name='balance_report_custom_fields', verbose_name=ugettext_lazy('master user'))
    name = models.CharField(max_length=255, verbose_name=ugettext_lazy('name'))
    user_code = models.CharField(max_length=255, verbose_name=ugettext_lazy('user code'))
    expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, verbose_name=ugettext_lazy('expression'))
    value_type = models.PositiveSmallIntegerField(choices=VALUE_TYPES, default=STRING,
                                                  verbose_name=ugettext_lazy('value type'))
    notes = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes'))

    class Meta:
        verbose_name = ugettext_lazy('balance report custom field')
        verbose_name_plural = ugettext_lazy('balance report custom fields')
        unique_together = [
            ['master_user', 'user_code']
        ]

    def __str__(self):
        return self.name


class PLReportCustomField(models.Model):

    STRING = 10
    NUMBER = 20
    DATE = 40

    VALUE_TYPES = (
        (NUMBER, ugettext_lazy('Number')),
        (STRING, ugettext_lazy('String')),
        (DATE, ugettext_lazy('Date')),
    )

    master_user = models.ForeignKey(MasterUser, related_name='pl_report_custom_fields', verbose_name=ugettext_lazy('master user'))
    name = models.CharField(max_length=255, verbose_name=ugettext_lazy('name'))
    user_code = models.CharField(max_length=255, verbose_name=ugettext_lazy('user code'))
    expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, verbose_name=ugettext_lazy('expression'))
    value_type = models.PositiveSmallIntegerField(choices=VALUE_TYPES, default=STRING,
                                                  verbose_name=ugettext_lazy('value type'))
    notes = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes'))

    class Meta:
        verbose_name = ugettext_lazy('pl report custom field')
        verbose_name_plural = ugettext_lazy('pl report custom fields')
        unique_together = [
            ['master_user', 'user_code']
        ]

    def __str__(self):
        return self.name


class TransactionReportCustomField(models.Model):

    STRING = 10
    NUMBER = 20
    DATE = 40

    VALUE_TYPES = (
        (NUMBER, ugettext_lazy('Number')),
        (STRING, ugettext_lazy('String')),
        (DATE, ugettext_lazy('Date')),
    )

    master_user = models.ForeignKey(MasterUser, related_name='transaction_report_custom_fields', verbose_name=ugettext_lazy('master user'))
    name = models.CharField(max_length=255, verbose_name=ugettext_lazy('name'))
    user_code = models.CharField(max_length=255, verbose_name=ugettext_lazy('user code'))
    expr = models.CharField(max_length=EXPRESSION_FIELD_LENGTH, verbose_name=ugettext_lazy('expression'))
    value_type = models.PositiveSmallIntegerField(choices=VALUE_TYPES, default=STRING,
                                                  verbose_name=ugettext_lazy('value type'))
    notes = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes'))

    class Meta:
        verbose_name = ugettext_lazy('transaction report custom field')
        verbose_name_plural = ugettext_lazy('transaction report custom fields')
        unique_together = [
            ['master_user', 'user_code']
        ]

    def __str__(self):
        return self.name


class BalanceReport(models.Model):
    master_user = models.ForeignKey(MasterUser, related_name='balance_reports',
                                    verbose_name=ugettext_lazy('master user'))

    class Meta:
        verbose_name = ugettext_lazy('balance report')
        verbose_name_plural = ugettext_lazy('balance reports')


class PLReport(models.Model):
    master_user = models.ForeignKey(MasterUser, related_name='pl_reports', verbose_name=ugettext_lazy('master user'))

    class Meta:
        verbose_name = ugettext_lazy('p&l report')
        verbose_name_plural = ugettext_lazy('p&l report')


class PerformanceReport(models.Model):
    master_user = models.ForeignKey(MasterUser, related_name='performance_reports',
                                    verbose_name=ugettext_lazy('master user'))

    class Meta:
        verbose_name = ugettext_lazy('performance report')
        verbose_name_plural = ugettext_lazy('performance reports')


class CashFlowReport(models.Model):
    master_user = models.ForeignKey(MasterUser, related_name='cashflow_reports',
                                    verbose_name=ugettext_lazy('master user'))

    class Meta:
        verbose_name = ugettext_lazy('cash flow report')
        verbose_name_plural = ugettext_lazy('cash flow reports')


class TransactionReport(models.Model):
    master_user = models.ForeignKey(MasterUser, related_name='transaction_reports',
                                    verbose_name=ugettext_lazy('master user'))

    class Meta:
        verbose_name = ugettext_lazy('transaction report')
        verbose_name_plural = ugettext_lazy('transaction reports')
