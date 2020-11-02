
from django.conf import settings

from poms.common import formula
from poms.common.crypto.RSACipher import RSACipher

from poms.integrations.models import TransactionFileResult

import logging

from poms.procedures.models import RequestDataFileProcedureInstance
from poms.procedures.tasks import procedure_request_data_file


from django.db import transaction

from poms.system_messages.handlers import send_system_message

_l = logging.getLogger('poms.procedures')


class RequestDataFileProcedureProcess(object):

    def __init__(self, procedure=None, master_user=None, member=None, schedule_instance=None):

        _l.info('RequestDataFileProcedureProcess. Master user: %s. Procedure: %s' % (master_user, procedure))

        self.master_user = master_user
        self.procedure = procedure

        self.member = member
        self.schedule_instance = schedule_instance

        self.execute_procedure_date_expressions()

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

            with transaction.atomic():

                procedure_instance = RequestDataFileProcedureInstance.objects.create(procedure=self.procedure,
                                                                      master_user=self.master_user,
                                                                      status=RequestDataFileProcedureInstance.STATUS_PENDING,

                                                                      action='request_transaction_file',
                                                                      provider='finmars',

                                                                      action_verbose='Request file with Transactions',
                                                                      provider_verbose='Finmars'

                                                                      )

                if self.member:
                    procedure_instance.started_by = RequestDataFileProcedureInstance.STARTED_BY_MEMBER
                    procedure_instance.member = self.member

                if self.schedule_instance:
                    procedure_instance.started_by = RequestDataFileProcedureInstance.STARTED_BY_SCHEDULE
                    procedure_instance.schedule_instance = self.schedule_instance

                procedure_instance.save()

                _l.info("RequestDataFileProcedureInstance procedure_instance created id: %s" % procedure_instance.id)

            _l.info("RequestDataFileProcedureProcess: Request_transaction_file. Master User: %s. Provider: %s, Scheme name: %s" % (self.master_user, self.procedure.provider, self.procedure.scheme_name) )

            item = TransactionFileResult.objects.create(
                procedure_instance=procedure_instance,
                master_user=self.master_user,
                provider=self.procedure.provider,
                scheme_name=self.procedure.scheme_name,
            )

            item.save()


            rsa_cipher = RSACipher()
            private_key, public_key = rsa_cipher.createKey()

            procedure_instance.private_key = private_key
            procedure_instance.public_key = public_key

            procedure_instance.save()

            data = {
                "id": procedure_instance.id,
                "user": {
                    "token": self.master_user.token,
                    "credentials": {},
                    "params": {},
                },
                "public_key": public_key,
                # "date_from": self.procedure.date_from,
                # "date_to": self.procedure.date_to,
                "provider": self.procedure.provider.user_code,
                "scheme_name": self.procedure.scheme_name,
                "files": [],
                "error_status": 0,
                "error_message": ""
            }

            _l.info("Executing procedure_request_data_file")
            procedure_request_data_file.apply_async(kwargs={
                                                            'master_user': self.master_user,
                                                            'procedure_instance': procedure_instance,
                                                            'transaction_file_result': item,
                                                            'data': data})

        else:
            _l.info('DATA_FILE_SERVICE_URL is not set')

            send_system_message(master_user=self.master_user,
                                source="Data File Procedure Service",
                                text="Data Service is unknown")
