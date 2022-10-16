from __future__ import unicode_literals

from datetime import timedelta, date

from django.shortcuts import render
from functools import lru_cache

import pytz
from babel import Locale
from babel.dates import get_timezone, get_timezone_gmt, get_timezone_name
from django.conf import settings
from django.http import HttpResponse
from django.utils import translation, timezone
from django.views.generic import TemplateView
from rest_framework import response, schemas
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from poms.api.serializers import LanguageSerializer, Language, TimezoneSerializer, Timezone, ExpressionSerializer
from poms.common.utils import get_list_of_business_days_between_two_dates, date_now, get_closest_bday_of_yesterday, \
    get_list_of_dates_between_two_dates
from poms.common.views import AbstractViewSet, AbstractApiView
from poms.instruments.models import PriceHistory, PricingPolicy

_languages = [Language(code, name) for code, name in settings.LANGUAGES]

from django.views.decorators.cache import never_cache
from django.http import HttpResponse, JsonResponse


@lru_cache()
def _get_timezones(locale, now):
    locale = Locale(locale)
    timezones = []
    for code in pytz.common_timezones:
        tz = get_timezone(code)
        d = timezone.localtime(now, tz)
        tz_offset = get_timezone_gmt(datetime=d, locale=locale)[3:]
        name = '%s - %s' % (
            tz_offset,
            get_timezone_name(tz, width='short', locale=locale),
        )
        timezones.append(Timezone(code, name, offset=d.utcoffset()))
    timezones = sorted(timezones, key=lambda v: v.offset)
    return timezones


def get_timezones():
    now = timezone.now()
    now = now.replace(minute=0, second=0, microsecond=0)
    # now = timezone.make_aware(datetime(2009, 10, 31, 23, 30))
    return _get_timezones(translation.get_language(), now)


class LanguageViewSet(AbstractViewSet):
    serializer_class = LanguageSerializer

    def list(self, request, *args, **kwargs):
        languages = _languages
        serializer = self.get_serializer(instance=languages, many=True)
        return Response(serializer.data)


class TimezoneViewSet(AbstractViewSet):
    serializer_class = TimezoneSerializer

    def list(self, request, *args, **kwargs):
        timezones = get_timezones()
        serializer = self.get_serializer(instance=timezones, many=True)
        return Response(serializer.data)


class ExpressionViewSet(AbstractViewSet):
    serializer_class = ExpressionSerializer

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(data={'expression': 'now()', 'is_eval': True})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


if 'rest_framework_swagger' in settings.INSTALLED_APPS:
    from rest_framework_swagger.renderers import SwaggerUIRenderer, OpenAPIRenderer


    class SchemaViewSet(AbstractApiView):
        renderer_classes = [SwaggerUIRenderer, OpenAPIRenderer]

        def get(self, request):
            generator = schemas.SchemaGenerator(title='FinMars API')
            return response.Response(generator.get_schema(request=request))


