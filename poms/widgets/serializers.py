from rest_framework import serializers

from poms.accounts.fields import AccountField
from poms.common.utils import date_now
from poms.portfolios.fields import PortfolioField


class CollectHistorySerializer(serializers.Serializer):

    date_from = serializers.DateField(required=False, allow_null=True, default=date_now)

    date_to = serializers.DateField(required=False, allow_null=True, default=date_now,)

    portfolio = PortfolioField(required=False, allow_null=True, allow_empty=True)