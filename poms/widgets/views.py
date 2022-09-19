import datetime

from poms.celery_tasks.models import CeleryTask
from poms.common.utils import get_list_of_dates_between_two_dates, check_if_last_day_of_month
from poms.common.views import AbstractViewSet
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.db import transaction

from poms.instruments.models import CostMethod
from poms.system_messages.handlers import send_system_message
from poms.users.models import EcosystemDefault
from poms.widgets.models import BalanceReportHistory
from poms.widgets.serializers import CollectHistorySerializer
from poms.widgets.tasks import collect_balance_report_history


class HistoryNavViewSet(AbstractViewSet):

    def list(self, request):

        date_from = request.query_params.get('date_from', None)
        date_to = request.query_params.get('date_to', None)
        currency = request.query_params.get('currency', None)
        pricing_policy = request.query_params.get('pricing_policy', None)
        cost_method = request.query_params.get('cost_method', None)
        portfolios = request.query_params.get('portfolios', None)
        accounts = request.query_params.get('accounts', None)
        segmentation_type = request.query_params.get('segmentation_type', None)

        if not date_from:
            raise ValidationError({"error_message": "Date from is not set"})

        if not date_to:
            raise ValidationError({"error_message": "Date to is not set"})

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

        if portfolios:
            portfolios = portfolios.split(',')

            balance_report_histories = balance_report_histories.filter(portfolios__in=portfolios)

        if accounts:
            accounts = accounts.split(',')

            balance_report_histories = balance_report_histories.filter(accounts__in=accounts)

        if segmentation_type == 'days':
            balance_report_histories = balance_report_histories.filter(
                date__gte=date_from,
                date__lte=date_to
            )

        if segmentation_type == 'months':
            end_of_months = []

            dates = get_list_of_dates_between_two_dates(date_from, date_to, to_string=True)

            for date in dates:

                d = datetime.datetime.strptime(date_from, "%Y-%m-%d").date()

                if check_if_last_day_of_month(d):
                    end_of_months.append(date)

            balance_report_histories = balance_report_histories.filter(
                date__in=end_of_months
            )

        balance_report_histories = balance_report_histories.prefetch_related('items')

        items = []

        for history_item in balance_report_histories:

            result_item = {}

            result_item['date'] = str(history_item['date'])
            result_item['nav'] = history_item['nav']

            categories = []

            for item in history_item.items:

                if item.category not in categories:
                    categories.append(item.category)

            result_item['categories'] = []
            for category in categories:
                result_item['categories'].append({
                    "name": category,
                    "items": []
                })

            for item in history_item.items:

                for category in result_item['categories']:

                    if item.category == category['name']:
                        category['items'].append({
                            'name': item['name'],
                            'key': item['key'],
                            'value': item['value']
                        })

            items.append(history_item)

        result = {

            "items": items

        }

        return Response(result)


class StatsViewSet(AbstractViewSet):

    def list(self, request):
        result = {

        }

        return Response(result)


class CollectHistoryViewSet(AbstractViewSet):
    serializer_class = CollectHistorySerializer

    def create(self, request):

        date_from = request.data.get('date_from', None)
        date_to = request.data.get('date_to', None)
        portfolios = request.data.get('portfolios', None)
        accounts = request.data.get('accounts', None)
        report_currency_id = request.data.get('report_currency', None)
        pricing_policy_id = request.data.get('pricing_policy', None)
        cost_method_id = request.data.get('cost_method', CostMethod.AVCO)

        if portfolios and isinstance(portfolios, str):
            portfolios = portfolios.split(',')

        if accounts and isinstance(accounts, str):
            accounts = accounts.split(',')

        ecosystem_default = EcosystemDefault.objects.get(master_user=request.user.master_user)

        if not report_currency_id:
            report_currency_id = ecosystem_default.currency_id
        if not pricing_policy_id:
            pricing_policy_id = ecosystem_default.pricing_policy_id

        parent_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            type='collect_history_chain',
        )

        dates = get_list_of_dates_between_two_dates(date_from, date_to, to_string=True)

        parent_task_options_object = {
            'date_from': date_from,
            'date_to': date_to,
            'portfolios': portfolios,
            'accounts': accounts,
            'report_currency_id': report_currency_id,
            'cost_method_id': cost_method_id,
            'pricing_policy_id': pricing_policy_id,
            'dates_to_process': dates,
            'error_dates': [],
            'processed_dates': []
        }

        parent_task.options_object = parent_task_options_object
        parent_task.save()

        celery_task = CeleryTask.objects.create(
            master_user=request.user.master_user,
            member=request.user.member,
            type='collect_history',
            parent=parent_task
        )

        options_object = {
            "report_date": date_from,
            "accounts": accounts,
            "portfolios": portfolios,
            "report_currency_id": report_currency_id,
            'cost_method_id': cost_method_id,
            'pricing_policy_id': pricing_policy_id,
        }

        celery_task.options_object = options_object

        celery_task.save()

        transaction.on_commit(lambda: collect_balance_report_history.apply_async(kwargs={'task_id': celery_task.id}))

        send_system_message(master_user=parent_task.master_user,
                            performed_by=parent_task.member.username,
                            section='schedules',
                            type='info',
                            title='Balance History is start collecting',
                            description='Balance History from %s to %s will be soon available' % (
                            parent_task_options_object['date_from'], parent_task_options_object['date_to']),
                            )

        return Response({
            'status': 'ok'
        })
