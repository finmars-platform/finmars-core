
from django.conf import settings
import requests
import json
from poms.common import formula

from poms.integrations.models import TransactionFileResult

import logging

from poms.procedures.models import RequestDataFileProcedureInstance

_l = logging.getLogger('poms.procedures')


class RequestDataFileProcedureProcess(object):

    def __init__(self, procedure=None, master_user=None):

        _l.info('RequestDataFileProcedureProcess. Master user: %s. Procedure: %s' % (master_user, procedure))

        self.execute_procedure_date_expressions()

        self.master_user = master_user
        self.procedure = procedure

    def execute_procedure_date_expressions(self):

        if self.procedure.price_date_from_expr:
            try:
                self.procedure.price_date_from = formula.safe_eval(self.procedure.price_date_from_expr, names={})
            except formula.InvalidExpression as e:
                _l.info("Cant execute price date from expression %s " % e)

        if self.procedure.price_date_to_expr:
            try:
                self.procedure.price_date_to = formula.safe_eval(self.procedure.price_date_to_expr, names={})
            except formula.InvalidExpression as e:
                _l.info("Cant execute price date to expression %s " % e)

    def process(self):

        if settings.DATA_FILE_SERVICE_URL:

            procedure_instance = RequestDataFileProcedureInstance(procedure=self.procedure,
                                                                  master_user=self.master_user,
                                                                  status=RequestDataFileProcedureInstance.STATUS_PENDING
                                                                  )

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
                # "date_from": self.procedure.date_from,
                # "date_to": self.procedure.date_to,
                "provider": self.procedure.provider.user_code,
                "scheme_name": self.procedure.scheme_name,
                "files": [],
                "params": {},
                "error_status": 0,
                "error_message": ""
            }

            headers = {'Content-type': 'application/json', 'Accept': 'application/json'}

            response = None

            try:

                url = settings.DATA_FILE_SERVICE_URL + '/' + self.procedure.provider.user_code + '/getfile'

                _l.info('url', url)

                response = requests.post(url=url, data=json.dumps(data), headers=headers)

                procedure_instance.save()

            except Exception:
                _l.info("Can't send request to Data File Service. Is Transaction File Service offline?")

                procedure_instance.status = RequestDataFileProcedureInstance.STATUS_ERROR
                procedure_instance.save()

                raise Exception("Data File Service is unavailable")

        else:
            _l.info('DATA_FILE_SERVICE_URL is not set')