class StatsViewSet(AbstractViewSet):
    items_to_fill = 0
    filled_items = 0

    def get_first_transaction_date(self):

        from poms.transactions.models import Transaction
        trns = Transaction.objects.all().order_by('accounting_date')

        if len(trns):
            return trns[0].accounting_date

        return None

    def get_general_section(self):

        from poms.instruments.models import Instrument

        from poms.transactions.models import ComplexTransaction
        from poms.transactions.models import Transaction
        from poms.portfolios.models import Portfolio
        from poms.accounts.models import Account
        from poms.currencies.models import Currency


        result = {
            'total_instruments': Instrument.objects.count(),
            'total_complex_transactions': ComplexTransaction.objects.filter(transactions__accounting_date__gte=self.date_from).count(),
            'total_base_transactions': Transaction.objects.filter(accounting_date__gte=self.date_from).count(),
            'total_portfolios': Portfolio.objects.count(),
            'total_accounts': Account.objects.count(),
            'total_currencies': Currency.objects.count(),
            'total_pricing_policies': PricingPolicy.objects.count(),
            'first_transaction_date': self.first_transaction_date,
            'days_from_first_transaction': len(self.days_from_first_transaction),
            'bdays_from_first_transaction': len(self.bdays_from_first_transaction),
        }

        if self.items_to_fill:
            result['filled_percent'] = round(self.filled_items / (self.items_to_fill / 100))

        return result

    def get_price_history_section(self):

        from poms.instruments.models import Instrument

        total_instruments = Instrument.objects.count()
        total_pricing_policies = PricingPolicy.objects.count()
        total_prices = PriceHistory.objects.filter(date__gte=self.date_from).count()

        result = {
            'total_instruments': total_instruments,
            'total_pricing_policies': total_pricing_policies,
            'total_prices': total_prices,
            'first_transaction_date': self.first_transaction_date,
            'days_from_first_transaction': len(self.days_from_first_transaction),
            'bdays_from_first_transaction': len(self.bdays_from_first_transaction),
            'expecting_total_prices': total_instruments * total_pricing_policies * len(
                self.days_from_first_transaction),
            'expecting_total_bdays_prices': total_instruments * total_pricing_policies * len(
                self.bdays_from_first_transaction),
            'filled_percent': round(total_prices / (
                        total_instruments * total_pricing_policies * len(self.bdays_from_first_transaction) / 100))
        }

        self.filled_items = self.filled_items + total_prices
        self.items_to_fill = self.items_to_fill + (total_instruments * total_pricing_policies* len(self.bdays_from_first_transaction))

        instruments = []

        for instrument in Instrument.objects.all():

            instrument_result = {}

            instrument_result['instrument'] = {
                'id': instrument.id,
                'user_code': instrument.user_code,
                'name': instrument.name
            }
            instrument_result['expecting_prices'] = total_pricing_policies * len(self.days_from_first_transaction)
            instrument_result['expecting_bdays_prices'] = total_pricing_policies * len(
                self.bdays_from_first_transaction)
            instrument_result['prices'] = PriceHistory.objects.filter(instrument=instrument, date__gte=self.date_from).count()

            try:
                instrument_result['last_price_date'] = \
                PriceHistory.objects.filter(instrument=instrument, date__gte=self.date_from).order_by('-date')[0].date
            except Exception as e:
                instrument_result['last_price_date'] = None

            instruments.append(instrument_result)

        result['instruments'] = instruments

        return result

    def get_currency_history_section(self):

        from poms.currencies.models import Currency
        from poms.currencies.models import CurrencyHistory

        total_currencies = Currency.objects.count()
        total_pricing_policies = PricingPolicy.objects.count()
        total_fxrates = CurrencyHistory.objects.filter(date__gte=self.date_from).count()

        result = {
            'total_currencies': total_currencies,
            'total_pricing_policies': total_pricing_policies,
            'total_fxrates': total_fxrates,
            'first_transaction_date': self.first_transaction_date,
            'days_from_first_transaction': len(self.days_from_first_transaction),
            'bdays_from_first_transaction': len(self.bdays_from_first_transaction),
            'expecting_total_fxrates': total_currencies * total_pricing_policies * len(
                self.days_from_first_transaction),
            'expecting_total_bdays_fxrates': total_currencies * total_pricing_policies * len(
                self.bdays_from_first_transaction),
            'filled_percent': round(total_fxrates / (
                        total_currencies * total_pricing_policies * len(self.bdays_from_first_transaction) / 100))
        }

        self.filled_items = self.filled_items + total_fxrates
        self.items_to_fill = self.items_to_fill + (total_currencies * total_pricing_policies * len(self.bdays_from_first_transaction))

        currencies = []

        for currency in Currency.objects.all():

            currency_result = {}

            currency_result['currency'] = {
                'id': currency.id,
                'user_code': currency.user_code,
                'name': currency.name
            }
            currency_result['expecting_fxrates'] = total_pricing_policies * len(self.days_from_first_transaction)
            currency_result['expecting_bdays_fxrates'] = total_pricing_policies * len(self.bdays_from_first_transaction)
            currency_result['fxrates'] = CurrencyHistory.objects.filter(currency=currency, date__gte=self.date_from).count()

            try:
                currency_result['last_fxrate_date'] = \
                CurrencyHistory.objects.filter(currency=currency, date__gte=self.date_from).order_by('-date')[0].date
            except Exception as e:
                currency_result['last_fxrate_date'] = None

            currencies.append(currency_result)

        result['currencies'] = currencies

        return result

    def get_nav_history_section(self):

        from poms.widgets.models import BalanceReportHistory
        total_nav_history = BalanceReportHistory.objects.filter(date__gte=self.date_from).count()

        from poms.portfolios.models import Portfolio
        portfolios_count = Portfolio.objects.count()

        result = {
            'total_nav_histories': total_nav_history,
            'expecting_histories': len(self.days_from_first_transaction) * portfolios_count,
            'expecting_bdays_histories': len(self.bdays_from_first_transaction) * portfolios_count,
            'filled_percent': round(
                total_nav_history / (len(self.bdays_from_first_transaction) * portfolios_count / 100)),
            'total_portfolios': Portfolio.objects.count()
        }

        self.filled_items = self.filled_items + total_nav_history
        self.items_to_fill = self.items_to_fill + (len(self.bdays_from_first_transaction) * portfolios_count)

        portfolios = []

        for portfolio in Portfolio.objects.all():

            portfolio_result = {}

            portfolio_result['portfolio'] = {
                'id': portfolio.id,
                'user_code': portfolio.user_code,
                'name': portfolio.name
            }
            portfolio_result['expecting_nav_histories'] = len(self.days_from_first_transaction)
            portfolio_result['expecting_bdays_nav_histories'] = len(self.bdays_from_first_transaction)
            portfolio_result['nav_histories'] = BalanceReportHistory.objects.filter(portfolio=portfolio, date__gte=self.date_from).count()

            try:
                portfolio_result['last_nav_history_date'] = \
                BalanceReportHistory.objects.filter(portfolio=portfolio, date__gte=self.date_from).order_by('-date')[0].date
            except Exception as e:
                portfolio_result['last_nav_history_date'] = None

            portfolios.append(portfolio_result)

        result['portfolios'] = portfolios

        return result

    def get_pl_history_section(self):

        from poms.widgets.models import PLReportHistory
        total_pl_history = PLReportHistory.objects.filter(date__gte=self.date_from).count()

        from poms.portfolios.models import Portfolio
        portfolios_count = Portfolio.objects.count()

        result = {

            'total_pl_histories': total_pl_history,
            'expecting_pl_histories': len(self.days_from_first_transaction) * portfolios_count,
            'expecting_pl_bdays_histories': len(self.bdays_from_first_transaction) * portfolios_count,
            'filled_percent': round(
                total_pl_history / (len(self.bdays_from_first_transaction) * portfolios_count / 100)),
            'total_portfolios': Portfolio.objects.count()
        }

        self.filled_items = self.filled_items + total_pl_history
        self.items_to_fill = self.items_to_fill + (len(self.bdays_from_first_transaction) * portfolios_count)

        portfolios = []

        for portfolio in Portfolio.objects.all():

            portfolio_result = {}

            portfolio_result['portfolio'] = {
                'id': portfolio.id,
                'user_code': portfolio.user_code,
                'name': portfolio.name
            }
            portfolio_result['expecting_pl_histories'] = len(self.days_from_first_transaction)
            portfolio_result['expecting_bdays_pl_histories'] = len(self.bdays_from_first_transaction)
            portfolio_result['pl_histories'] = PLReportHistory.objects.filter(portfolio=portfolio, date__gte=self.date_from).count()

            try:
                portfolio_result['last_pl_history_date'] = \
                PLReportHistory.objects.filter(portfolio=portfolio, date__gte=self.date_from).order_by('-date')[0].date
            except Exception as e:
                portfolio_result['last_pl_history_date'] = None

            portfolios.append(portfolio_result)

        result['portfolios'] = portfolios

        return result

    def get_widget_stats_history_section(self):

        from poms.widgets.models import WidgetStats
        total_widget_stats = WidgetStats.objects.filter(date__gte=self.date_from).count()

        from poms.portfolios.models import Portfolio
        portfolios_count = Portfolio.objects.count()

        result = {

            'total_widget_stats': total_widget_stats,
            'expecting_widget_stats': len(self.days_from_first_transaction) * portfolios_count,
            'expecting_bdays_widget_stats': len(self.bdays_from_first_transaction) * portfolios_count,
            'filled_percent': round(
                total_widget_stats / (len(self.bdays_from_first_transaction) * portfolios_count / 100)),
            'total_portfolios': Portfolio.objects.count()
        }

        self.filled_items = self.filled_items + total_widget_stats
        self.items_to_fill = self.items_to_fill + (len(self.bdays_from_first_transaction) * portfolios_count)

        portfolios = []

        for portfolio in Portfolio.objects.all():

            portfolio_result = {}

            portfolio_result['portfolio'] = {
                'id': portfolio.id,
                'user_code': portfolio.user_code,
                'name': portfolio.name
            }
            portfolio_result['expecting_widget_stats'] = len(self.days_from_first_transaction)
            portfolio_result['expecting_bdays_widget_stats'] = len(self.bdays_from_first_transaction)
            portfolio_result['widget_stats'] = WidgetStats.objects.filter(portfolio=portfolio, date__gte=self.date_from).count()

            try:
                portfolio_result['last_widget_stats_date'] = \
                WidgetStats.objects.filter(portfolio=portfolio, date__gte=self.date_from).order_by('-date')[0].date
            except Exception as e:
                portfolio_result['last_widget_stats_date'] = None

            portfolios.append(portfolio_result)

        result['portfolios'] = portfolios

        return result

    def list(self, request, *args, **kwargs):

        result = {}

        self.period = request.query_params.get('period', 'this_year')

        first_transaction_date = self.get_first_transaction_date()
        bday_yesterday = get_closest_bday_of_yesterday()

        self.date_to = bday_yesterday

        if first_transaction_date:

            self.first_transaction_date = self.get_first_transaction_date()

            self.date_from = self.first_transaction_date

            if self.period == 'since_inception':
                self.date_from = self.first_transaction_date

            if self.period == 'this_year':
                self.date_from = date(date.today().year, 1, 1)

            if self.period == 'last_year':
                self.date_from = date(date.today().year - 1, 1, 1)

            if self.date_from < self.first_transaction_date:
                self.date_from = self.first_transaction_date

            self.days_from_first_transaction = get_list_of_dates_between_two_dates(self.date_from, self.date_to)
            self.bdays_from_first_transaction = get_list_of_business_days_between_two_dates(self.date_from, self.date_to)

            result['price_history'] = self.get_price_history_section()
            result['currency_history'] = self.get_currency_history_section()
            result['nav_history'] = self.get_nav_history_section()
            result['pl_history'] = self.get_pl_history_section()
            result['widget_stats_history'] = self.get_widget_stats_history_section()
            # important to be after other section to calc overall percent
            result['general'] = self.get_general_section()
            result['date_from'] = self.date_from
            result['date_to'] = self.date_to


        else:
            result['error_message'] = 'No Transactions'

        return Response(result)
