
from celery import shared_task
from django.utils import timezone
from django.conf import settings

import logging
import json

from poms.integrations.models import TransactionFileResult
from poms.pricing.handlers import PricingProcedureProcess
from poms.schedules.models import PricingSchedule, TransactionFileDownloadSchedule

import requests

_l = logging.getLogger('poms.schedules')

@shared_task(name='schedules.process_pricing_procedure_async', bind=True, ignore_result=True)
def process_pricing_procedure_async(self, procedure, master_user):

    _l.info("PricingSchedule: Subprocess process_pricing_procedure_async. Master User: %s. Procedure: %s" % (master_user, procedure) )

    instance = PricingProcedureProcess(procedure=procedure, master_user=master_user)
    from time import sleep
    from random import randint

    # val = randint(5, 10)
    #
    # _l.info("PricingSchedule: Sleep for %s seconds" % val)

    # sleep(val)
    instance.process()


@shared_task(name='schedules.auto_process_pricing_procedures_schedules', bind=True, ignore_result=True)
def auto_process_pricing_procedures_schedules(self):

    schedule_qs = PricingSchedule.objects.select_related('master_user').filter(
        is_enabled=True, next_run_at__lte=timezone.now()
    )

    if schedule_qs.count():
        _l.info('PricingSchedule: Schedules initialized: %s', schedule_qs.count())

    # TODO tmp limit

    procedures_count = 0

    for s in schedule_qs:

        master_user = s.master_user

        with timezone.override(master_user.timezone or settings.TIME_ZONE):
            next_run_at = timezone.localtime(s.next_run_at)
            s.schedule(save=True)

            _l.info('PricingSchedule: master_user=%s, next_run_at=%s. STARTED',
                    master_user.id, s.next_run_at)

            _l.info('PricingSchedule: count %s' % len(s.pricing_procedures.all()))

            for procedure in s.pricing_procedures.all():

                try:

                    process_pricing_procedure_async.apply_async(kwargs={'procedure':procedure, 'master_user':master_user})

                    _l.info('PricingSchedule: master_user=%s, next_run_at=%s. PROCESSED',
                            master_user.id, s.next_run_at)

                    procedures_count = procedures_count + 1

                except Exception as e:

                    _l.info('PricingSchedule: master_user=%s, next_run_at=%s. Error',
                            master_user.id, s.next_run_at)

                    _l.info('PricingSchedule: Error %s' % e)

                    pass

        s.last_run_at = timezone.now()
        s.save(update_fields=['last_run_at'])

    if procedures_count:
        _l.info('PricingSchedule: Finished. Procedures initialized: %s' % procedures_count)


@shared_task(name='schedules.process_pricing_procedures_schedules', bind=True, ignore_result=True)
def process_pricing_procedures_schedules(self, schedules):

    if len(schedules):
        _l.info('PricingSchedule: Schedules initialized: %s', len(schedules))

    procedures_count = 0

    for s in schedules:

        master_user = s.master_user

        with timezone.override(master_user.timezone or settings.TIME_ZONE):
            next_run_at = timezone.localtime(s.next_run_at)
            s.schedule(save=True)

            _l.info('PricingSchedule: master_user=%s, next_run_at=%s. STARTED',
                    master_user.id, s.next_run_at)

            _l.info('PricingSchedule: count %s' % len(s.pricing_procedures.all()))

            for procedure in s.pricing_procedures.all():

                try:

                    process_pricing_procedure_async.apply_async(kwargs={'procedure':procedure, 'master_user':master_user})

                    _l.info('PricingSchedule: master_user=%s, next_run_at=%s. PROCESSED',
                            master_user.id, s.next_run_at)

                    procedures_count = procedures_count + 1

                except Exception as e:

                    _l.info('PricingSchedule: master_user=%s, next_run_at=%s. Error',
                            master_user.id, s.next_run_at)

                    _l.info('PricingSchedule: Error %s' % e)

                    pass

        s.last_run_at = timezone.now()
        s.save(update_fields=['last_run_at'])

    if procedures_count:
        _l.info('PricingSchedule: Finished. Procedures initialized: %s' % procedures_count)


## Transaction File


@shared_task(name='schedules.process_pricing_procedure_async', bind=True, ignore_result=True)
def process_request_transaction_file_async(self, provider, scheme_name, master_user):

    if settings.TRANSACTION_FILE_SERVICE_URL:

        _l.info("TransactionFileDownloadSchedule: Subprocess process_request_transaction_file_async. Master User: %s. Provider: %s, Scheme name: %s" % (master_user, provider, scheme_name) )

        item = TransactionFileResult.objects.create(
            master_user=master_user,
            provider=provider,
            scheme_name=scheme_name,
        )

        data = {
            "id": item.id,
            "user": {
                "token": master_user.token
            },
            "provider": provider,
            "scheme_name": scheme_name
        }

        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}

        response = None

        try:

            response = requests.post(url=settings.TRANSACTION_FILE_SERVICE_URL, data=json.dumps(data), headers=headers)

        except Exception:
            _l.info("Can't send request to Transaction File Service. Is Transaction File Service offline?")

            raise Exception("Transaction File Service is unavailable")

    else:
        _l.info('TRANSACTION_FILE_SERVICE_URL is not set')


@shared_task(name='schedules.request_transaction_files_schedules', bind=True, ignore_result=True)
def request_transaction_files_schedules(self):

    schedule_qs = TransactionFileDownloadSchedule.objects.select_related('master_user').filter(
        is_enabled=True, next_run_at__lte=timezone.now()
    )

    if schedule_qs.count():
        _l.info('PricingSchedule: Schedules initialized: %s', schedule_qs.count())

    # TODO tmp limit


    for s in schedule_qs:

        master_user = s.master_user

        with timezone.override(master_user.timezone or settings.TIME_ZONE):
            next_run_at = timezone.localtime(s.next_run_at)
            s.schedule(save=True)

            _l.info('PricingSchedule: master_user=%s, next_run_at=%s. STARTED',
                    master_user.id, s.next_run_at)

            process_request_transaction_file_async.apply_async(kwargs={'provider': s.provider, 'scheme_name': s.scheme_name, 'master_user':master_user})

        s.last_run_at = timezone.now()
        s.save(update_fields=['last_run_at'])




