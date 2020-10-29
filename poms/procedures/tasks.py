from celery import shared_task
from django.conf import settings
import requests
import json

from poms.integrations.tasks import complex_transaction_csv_file_import_from_transaction_file

from poms.procedures.models import RequestDataFileProcedureInstance

import logging
_l = logging.getLogger('poms.procedures')


@shared_task(name='procedures.procedure_request_data_file', bind=True, ignore_result=True)
def procedure_request_data_file(self, procedure_instance, transaction_file_result, data):

    try:

        url = settings.DATA_FILE_SERVICE_URL + '/' + self.procedure.provider.user_code + '/getfile'

        headers = {'Content-type': 'application/json', 'Accept': 'application/json'}

        response = None

        _l.info('url %s' % url)

        response = requests.post(url=url, data=json.dumps(data), headers=headers)

        _l.info('response %s' % response)
        _l.info('response text %s' % response.text)

        if response.status_code == 200:

            procedure_instance.save()

            data = response.json()

            if data['files'] and len(data['files']):
                transaction_file_result.file = data['files'][0]["path"]

                transaction_file_result.save()

                _l.info("Run data file import from response")
                complex_transaction_csv_file_import_from_transaction_file.apply_async(kwargs={'transaction_file': transaction_file_result.file, 'master_user': self.master_user})

        else:
            procedure_instance.status = RequestDataFileProcedureInstance.STATUS_ERROR
            procedure_instance.save()

        _l.info("procedure instance saved %s" % procedure_instance)

    except Exception as e:
        _l.info("Can't send request to Data File Service. Is Transaction File Service offline?")
        _l.info("Error %s" % e)

        procedure_instance.status = RequestDataFileProcedureInstance.STATUS_ERROR
        procedure_instance.save()

        raise Exception("Data File Service is unavailable")
