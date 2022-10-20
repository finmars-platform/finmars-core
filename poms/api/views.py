from __future__ import unicode_literals

import calendar
import croniter
from datetime import timedelta, date, datetime

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
    get_list_of_dates_between_two_dates, last_day_of_month
from poms.common.views import AbstractViewSet, AbstractApiView
from poms.currencies.models import Currency
from poms.instruments.models import PriceHistory, PricingPolicy, Instrument

_languages = [Language(code, name) for code, name in settings.LANGUAGES]

from django.views.decorators.cache import never_cache
from django.http import HttpResponse, JsonResponse

import logging

_l = logging.getLogger('poms.api')


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
            'total_complex_transactions': ComplexTransaction.objects.filter(
                transactions__accounting_date__gte=self.date_from).count(),
            'total_base_transactions': Transaction.objects.filter(accounting_date__gte=self.date_from).count(),
            'total_portfolios': Portfolio.objects.count(),
            'total_accounts': Account.objects.count(),
            'total_currencies': Currency.objects.count(),
            'total_pricing_policies': PricingPolicy.objects.count(),
            'first_transaction_date': self.first_transaction_date,
            'days_from_first_transaction': len(self.days_from_first_transaction),
            'bdays_from_first_transaction': len(self.bdays_from_first_transaction),
        }

        return result

    def get_price_history_section(self, portfolio, portfolio_stats, instruments_ids):

        from poms.instruments.models import Instrument

        total_pricing_policies = PricingPolicy.objects.count()

        result = {
            'filled_items': 0,
            'items_to_fill': 0
        }

        pricing_policies = []

        instruments_count = Instrument.objects.filter(id__in=instruments_ids).count()

        for pricing_policy in PricingPolicy.objects.all():

            pricing_policy_result = {
                'expecting_histories': len(self.days_from_first_transaction) * instruments_count,
                'expecting_bdays_histories': len(self.bdays_from_first_transaction) * instruments_count,
                'price_histories': PriceHistory.objects.filter(date__gte=self.date_from, pricing_policy=pricing_policy,
                                                               instrument_id__in=instruments_ids).count(),
            }

            try:
                pricing_policy_result['filled_percent'] = round(
                    PriceHistory.objects.filter(date__gte=self.date_from, pricing_policy=pricing_policy,
                                                instrument_id__in=instruments_ids).count() / (
                            len(self.bdays_from_first_transaction) * instruments_count / 100))
            except Exception as e:
                pricing_policy_result['filled_percent'] = 0

            pricing_policy_result['pricing_policy'] = {
                'id': pricing_policy.id,
                'name': pricing_policy.name,
                'user_code': pricing_policy.user_code
            }

            instruments = []

            for instrument in Instrument.objects.filter(id__in=instruments_ids):

                instrument_result = {}

                instrument_result['instrument'] = {
                    'id': instrument.id,
                    'user_code': instrument.user_code,
                    'name': instrument.name
                }
                instrument_result['expecting_prices'] = len(self.days_from_first_transaction)
                instrument_result['expecting_bdays_prices'] = len(
                    self.bdays_from_first_transaction)
                instrument_result['prices'] = PriceHistory.objects.filter(instrument=instrument,
                                                                          date__gte=self.date_from,
                                                                          pricing_policy=pricing_policy).count()

                try:
                    instrument_result['last_price_date'] = \
                        PriceHistory.objects.filter(instrument=instrument, date__gte=self.date_from).order_by('-date')[
                            0].date
                except Exception as e:
                    instrument_result['last_price_date'] = None

                instruments.append(instrument_result)

            pricing_policy_result['instruments'] = instruments

            # Price History stats

            result['filled_items'] = result['filled_items'] + pricing_policy_result['price_histories']
            result['items_to_fill'] = result['items_to_fill'] + (
                    len(self.bdays_from_first_transaction) * instruments_count)

            # Portfolio stats

            portfolio_stats['filled_items'] = portfolio_stats['filled_items'] + pricing_policy_result['price_histories']
            portfolio_stats['items_to_fill'] = portfolio_stats['items_to_fill'] + (
                    len(self.bdays_from_first_transaction) * instruments_count)

            pricing_policies.append(pricing_policy_result)

        result['pricing_policies'] = pricing_policies
        try:
            result['filled_percent'] = round(result['filled_items'] / (result['items_to_fill'] / 100))
        except Exception as e:
            result['filled_percent'] = 0

        return result

    def get_currency_history_section(self, portfolio, portfolio_stats, currencies_ids):

        from poms.currencies.models import Currency
        from poms.currencies.models import CurrencyHistory

        total_pricing_policies = PricingPolicy.objects.count()

        result = {
            'filled_items': 0,
            'items_to_fill': 0
        }

        pricing_policies = []

        for pricing_policy in PricingPolicy.objects.all():

            currencies_count = Currency.objects.filter(id__in=currencies_ids).count()

            pricing_policy_result = {
                'expecting_histories': len(self.days_from_first_transaction) * currencies_count,
                'expecting_bdays_histories': len(self.bdays_from_first_transaction) * currencies_count,
                'currency_histories': CurrencyHistory.objects.filter(date__gte=self.date_from,
                                                                     pricing_policy=pricing_policy,
                                                                     currency_id__in=currencies_ids).count(),
            }

            try:
                pricing_policy_result['filled_percent'] = round(
                    CurrencyHistory.objects.filter(date__gte=self.date_from, pricing_policy=pricing_policy,
                                                   currency_id__in=currencies_ids).count() / (
                            len(self.bdays_from_first_transaction) * currencies_count / 100))
            except Exception as e:
                pricing_policy_result['filled_percent'] = 0

            pricing_policy_result['pricing_policy'] = {
                'id': pricing_policy.id,
                'name': pricing_policy.name,
                'user_code': pricing_policy.user_code
            }

            currencies = []

            for currency in Currency.objects.filter(id__in=currencies_ids):

                currency_result = {}

                currency_result['currency'] = {
                    'id': currency.id,
                    'user_code': currency.user_code,
                    'name': currency.name
                }
                currency_result['expecting_fxrates'] = len(self.days_from_first_transaction)
                currency_result['expecting_bdays_fxrates'] = len(self.bdays_from_first_transaction)
                currency_result['fxrates'] = CurrencyHistory.objects.filter(currency=currency, date__gte=self.date_from,
                                                                            pricing_policy=pricing_policy).count()

                try:
                    currency_result['last_fxrate_date'] = \
                        CurrencyHistory.objects.filter(currency=currency, date__gte=self.date_from).order_by('-date')[
                            0].date
                except Exception as e:
                    currency_result['last_fxrate_date'] = None

                currencies.append(currency_result)

            pricing_policy_result['currencies'] = currencies

            # Currency history stat

            result['filled_items'] = result['filled_items'] + pricing_policy_result['currency_histories']
            result['items_to_fill'] = result['items_to_fill'] + (
                    len(self.bdays_from_first_transaction) * currencies_count)

            # Portfolio stat

            portfolio_stats['filled_items'] = portfolio_stats['filled_items'] + pricing_policy_result[
                'currency_histories']
            portfolio_stats['items_to_fill'] = portfolio_stats['items_to_fill'] + (
                    len(self.bdays_from_first_transaction) * currencies_count)

            pricing_policies.append(pricing_policy_result)

        result['pricing_policies'] = pricing_policies
        try:
            result['filled_percent'] = round(result['filled_items'] / (result['items_to_fill'] / 100))
        except Exception as e:
            result['filled_percent'] = 0

        return result

    def get_nav_history_section(self, portfolio, portfolio_stats):

        from poms.widgets.models import BalanceReportHistory

        result = {
            'expecting_histories': len(self.days_from_first_transaction),
            'expecting_bdays_histories': len(self.bdays_from_first_transaction),
        }

        result['nav_histories'] = BalanceReportHistory.objects.filter(portfolio=portfolio,
                                                                      date__gte=self.date_from).count()

        result['filled_percent'] = round(result['nav_histories'] / (len(self.bdays_from_first_transaction) / 100))

        try:
            result['last_nav_history_date'] = \
                BalanceReportHistory.objects.filter(portfolio=portfolio, date__gte=self.date_from).order_by('-date')[
                    0].date
        except Exception as e:
            result['last_nav_history_date'] = None

        portfolio_stats['filled_items'] = portfolio_stats['filled_items'] + result['nav_histories']
        portfolio_stats['items_to_fill'] = portfolio_stats['items_to_fill'] + (len(self.bdays_from_first_transaction))

        return result

    def get_pl_history_section(self, portfolio, portfolio_stats):

        from poms.widgets.models import PLReportHistory

        result = {
            'expecting_pl_histories': len(self.days_from_first_transaction),
            'expecting_pl_bdays_histories': len(self.bdays_from_first_transaction),
        }

        result['pl_histories'] = PLReportHistory.objects.filter(portfolio=portfolio, date__gte=self.date_from).count()
        result['filled_percent'] = round(result['pl_histories'] / (len(self.bdays_from_first_transaction) / 100))

        try:
            result['last_pl_history_date'] = \
                PLReportHistory.objects.filter(portfolio=portfolio, date__gte=self.date_from).order_by('-date')[0].date
        except Exception as e:
            result['last_pl_history_date'] = None

        portfolio_stats['filled_items'] = portfolio_stats['filled_items'] + result['pl_histories']
        portfolio_stats['items_to_fill'] = portfolio_stats['items_to_fill'] + (len(self.bdays_from_first_transaction))

        return result

    def get_widget_stats_history_section(self, portfolio, portfolio_stats):

        from poms.widgets.models import WidgetStats

        result = {
            'expecting_widget_stats': len(self.days_from_first_transaction),
            'expecting_bdays_widget_stats': len(self.bdays_from_first_transaction)
        }

        result['widget_stats'] = WidgetStats.objects.filter(portfolio=portfolio, date__gte=self.date_from).count()
        result['filled_percent'] = round(result['widget_stats'] / (len(self.bdays_from_first_transaction) / 100))

        try:
            result['last_widget_stats_date'] = \
                WidgetStats.objects.filter(portfolio=portfolio, date__gte=self.date_from).order_by('-date')[0].date
        except Exception as e:
            result['last_widget_stats_date'] = None

        portfolio_stats['filled_items'] = portfolio_stats['filled_items'] + result['widget_stats']
        portfolio_stats['items_to_fill'] = portfolio_stats['items_to_fill'] + (len(self.bdays_from_first_transaction))

        return result

    def list(self, request, *args, **kwargs):

        from poms.transactions.models import ComplexTransaction

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
            self.bdays_from_first_transaction = get_list_of_business_days_between_two_dates(self.date_from,
                                                                                            self.date_to)

            from poms.portfolios.models import Portfolio
            from poms.transactions.models import Transaction

            portfolios = []

            for portfolio in Portfolio.objects.all():
                portfolio_item = {}

                portfolio_stats = {
                    'filled_items': 0,
                    'items_to_fill': 0
                }

                portfolio_item['portfolio'] = {
                    'id': portfolio.id,
                    'name': portfolio.name,
                    'user_code': portfolio.user_code
                }

                portfolio_item['complex_transactions'] = ComplexTransaction.objects.filter(
                    transactions__portfolio=portfolio, transactions__accounting_date__gte=self.date_from).count()
                portfolio_item['transactions'] = Transaction.objects.filter(portfolio=portfolio,
                                                                            accounting_date__gte=self.date_from).count()

                instruments_ids = list(
                    Transaction.objects.filter(portfolio=portfolio).values_list('instrument', flat=True))
                instruments_ids = instruments_ids + list(
                    Transaction.objects.filter(portfolio=portfolio).values_list('linked_instrument', flat=True))
                instruments_ids = instruments_ids + list(
                    Transaction.objects.filter(portfolio=portfolio).values_list('allocation_balance', flat=True))
                instruments_ids = instruments_ids + list(
                    Transaction.objects.filter(portfolio=portfolio).values_list('allocation_pl', flat=True))

                portfolio_item['related_instruments'] = Instrument.objects.filter(id__in=instruments_ids).count()

                currency_ids = list(
                    Transaction.objects.filter(portfolio=portfolio).values_list('transaction_currency', flat=True))
                currency_ids = currency_ids + list(
                    Transaction.objects.filter(portfolio=portfolio).values_list('settlement_currency', flat=True))

                portfolio_item['related_currencies'] = Currency.objects.filter(id__in=currency_ids).count()

                portfolio_item['price_history'] = self.get_price_history_section(portfolio, portfolio_stats,
                                                                                 instruments_ids)
                portfolio_item['currency_history'] = self.get_currency_history_section(portfolio, portfolio_stats,
                                                                                       currency_ids)
                portfolio_item['nav_history'] = self.get_nav_history_section(portfolio, portfolio_stats)
                portfolio_item['pl_history'] = self.get_pl_history_section(portfolio, portfolio_stats)
                portfolio_item['widget_stats_history'] = self.get_widget_stats_history_section(portfolio,
                                                                                               portfolio_stats)

                portfolio_item['portfolio_stats'] = portfolio_stats
                portfolio_item['filled_percent'] = round(portfolio_item['portfolio_stats']['filled_items'] / (
                        portfolio_item['portfolio_stats']['items_to_fill'] / 100))

                trns = Transaction.objects.filter(portfolio=portfolio).order_by('accounting_date')
                portfolio_item['first_transaction_date'] = []
                if len(trns):
                    portfolio_item['first_transaction_date'] = trns[0].accounting_date

                portfolios.append(portfolio_item)

            result['portfolios'] = portfolios
            # important to be after other section to calc overall percent
            result['general'] = self.get_general_section()
            result['date_from'] = self.date_from
            result['date_to'] = self.date_to

            for item in result['portfolios']:
                items_to_fill = 0
                filled_items = 0

                items_to_fill = items_to_fill + item['portfolio_stats']['items_to_fill']
                filled_items = filled_items + item['portfolio_stats']['filled_items']

                result['general']['filled_percent'] = round(filled_items / (items_to_fill / 100))


        else:
            result['error_message'] = 'No Transactions'

        return Response(result)


