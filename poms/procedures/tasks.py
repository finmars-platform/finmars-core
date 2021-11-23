from celery import shared_task
from django.conf import settings
import requests
import json

from poms.integrations.tasks import complex_transaction_csv_file_import_by_procedure
from poms.csv_import.tasks import data_csv_file_import_by_procedure

from poms.procedures.models import RequestDataFileProcedureInstance

import logging

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

        response = requests.post(url=url, json=data, headers=headers)

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
                                        source="Data File Procedure Service",
                                        text=text)

                    procedure_instance.status = RequestDataFileProcedureInstance.STATUS_ERROR
                    procedure_instance.save()


            #
            # if data['files'] and len(data['files']):
            #
            #     procedure_instance.symmetric_key = data['files'][0]['symmetric_key']
            #     procedure_instance.save()
            #
            #     transaction_file_result.file_path = data['files'][0]["path"]
            #
            #     transaction_file_result.save()
            #
            #     if procedure_instance.procedure.scheme_type == 'transaction_import':
            #
            #         _l.debug("Run Transaction import from response")
            #         complex_transaction_csv_file_import_by_procedure.apply_async(kwargs={'procedure_instance': procedure_instance,
            #                                                                             'transaction_file_result': transaction_file_result,
            #                                                                               })
            #     if procedure_instance.procedure.scheme_type == 'simple_import':
            #
            #         _l.debug("Run Simple import from response")
            #         data_csv_file_import_by_procedure.apply_async(kwargs={'procedure_instance': procedure_instance,
            #                                                                              'transaction_file_result': transaction_file_result,
            #                                                                              })


        else:

            text = "Data File Procedure %s. Error during request to Data Service" % (
                procedure_instance.procedure.user_code)

            send_system_message(master_user=master_user,
                                source="Data File Procedure Service",
                                text=text)

            procedure_instance.status = RequestDataFileProcedureInstance.STATUS_ERROR
            procedure_instance.save()

        _l.debug("procedure instance saved %s" % procedure_instance)

    except Exception as e:
        _l.debug("Can't send request to Data File Service. Is Transaction File Service offline?")
        _l.debug("Error %s" % e)

        text = "Data File Procedure %s. Data Service is offline" % (
            procedure_instance.procedure.user_code)

        send_system_message(master_user=master_user,
                            source="Data File Procedure Service",
                            text=text)

        procedure_instance.status = RequestDataFileProcedureInstance.STATUS_ERROR
        procedure_instance.save()

        raise Exception("Data File Service is unavailable")
