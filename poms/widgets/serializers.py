from rest_framework import serializers

from poms.accounts.fields import AccountField
from poms.common.utils import date_now
from poms.currencies.fields import CurrencyField
from poms.instruments.fields import PricingPolicyField, CostMethodField
from poms.portfolios.fields import PortfolioField
from poms.widgets.models import WidgetStats


class CollectHistorySerializer(serializers.Serializer):

    date_from = serializers.DateField(required=False, allow_null=True, default=date_now)

    date_to = serializers.DateField(required=False, allow_null=True, default=date_now,)

    portfolio = PortfolioField(required=False, allow_null=True, allow_empty=True)
    currency = CurrencyField(required=False, allow_null=True, allow_empty=True)
    pricing_policy = PricingPolicyField(required=False, allow_null=True, allow_empty=True)
    cost_method = CostMethodField(required=False, allow_null=True)

    segmentation_type = serializers.CharField(required=False, allow_null=True, initial='months', default='months')


class CollectStatsSerializer(serializers.Serializer):

    date_from = serializers.DateField(required=False, allow_null=True, default=date_now)

    date_to = serializers.DateField(required=False, allow_null=True, default=date_now,)

    portfolio = PortfolioField(required=False, allow_null=True, allow_empty=True)

    benchmark = serializers.CharField(required=False, allow_null=True, initial='sp_500', default='sp_500')

    segmentation_type = serializers.CharField(required=False, allow_null=True, initial='months', default='months')


class WidgetStatsSerializer(serializers.ModelSerializer):

    class Meta():
        model = WidgetStats
        fields = ['date', 'portfolio', 'benchmark',
                  'nav', 'total',

                  'cumulative_return', 'annualized_return',

                  'portfolio_volatility', 'annualized_portfolio_volatility',

                  'sharpe_ratio', 'max_annualized_drawdown',

                  'betta', 'alpha',

                  'correlation'

                  ]