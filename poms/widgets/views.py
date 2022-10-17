import datetime
import statistics
import math
from django.db.models import Q

from poms.accounts.models import Account
from poms.celery_tasks.models import CeleryTask
from poms.common.utils import get_list_of_dates_between_two_dates, check_if_last_day_of_month, get_first_transaction, \
    last_business_day_in_month, get_list_of_months_between_two_dates, get_list_of_business_days_between_two_dates, \
    get_last_bdays_of_months_between_two_dates, get_closest_bday_of_yesterday
from poms.common.views import AbstractViewSet
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.db import transaction

from poms.currencies.models import Currency
from poms.instruments.models import CostMethod, PricingPolicy
from poms.portfolios.models import Portfolio, PortfolioBundle
from poms.reports.voila_constructrices.performance import PerformanceReportBuilder
from poms.system_messages.handlers import send_system_message
from poms.users.models import EcosystemDefault
from poms.widgets.handlers import StatsHandler
from poms.widgets.models import BalanceReportHistory, PLReportHistory, WidgetStats
from poms.widgets.serializers import CollectHistorySerializer, CollectStatsSerializer, WidgetStatsSerializer
from poms.widgets.tasks import collect_balance_report_history, collect_pl_report_history, collect_stats

import logging

from poms.widgets.utils import collect_balance_history, collect_pl_history, collect_widget_stats

_l = logging.getLogger('poms.widgets')


class HistoryNavViewSet(AbstractViewSet):

    def list(self, request):

        date_from = request.query_params.get('date_from', None)
        date_to = request.query_params.get('date_to', None)
        currency = request.query_params.get('currency', None)
        pricing_policy = request.query_params.get('pricing_policy', None)
        cost_method = request.query_params.get('cost_method', None)
        portfolio = request.query_params.get('portfolio', None)
        segmentation_type = request.query_params.get('segmentation_type', None)

        if not portfolio:
            raise ValidationError("Portfolio is no set")

        if not date_from:
            # date_from = str(datetime.datetime.now().year) + "-01-01"
            date_from = get_first_transaction(portfolio).accounting_date.strftime("%Y-%m-%d")

        if not date_to:
            date_to = get_closest_bday_of_yesterday(to_string=True)

        _l.info('date_from %s ' % date_from)
        _l.info('date_to %s ' % date_to)

        ecosystem_default = EcosystemDefault.objects.get(master_user=request.user.master_user)

        if not currency:
            currency = ecosystem_default.currency_id

        if not pricing_policy:
            pricing_policy = ecosystem_default.pricing_policy_id

        if not cost_method:
            cost_method = CostMethod.AVCO

        if not segmentation_type:
            segmentation_type = 'months'

        balance_report_histories = BalanceReportHistory.objects.filter(
            master_user=request.user.master_user,
            cost_method=cost_method,
            pricing_policy=pricing_policy,
            report_currency=currency
        )

        balance_report_histories = balance_report_histories.filter(portfolio_id=portfolio)

        _l.info('balance_report_histories %s' % len(list(balance_report_histories)))

        if segmentation_type == 'days':
            balance_report_histories = balance_report_histories.filter(
                date__gte=date_from,
                date__lte=date_to
            )

        if segmentation_type == 'months':

            end_of_months = get_last_bdays_of_months_between_two_dates(date_from, date_to)

            # _l.info(end_of_months)

            q = Q()

            for date in end_of_months:
                query = Q(**{'date': date})

                q = q | query

            balance_report_histories = balance_report_histories.filter(q)

            _l.info('balance_report_histories %s' % balance_report_histories.count())

        balance_report_histories = balance_report_histories.prefetch_related('items')

        items = []

        balance_report_histories = balance_report_histories.order_by('date')

        for history_item in balance_report_histories:

            result_item = {}

            result_item['date'] = str(history_item.date)
            result_item['nav'] = history_item.nav

            categories = []

            for item in history_item.items.all():

                if item.category not in categories:
                    categories.append(item.category)

            result_item['categories'] = []
            for category in categories:
                result_item['categories'].append({
                    "name": category,
                    "items": []
                })

            for item in history_item.items.all():

                for category in result_item['categories']:

                    if item.category == category['name']:
                        category['items'].append({
                            'name': item.name,
                            'key': item.key,
                            'value': item.value
                        })

            items.append(result_item)

        currency_object = Currency.objects.get(id=currency)
        pricing_policy_object = PricingPolicy.objects.get(id=pricing_policy)
        cost_method_object = CostMethod.objects.get(id=cost_method)

        portfolio_instance = Portfolio.objects.get(id__in=portfolio)

        portfolio_instance_json = {
            "id": portfolio_instance.id,
            "name": portfolio_instance.name,
            "user_code": portfolio_instance.user_code
        }

        result = {
            "date_from": str(date_from),
            "date_to": str(date_to),
            "segmentation_type": segmentation_type,
            "currency": currency,
            "currency_object": {
                "id": currency_object.id,
                "name": currency_object.name,
                "user_code": currency_object.user_code
            },
            "pricing_policy": pricing_policy,
            "pricing_policy_object": {
                "id": pricing_policy_object.id,
                "name": pricing_policy_object.name,
                "user_code": pricing_policy_object.user_code
            },
            "cost_method": cost_method,
            "cost_method_object": {
                "id": cost_method_object.id,
                "name": cost_method_object.name,
                "user_code": cost_method_object.user_code
            },
            "portfolio": portfolio,
            "portfolio_object": portfolio_instance_json,

            "items": items

        }

        return Response(result)


