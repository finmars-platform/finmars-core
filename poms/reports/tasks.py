import logging
import time

from celery import shared_task
from django.db import transaction

from poms.reports.builders.balance_pl import ReportBuilder
from poms.reports.builders.cash_flow_projection import CashFlowProjectionReportBuilder
from poms.reports.builders.performance import PerformanceReportBuilder
from poms.reports.builders.transaction import TransactionReportBuilder

_l = logging.getLogger('poms.reports')


# curl -X POST --user a:a  http://127.0.0.1:8000/api/v1/reports/transaction-report/?format=json  -v -o /dev/null


class FakeRequest:
    def __init__(self, master_user, member):
        self.user = member.user
        self.user.member = member
        self.user.master_user = master_user


print('Celery')

@shared_task(name='reports.balance_report')
def balance_report(instance):
    print('Celery balance report task')

    _l.debug('balance_report: %s', instance)

    st = time.perf_counter()

    with transaction.atomic():
        try:
            builder = ReportBuilder(instance=instance)
            instance = builder.build_balance()
            # instance.transactions = None
            return instance
        except:
            _l.error('balance report failed', exc_info=True)
            raise
        finally:
            transaction.set_rollback(True)
            # _l.debug('finished')
            _l.debug('balance_report finished: %s', (time.perf_counter() - st))


@shared_task(name='reports.pl_report')
def pl_report(instance):
    _l.debug('pl_report: %s', instance)
    with transaction.atomic():
        try:
            builder = ReportBuilder(instance=instance)
            instance = builder.build_pl()
            # instance.transactions = None
            return instance
        except:
            _l.error('pl report failed', exc_info=True)
            raise
        finally:
            transaction.set_rollback(True)
            _l.debug('finished')


@shared_task(name='reports.transaction_report')
def transaction_report(instance):
    _l.debug('transaction_report: >')
    with transaction.atomic():
        try:
            builder = TransactionReportBuilder(instance)
            builder.build()
            # instance.transactions = None
            return builder.instance
        except:
            _l.error('transaction report failed', exc_info=True)
            raise
        finally:
            transaction.set_rollback(True)
            _l.debug('transaction_report: <')


@shared_task(name='reports.cash_flow_projection_report')
def cash_flow_projection_report(instance):
    _l.debug('cash_flow_projection_report: >')
    with transaction.atomic():
        try:
            builder = CashFlowProjectionReportBuilder(instance)
            builder.build()
            # instance.transactions = None
            return builder.instance
        except:
            _l.error('cash flow projection report failed', exc_info=True)
            raise
        finally:
            transaction.set_rollback(True)
            _l.debug('cash_flow_projection_report: <')


@shared_task(name='reports.performance_report')
def performance_report(instance):
    _l.debug('performance_report: >')
    with transaction.atomic():
        try:
            builder = PerformanceReportBuilder(instance)
            builder.build_performance()
            # instance.transactions = None
            return builder.instance
        except:
            _l.error('performance report failed', exc_info=True)
            raise
        finally:
            transaction.set_rollback(True)
            _l.debug('performance_report: <')
