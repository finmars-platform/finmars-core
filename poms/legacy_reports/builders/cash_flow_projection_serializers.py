from __future__ import unicode_literals

from datetime import date

from dateutil.relativedelta import relativedelta
from django.conf import settings
from poms.reports.builders.cash_flow_projection_item import CashFlowProjectionReport
from poms.reports.builders.cash_flow_projection_item import CashFlowProjectionReportItem
from poms.reports.builders.transaction_serializers import TransactionReportItemSerializer, TransactionReportSerializer
from rest_framework import serializers

from poms.common.utils import date_now


class CashFlowProjectionReportItemSerializer(TransactionReportItemSerializer):
    item_type = serializers.ChoiceField(source='type', read_only=True,
                                        choices=CashFlowProjectionReportItem.TYPE_CHOICES)
    item_type_code = serializers.CharField(source='type_code', read_only=True)
    item_type_name = serializers.CharField(source='type_name', read_only=True)
    cash_consideration_before = serializers.ReadOnlyField()
    cash_consideration_after = serializers.ReadOnlyField()

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('read_only', True)

        super(CashFlowProjectionReportItemSerializer, self).__init__(*args, **kwargs)


class CashFlowProjectionReportSerializer(TransactionReportSerializer):
    balance_date = serializers.DateField(required=False, allow_null=True)
    report_date = serializers.DateField(required=False, allow_null=True)
    has_errors = serializers.ReadOnlyField()
    items = CashFlowProjectionReportItemSerializer(many=True, read_only=True)

    def __init__(self, *args, **kwargs):
        # kwargs.setdefault('read_only', True)

        super(CashFlowProjectionReportSerializer, self).__init__(*args, **kwargs)

    def validate(self, attrs):
        if not attrs.get('balance_date', None):
            if settings.DEBUG:
                attrs['balance_date'] = date(2016, 12, 21)
            else:
                attrs['balance_date'] = date_now()

        if not attrs.get('report_date', None):
            if settings.DEBUG:
                attrs['report_date'] = date(2016, 12, 26)
            else:
                attrs['report_date'] = attrs['balance_date'] + relativedelta(months=1)

        return attrs

    def create(self, validated_data):
        return CashFlowProjectionReport(**validated_data)