class HistoryPlViewSet(AbstractViewSet):

    def list(self, request):

        date_from = request.query_params.get('date_from', None)
        date_to = request.query_params.get('date_to', None)
        currency = request.query_params.get('currency', None)
        pricing_policy = request.query_params.get('pricing_policy', None)
        cost_method = request.query_params.get('cost_method', None)
        portfolio = request.query_params.get('portfolio', None)
        accounts = request.query_params.get('accounts', [])
        segmentation_type = request.query_params.get('segmentation_type', None)

        if not date_from:
            date_from = get_first_transaction(portfolio).accounting_date.strftime("%Y-%m-%d")

        if not date_to:
            date_to = get_closest_bday_of_yesterday(to_string=True)

        _l.info('date_from %s ' % date_from)
        _l.info('date_to %s ' % date_to)

        ecosystem_default = EcosystemDefault.objects.get(master_user=request.user.master_user)

        if not currency:
            currency = ecosystem_default.currency_id

        if not pricing_policy:
            pricing_policy = ecosystem_default.pricing_policy_id

        if not cost_method:
            cost_method = CostMethod.AVCO

        if not segmentation_type:
            segmentation_type = 'months'

        pl_report_histories = PLReportHistory.objects.filter(
            master_user=request.user.master_user,
            cost_method=cost_method,
            pricing_policy=pricing_policy,
            report_currency=currency
        )

        if not portfolio:
            raise ValidationError("Portfolio is not set")

        pl_report_histories = pl_report_histories.filter(portfolio=portfolio)

        if accounts:
            accounts = accounts.split(',')

            pl_report_histories = pl_report_histories.filter(accounts__in=accounts)

        if segmentation_type == 'days':
            pl_report_histories = pl_report_histories.filter(
                date__gte=date_from,
                date__lte=date_to
            )

        if segmentation_type == 'months':

            end_of_months = get_last_bdays_of_months_between_two_dates(date_from, date_to)

            q = Q()

            for date in end_of_months:
                query = Q(**{'date': date})

                q = q | query

            pl_report_histories = pl_report_histories.filter(
                q
            )

        pl_report_histories = pl_report_histories.prefetch_related('items')

        items = []

        for history_item in pl_report_histories:

            result_item = {}

            result_item['date'] = str(history_item.date)
            result_item['total'] = history_item.total

            categories = []

            for item in history_item.items.all():

                if item.category not in categories:
                    categories.append(item.category)

            result_item['categories'] = []
            for category in categories:
                result_item['categories'].append({
                    "name": category,
                    "items": []
                })

            for item in history_item.items.all():

                for category in result_item['categories']:

                    if item.category == category['name']:
                        category['items'].append({
                            'name': item.name,
                            'key': item.key,
                            'value': item.value
                        })

            items.append(result_item)

        currency_object = Currency.objects.get(id=currency)
        pricing_policy_object = PricingPolicy.objects.get(id=pricing_policy)
        cost_method_object = CostMethod.objects.get(id=cost_method)

        portfolio_instance = Portfolio.objects.get(id__in=portfolio)

        portfolio_instance_json = {
            "id": portfolio_instance.id,
            "name": portfolio_instance.name,
            "user_code": portfolio_instance.user_code
        }

        result = {
            "date_from": str(date_from),
            "date_to": str(date_to),
            "segmentation_type": segmentation_type,
            "currency": currency,
            "currency_object": {
                "id": currency_object.id,
                "name": currency_object.name,
                "user_code": currency_object.user_code
            },
            "pricing_policy": pricing_policy,
            "pricing_policy_object": {
                "id": pricing_policy_object.id,
                "name": pricing_policy_object.name,
                "user_code": pricing_policy_object.user_code
            },
            "cost_method": cost_method,
            "cost_method_object": {
                "id": cost_method_object.id,
                "name": cost_method_object.name,
                "user_code": cost_method_object.user_code
            },
            "portfolio": portfolio_instance.id,
            "portfolio_object": portfolio_instance_json,

            "items": items

        }

        return Response(result)


