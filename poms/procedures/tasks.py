import logging

import requests
from celery import shared_task
from django.conf import settings

from poms.common.models import ProxyUser, ProxyRequest
from poms.procedures.models import RequestDataFileProcedureInstance
from poms.system_messages.handlers import send_system_message

_l = logging.getLogger('poms.procedures')


@shared_task(name='procedures.procedure_request_data_file', bind=True, ignore_result=True)
def procedure_request_data_file(self,
                                master_user,
                                procedure_instance,
                                transaction_file_result,
                                data):
    _l.debug('procedure_request_data_file processing')
    _l.debug('procedure_request_data_file procedure %s' % procedure_instance)
    _l.debug('procedure_request_data_file transaction_file_result %s' % transaction_file_result)
    _l.debug('procedure_request_data_file data %s' % data)

    try:

        url = settings.DATA_FILE_SERVICE_URL + '/' + procedure_instance.procedure.provider.user_code + '/getfile'

        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}

        response = None

        _l.debug('url %s' % url)

        procedure_instance.request_data = data

        try:
            response = requests.post(url=url, json=data, headers=headers, verify=settings.VERIFY_SSL)
        except requests.exceptions.ReadTimeout:
            _l.debug('Will not wait response')
            return
        _l.debug('response %s' % response)
        _l.debug('response text %s' % response.text)

        if response.status_code == 200:

            procedure_instance.save()

            data = response.json()

            if 'error_message' in data:

                if data['error_message']:
                    text = "Data File Procedure %s. Error during request to Data Service. Error Message: %s" % (
                        procedure_instance.procedure.user_code, data['error_message'])

                    send_system_message(master_user=master_user,
                                        performed_by='System',
                                        type='error',
                                        description=text)

                    procedure_instance.status = RequestDataFileProcedureInstance.STATUS_ERROR
                    procedure_instance.save()

        else:

            text = "Data File Procedure %s. Error during request to Data Service" % (
                procedure_instance.procedure.user_code)

            send_system_message(master_user=master_user,
                                performed_by='System',
                                type='error',
                                description=text)

            procedure_instance.status = RequestDataFileProcedureInstance.STATUS_ERROR
            procedure_instance.save()

        _l.debug("procedure instance saved %s" % procedure_instance)

    except Exception as e:
        _l.debug("Can't send request to Data File Service. Is Transaction File Service offline?")
        _l.debug("Error %s" % e)

        text = "Data File Procedure %s. Data Service is offline" % (
            procedure_instance.procedure.user_code)

        send_system_message(master_user=master_user,
                            performed_by='System',
                            type='error',
                            description=text)

        procedure_instance.status = RequestDataFileProcedureInstance.STATUS_ERROR
        procedure_instance.save()

        raise Exception("Data File Service is unavailable")


@shared_task(name='procedures.run_data_procedure_from_formula', bind=True)
def run_data_procedure_from_formula(self, master_user_id, member_id, user_code, user_context, **kwargs):
    _l.info('run_data_procedure_from_formula init')

    from poms.users.models import MasterUser
    from poms.users.models import Member
    from poms.procedures.models import RequestDataFileProcedure

    master_user = MasterUser.objects.get(id=master_user_id)

    member = Member.objects.get(id=member_id)

    proxy_user = ProxyUser(member, master_user)
    proxy_request = ProxyRequest(proxy_user)

    context = {
        'request': proxy_request
    }

    merged_context = {}
    merged_context.update(context)

    if user_context:
        if 'names' not in merged_context:
            merged_context['names'] = {}

        merged_context['names'].update(user_context)

    procedure = RequestDataFileProcedure.objects.get(master_user=master_user, user_code=user_code)

    kwargs.pop('user_context', None)

    from poms.procedures.handlers import DataProcedureProcess
    instance = DataProcedureProcess(procedure=procedure, master_user=master_user, member=member,
                                    context=merged_context, **kwargs)
    instance.process()
