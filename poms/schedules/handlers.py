
from django.conf import settings
import requests
import json


from poms.integrations.models import TransactionFileResult

import logging
_l = logging.getLogger('poms.shedules')


class RequestDataFileProcedureProcess(object):

    def __init__(self, procedure=None, master_user=None):

        _l.info('RequestDataFileProcedureProcess. Master user: %s. Procedure: %s' % (master_user, procedure))

        self.master_user = master_user
        self.procedure = procedure

    def process(self):

        if settings.DATA_FILE_SERVICE_URL:

            _l.info("RequestDataFileProcedureProcess: Subprocess process_request_transaction_file_async. Master User: %s. Provider: %s, Scheme name: %s" % (master_user, provider, scheme_name) )

            item = TransactionFileResult.objects.create(
                master_user=self.master_user,
                provider=self.procedure.provider,
                scheme_name=self.procedure.scheme_name,
            )

            data = {
                "id": item.id,
                "user": {
                    "token": self.master_user.token,
                    "credentials": {}
                },
                "date_from": self.procedure.date_from,
                "date_to": self.procedure.date_to,
                "provider": self.procedure.provider,
                "scheme_name": self.procedure.scheme_name,
                "files": [
                    {"host": "sftp", "path": "SNAP"}
                ]
            }

            headers = {'Content-type': 'application/json', 'Accept': 'application/json'}

            response = None

            try:

                response = requests.post(url=settings.DATA_FILE_SERVICE_URL, data=json.dumps(data), headers=headers)

            except Exception:
                _l.info("Can't send request to Data File Service. Is Transaction File Service offline?")

                raise Exception("Data File Service is unavailable")

        else:
            _l.info('DATA_FILE_SERVICE_URL is not set')