class StatsViewSet(AbstractViewSet):

    def list(self, request):
        date = request.query_params.get('date', None)
        portfolio = request.query_params.get('portfolio', None)
        benchmark = request.query_params.get('benchmark', 'sp_500')

        if not portfolio:
            raise ValidationError("Portfolio is required")

        _l.info("StatsViewSet.date %s" % date)
        _l.info("StatsViewSet.portfolio %s" % portfolio)

        widget = WidgetStats.objects.get(date=date, portfolio_id=portfolio, benchmark=benchmark)

        serializer = WidgetStatsSerializer(instance=widget)

        return Response(serializer.data)


class CollectHistoryViewSet(AbstractViewSet):
    serializer_class = CollectHistorySerializer

    def create(self, request):

        date_from = request.data.get('date_from', None)
        date_to = request.data.get('date_to', None)
        portfolio_id = request.data.get('portfolio', None)
        report_currency_id = request.data.get('currency', None)
        pricing_policy_id = request.data.get('pricing_policy', None)
        cost_method_id = request.data.get('cost_method', None)
        segmentation_type = request.data.get('segmentation_type', None)

        ecosystem_default = EcosystemDefault.objects.get(master_user=request.user.master_user)

        if not report_currency_id:
            report_currency_id = ecosystem_default.currency_id
        if not pricing_policy_id:
            pricing_policy_id = ecosystem_default.pricing_policy_id

        if not cost_method_id:
            cost_method_id = CostMethod.AVCO

        _l.info('CollectHistoryViewSet.segmentation_type %s' % segmentation_type)
        if not segmentation_type:
            segmentation_type = 'months'

        dates = []

        _l.info('CollectHistoryViewSet.date_from %s' % date_from)
        _l.info('CollectHistoryViewSet.date_to %s' % date_to)

        if segmentation_type == 'days':
            dates = get_list_of_business_days_between_two_dates(date_from, date_to, to_string=True)

        if segmentation_type == 'months':
            dates = get_last_bdays_of_months_between_two_dates(date_from, date_to, to_string=True)
            _l.info('CollectHistoryViewSet.create: dates %s' % dates)

        if len(dates) == 0:
            raise ValidationError("No buisness days in range %s to %s" % (date_from, date_to))

        if len(dates) > 365:
            raise ValidationError("Date range exceeded max limit of 365 days")

        collect_balance_history(request.user.master_user,
                                request.user.member,
                                date_from,
                                date_to,
                                dates,
                                segmentation_type, portfolio_id, report_currency_id,
                                cost_method_id, pricing_policy_id)
        collect_pl_history(request.user.master_user,
                           request.user.member,
                           date_from,
                           date_to,
                           dates,
                           segmentation_type,
                           portfolio_id, report_currency_id, cost_method_id,
                           pricing_policy_id)

        return Response({
            'status': 'ok'
        })


class CollectStatsViewSet(AbstractViewSet):
    serializer_class = CollectStatsSerializer

    def create(self, request):
        date_from = request.data.get('date_from', None)
        date_to = request.data.get('date_to', None)
        portfolio_id = request.data.get('portfolio', None)
        benchmark = request.data.get('benchmark', None)
        segmentation_type = request.data.get('segmentation_type', None)

        if not segmentation_type:
            segmentation_type = 'months'


        if not portfolio_id:
            raise ValidationError("Portfolio is not set")

        if not benchmark:
            benchmark = 'sp_500'

        dates = []

        _l.info('CollectHistoryViewSet.date_from %s' % date_from)
        _l.info('CollectHistoryViewSet.date_to %s' % date_to)

        if segmentation_type == 'days':
            dates = get_list_of_business_days_between_two_dates(date_from, date_to, to_string=True)

        if segmentation_type == 'months':
            dates = get_last_bdays_of_months_between_two_dates(date_from, date_to, to_string=True)
            _l.info('CollectHistoryViewSet.create: dates %s' % dates)

        if len(dates) == 0:
            raise ValidationError("No buisness days in range %s to %s" % (date_from, date_to))

        if len(dates) > 365:
            raise ValidationError("Date range exceeded max limit of 365 days")

        collect_widget_stats(request.user.master_user,
                             request.user.member,
                             date_from,
                             date_to,
                             dates,
                             portfolio_id, benchmark)

        return Response({
            'status': 'ok'
        })