class CalendarEventsViewSet(AbstractViewSet):

    def list(self, request, *args, **kwargs):

        from poms.schedules.models import Schedule
        from poms.celery_tasks.models import CeleryTask
        from django_celery_beat.models import CrontabSchedule, PeriodicTask
        from poms.procedures.models import ExpressionProcedureInstance
        from poms.procedures.models import BaseProcedureInstance
        from poms.procedures.models import PricingProcedureInstance
        from poms.procedures.models import RequestDataFileProcedureInstance
        from poms.system_messages.models import SystemMessage
        def cronexp(field):
            """Representation of cron expression."""
            return field and str(field).replace(' ', '') or '*'

        date_from = request.query_params.get('date_from', None)
        date_to = request.query_params.get('date_to', None)
        filter = request.query_params.get('filter', None)

        if not date_from:
            date_from = datetime.today().replace(day=1)
        else:
            date_from = datetime.strptime(date_from, '%Y-%m-%d')

        if not date_to:
            date_to = last_day_of_month(date_from)
        else:
            date_to = datetime.strptime(date_to, '%Y-%m-%d')

        if not filter:
            filter = ['data_procedure', 'expression_procedure', 'pricing_procedure', 'celery_task']
        else:
            filter = filter.split(',')

        _l.info('date_from %s' % date_from)
        _l.info('date_to %s' % date_to)

        dates = get_list_of_dates_between_two_dates(date_from, date_to)

        results = []
        # Format for Date Calendar
        # {
        #     title  : 'event2',
        #     start  : '2010-01-05',
        #     end    : '2010-01-07'
        # },

        # Collect System Schedule

        if 'system_schedule' in filter:

            periodic_tasks = PeriodicTask.objects.exclude(name='Shedules Process')

            for task in periodic_tasks:

                # print('task.crontab.shedule %s' % task.crontab)
                expr = '{0} {1} {2} {3} {4}'.format(cronexp(task.crontab.minute),
                                                    cronexp(task.crontab.hour),
                                                    cronexp(task.crontab.day_of_month),
                                                    cronexp(task.crontab.month_of_year),
                                                    cronexp(task.crontab.day_of_week))

                # print('expr %s' % expr)

                cron = croniter.croniter(expr, date_from)

                lookup = True
                while lookup:
                    nextdate = cron.get_next(datetime)

                    item = {
                        'title': task.name,
                        'start': str(nextdate),
                        'classNames': ['system'],
                        'backgroundColor': '#ddd',
                        'extendedProps': {
                            'type': 'system_schedule',
                        }
                    }

                    results.append(item)

                    if nextdate > date_to:
                        lookup = False

        # Collect User Schedules

        if 'schedule' in filter:

            schedules = Schedule.objects.all()

            for schedule in schedules:
                cron = croniter.croniter(schedule.cron_expr, date_from)

                lookup = True
                while lookup:
                    nextdate = cron.get_next(datetime)

                    item = {
                        'title': schedule.name,
                        'start': str(nextdate),
                        'classNames': ['user'],
                        'backgroundColor': 'lightgrey',
                        'extendedProps': {
                            'type': 'schedule',
                        }
                    }

                    results.append(item)

                    if nextdate > date_to:
                        lookup = False

        # Data Procedures

        if 'data_procedure' in filter:

            data_procedure_instances = RequestDataFileProcedureInstance.objects.filter(created__gte=date_from,
                                                                                       created__lte=date_to)
            for instance in data_procedure_instances:

                item = {
                    'start': instance.created,
                    'classNames': ['user'],
                    'extendedProps': {
                        'type': 'data_procedure',
                        'id': instance.id,
                        'payload': {
                            'action': instance.action,
                            'provider': instance.provider,
                            'status': instance.status,
                            'error_message': instance.error_message,
                        }
                    }
                }

                item['backgroundColor'] = 'green'

                if instance.status == BaseProcedureInstance.STATUS_ERROR:
                    item['backgroundColor'] = 'red'

                if instance.status == BaseProcedureInstance.STATUS_PENDING:
                    item['backgroundColor'] = 'blue'

                title = '[' + str(instance.id) + ']'

                if instance.action:
                    title = title + ' ' + instance.action
                if instance.member:
                    title = title + ' by ' + instance.member.username

                item['title'] = title

                results.append(item)

        # Pricing Procedures

        if 'pricing_procedure' in filter:

            pricing_procedure_instances = PricingProcedureInstance.objects.filter(created__gte=date_from,
                                                                                  created__lte=date_to)

            for instance in pricing_procedure_instances:

                item = {
                    'start': instance.created,
                    'classNames': ['user'],
                    'extendedProps': {
                        'type': 'pricing_procedure',
                        'id': instance.id,
                        'payload': {
                            'action': instance.action,
                            'provider': instance.provider,
                            'status': instance.status,
                            'error_message': instance.error_message,
                        }
                    }
                }

                item['backgroundColor'] = 'green'

                if instance.status == BaseProcedureInstance.STATUS_ERROR:
                    item['backgroundColor'] = 'red'

                if instance.status == BaseProcedureInstance.STATUS_PENDING:
                    item['backgroundColor'] = 'blue'

                title = '[' + str(instance.id) + ']'

                if instance.action:
                    title = title + ' ' + instance.action
                if instance.member:
                    title = title + ' by ' + instance.member.username

                item['title'] = title

                results.append(item)

        # Expression Procedures

        if 'expression_procedure' in filter:

            expression_procedure_instances = ExpressionProcedureInstance.objects.filter(created__gte=date_from,
                                                                                        created__lte=date_to)

            for instance in expression_procedure_instances:

                item = {
                    'start': instance.created,
                    'classNames': ['user'],
                    'extendedProps': {
                        'type': 'expression_procedure',
                        'id': instance.id,
                        'payload': {
                            'action': instance.action,
                            'provider': instance.provider,
                            'status': instance.status,
                            'error_message': instance.error_message,
                            'result': instance.result
                        }
                    }
                }

                item['backgroundColor'] = 'green'

                if instance.status == BaseProcedureInstance.STATUS_ERROR:
                    item['backgroundColor'] = 'red'

                if instance.status == BaseProcedureInstance.STATUS_PENDING:
                    item['backgroundColor'] = 'blue'

                title = '[' + str(instance.id) + ']'
                if instance.action:
                    title = title + ' ' + instance.action
                if instance.member:
                    title = title + ' by ' + instance.member.username

                item['title'] = title

                results.append(item)

        # Collect Celery Tasks

        if 'celery_task' in filter:

            tasks = CeleryTask.objects.filter(created__gte=date_from, created__lte=date_to)

            for task in tasks:
                item = {
                    'start': task.created,
                    'classNames': ['user'],
                    'extendedProps': {
                        'type': 'celery_task',
                        'id': task.id,
                        'payload': {
                            'type': task.type,
                            'status': task.status,
                            'error_message': task.error_message
                        }
                    }
                }

                item['backgroundColor'] = 'green'

                if task.status == CeleryTask.STATUS_ERROR:
                    item['backgroundColor'] = 'red'

                if task.status == CeleryTask.STATUS_PENDING:
                    item['backgroundColor'] = 'blue'

                if task.verbose_name:
                    item['title'] = task.verbose_name
                else:

                    title = ''

                    if task.type:
                        title = title + ' ' + task.type

                    if task.member:
                        title = title + ' by ' + task.member.username

                    if not title:
                        title = '[' + str(task.id) + ']'

                    item['title'] = title

                results.append(item)

        # Manual System Message

        if 'system_message' in filter:

            messages = SystemMessage.objects.filter(created__gte=date_from, created__lte=date_to, title__icontains='manual')

            for message in messages:
                item = {
                    'title': message.title,
                    'start': message.created,
                    'classNames': ['user'],
                    'extendedProps': {
                        'type': 'system_message',
                        'id': message.id,
                        'payload': {
                            'type': message.type,
                            'section': message.section,
                            'description': message.description
                        }
                    }
                }

                results.append(item)

        response = {}

        response['results'] = results

        return Response(response)
