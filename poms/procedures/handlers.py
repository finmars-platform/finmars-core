
from django.conf import settings

from poms.common import formula
from poms.common.crypto.RSACipher import RSACipher
from poms.credentials.models import Credentials

from poms.integrations.models import TransactionFileResult

import logging

from poms.procedures.models import RequestDataFileProcedureInstance
from poms.procedures.tasks import procedure_request_data_file


from django.db import transaction

from poms.system_messages.handlers import send_system_message

_l = logging.getLogger('poms.procedures')


class RequestDataFileProcedureProcess(object):

    def __init__(self, procedure=None, master_user=None, member=None, schedule_instance=None):

        _l.debug('RequestDataFileProcedureProcess. Master user: %s. Procedure: %s' % (master_user, procedure))

        self.master_user = master_user
        self.procedure = procedure

        self.member = member
        self.schedule_instance = schedule_instance

        self.execute_procedure_date_expressions()

    def execute_procedure_date_expressions(self):

        if self.procedure.date_from_expr:
            try:
                self.procedure.date_from = formula.safe_eval(self.procedure.date_from_expr, names={})
            except formula.InvalidExpression as e:
                _l.debug("Cant execute date from expression %s " % e)

        if self.procedure.date_to_expr:
            try:
                self.procedure.date_to = formula.safe_eval(self.procedure.date_to_expr, names={})
            except formula.InvalidExpression as e:
                _l.debug("Cant execute date to expression %s " % e)

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

                rsa_cipher = RSACipher()
                private_key, public_key = rsa_cipher.createKey()

                procedure_instance.private_key = private_key
                procedure_instance.public_key = public_key

                procedure_instance.save()

                _l.debug("RequestDataFileProcedureInstance procedure_instance created id: %s" % procedure_instance.id)

            _l.debug("RequestDataFileProcedureProcess: Request_transaction_file. Master User: %s. Provider: %s, Scheme name: %s" % (self.master_user, self.procedure.provider, self.procedure.scheme_name) )

            item = TransactionFileResult.objects.create(
                procedure_instance=procedure_instance,
                master_user=self.master_user,
                provider=self.procedure.provider,
                scheme_name=self.procedure.scheme_name,
            )

            item.save()

            params = {}

            if self.procedure.provider.user_code == 'email_provider':

                if self.procedure.data:

                    if 'sender' in self.procedure.data and self.procedure.data['sender']:
                        params['sender'] = self.procedure.data['sender']

                    if 'filename' in self.procedure.data and self.procedure.data['filename']:
                        params['filename'] = self.procedure.data['filename']

                    if 'subject' in self.procedure.data and self.procedure.data['subject']:
                        params['subject'] = self.procedure.data['subject']

                    if 'hasNoDelete' in self.procedure.data:

                        if self.procedure.data['hasNoDelete']: # pain
                            params['hasNoDelete'] = 'true'
                        else:
                            params['hasNoDelete'] = 'false'
                else:
                    send_system_message(master_user=self.master_user,
                                        source="Data File Procedure Service",
                                        text="Email Provider Procedure is not configured")

            if self.procedure.provider.user_code == 'julius_baer':

                try:

                    credentials = Credentials.objects.get(master_user=self.master_user, provider=self.procedure.provider)

                    params['sftpuser'] = credentials.username
                    params['sftpkeypath'] = credentials.path_to_private_key

                except Exception as error:
                    send_system_message(master_user=self.master_user,
                                        source="Data File Procedure Service",
                                        text="Can't configure Julius Baer Provider")

            if self.procedure.provider.user_code == 'lombard_odier':

                try:

                    credentials = Credentials.objects.get(master_user=self.master_user, provider=self.procedure.provider)

                    params['sftpuser'] = credentials.username
                    params['sftppassword'] = credentials.password

                    if self.procedure.data:

                        if 'archivepassword' in self.procedure.data and self.procedure.data['archivepassword']:
                            params['archivepassword'] = self.procedure.data['archivepassword']

                    else:
                        send_system_message(master_user=self.master_user,
                                            source="Data File Procedure Service",
                                            text="Lombard Odier Provider Procedure is not configured")

                except Exception as error:
                    send_system_message(master_user=self.master_user,
                                    source="Data File Procedure Service",
                                    text="Can't configure Lombard Odier Provider")

            if self.procedure.provider.user_code == 'revolut':

                if self.procedure.data:

                    if 'code' in self.procedure.data and self.procedure.data['code']:
                        params['code'] = self.procedure.data['code']

                    if 'issuer' in self.procedure.data and self.procedure.data['issuer']:
                        params['issuer'] = self.procedure.data['issuer']

                    if 'client_id' in self.procedure.data and self.procedure.data['client_id']:
                        params['client_id'] = self.procedure.data['client_id']

                    if 'jwt' in self.procedure.data and self.procedure.data['jwt']:
                        params['jwt'] = self.procedure.data['jwt']

                else:
                    send_system_message(master_user=self.master_user,
                                        source="Data File Procedure Service",
                                        text="Revolut rovider Procedure is not configured")

            data = {
                "id": procedure_instance.id,
                "user": {
                    "token": self.master_user.token,
                    "credentials": {},
                    "params": params
                },
                "public_key": public_key,
                # "date_from": self.procedure.date_from,
                # "date_to": self.procedure.date_to,
                "provider": self.procedure.provider.user_code,
                "scheme_name": self.procedure.scheme_name,
                "scheme_type": self.procedure.scheme_type,

                "files": [],
                "error_status": 0,
                "error_message": ""
            }

            # internal/data/transactions/callback

            if self.procedure.date_from:
                data["date_from"] = str(self.procedure.date_from)

            if self.procedure.date_to:
                data["date_to"] = str(self.procedure.date_to)

            _l.debug("Executing procedure_request_data_file")
            procedure_request_data_file.apply_async(kwargs={
                                                            'master_user': self.master_user,
                                                            'procedure_instance': procedure_instance,
                                                            'transaction_file_result': item,
                                                            'data': data})

        else:
            _l.debug('DATA_FILE_SERVICE_URL is not set')

            send_system_message(master_user=self.master_user,
                                source="Data File Procedure Service",
                                text="Data Service is unknown")
