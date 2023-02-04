import json
import logging
import traceback

import requests
from django.db import transaction
from django.db.transaction import on_commit
from django.utils.timezone import now

from poms.celery_tasks.models import CeleryTask
from poms.common import formula
from poms.common.crypto.RSACipher import RSACipher
from poms.credentials.models import Credentials
from poms.csv_import.tasks import data_csv_file_import_by_procedure_json
from poms.file_reports.models import FileReport
from poms.integrations.models import TransactionFileResult
from poms.integrations.tasks import complex_transaction_csv_file_import_by_procedure_json
from poms.procedures.models import RequestDataFileProcedureInstance, ExpressionProcedureInstance
from poms.procedures.tasks import procedure_request_data_file
from poms.system_messages.handlers import send_system_message
from poms.users.models import Member, MasterUser
from poms_app import settings

_l = logging.getLogger('poms.procedures')


class DataProcedureProcess(object):

    def __init__(self, procedure=None, master_user=None, date_from=None, date_to=None, member=None,
                 schedule_instance=None, context=None):

        _l.info('DataProcedureProcess. Master user: %s. Procedure: %s' % (master_user, procedure))

        self.master_user = master_user
        self.procedure = procedure

        self.member = member
        self.schedule_instance = schedule_instance
        self.context = context

        self.execute_procedure_date_expressions()

        if date_from:
            self.procedure.date_from = date_from
        if date_to:
            _l.info("Date To set from user Settings")
            self.procedure.date_to = date_to

    def execute_procedure_date_expressions(self):

        if self.procedure.date_from_expr:
            try:
                self.procedure.date_from = formula.safe_eval(self.procedure.date_from_expr, names={})
            except formula.InvalidExpression as e:
                _l.error("Cant execute date from expression %s " % e)

        if self.procedure.date_to_expr:
            try:
                self.procedure.date_to = formula.safe_eval(self.procedure.date_to_expr, names={})
            except formula.InvalidExpression as e:
                _l.error("Cant execute date to expression %s " % e)

    def process(self):

        if self.procedure.provider.user_code == 'universal':

            try:

                with transaction.atomic():

                    procedure_instance = RequestDataFileProcedureInstance.objects.create(procedure=self.procedure,
                                                                                         master_user=self.master_user,
                                                                                         status=RequestDataFileProcedureInstance.STATUS_PENDING,
                                                                                         schedule_instance=self.schedule_instance,
                                                                                         action='request_transaction_file',
                                                                                         provider='universal',
                                                                                         date_from=self.procedure.date_from,
                                                                                         date_to=self.procedure.date_to,
                                                                                         action_verbose='Request file with Transactions',
                                                                                         provider_verbose='Universal'

                                                                                         )

                    send_system_message(master_user=self.master_user,
                                        performed_by='System',
                                        description="universal Broker.  Procedure %s. Start" % procedure_instance.id,
                                        )

                    headers = {'Content-type': 'application/json', 'Accept': 'application/json'}

                    url = None
                    security_token = None
                    data = None

                    try:

                        url = self.procedure.data['url']
                        security_token = self.procedure.data['security_token']

                        data = {
                            'security_token': security_token,
                            "id": procedure_instance.id,
                            "user": {
                                "token": self.master_user.token,
                                "credentials": {}
                            },
                            "provider": self.procedure.provider.user_code,
                            "scheme_name": self.procedure.scheme_user_code,
                            "scheme_type": self.procedure.scheme_type,
                            "data": [],
                            "options": self.procedure.data,
                            "error_status": 0,
                            "error_message": "",
                        }

                        if self.context:
                            if 'names' in self.context:
                                if "echo" in data['options']:
                                    for key, value in data['options']["echo"].items():

                                        if value in self.context['names']:
                                            data['options']["echo"][key] = str(self.context['names'][value])

                        if self.procedure.date_from:
                            data["date_from"] = str(self.procedure.date_from)

                        if self.procedure.date_to:
                            data["date_to"] = str(self.procedure.date_to)

                        # if self.procedure.data['currencies']:
                        #     data["options"]['currencies'] = self.procedure.data['currencies']

                        _l.info('request universal url %s' % url)
                        _l.info('request universal data %s' % data)
                        _l.info('request universal self.context %s' % self.context)

                        procedure_instance.request_data = data
                        procedure_instance.save()
                    except Exception as e:
                        procedure_instance.error_message = 'Data Config Error %s' % e
                        procedure_instance.status = RequestDataFileProcedureInstance.STATUS_ERROR
                        procedure_instance.save()

                    response = None

                    try:
                        response = requests.post(url=url, json=data, headers=headers, verify=settings.VERIFY_SSL)
                    except Exception as e:

                        procedure_instance.error_message = 'Request To Remote Server Error %s.' % e
                        procedure_instance.status = RequestDataFileProcedureInstance.STATUS_ERROR
                        procedure_instance.save()

                        return

                    response_data = None

                    current_date_time = now().strftime("%Y-%m-%d-%H-%M")

                    file_report = FileReport()

                    file_name = "Universal Broker Response %s %s.json" % (procedure_instance.id, current_date_time)

                    file_content = ''

                    try:

                        response_data = response.json()

                        file_content = json.dumps(response_data, indent=4)
                        procedure_instance.response_data = file_content
                        procedure_instance.save()

                    except Exception as e:

                        procedure_instance.response_data = response.text

                        procedure_instance.error_message = 'Received JSON Error %s' % e
                        procedure_instance.status = RequestDataFileProcedureInstance.STATUS_ERROR
                        procedure_instance.save()

                        _l.info('response %s' % response.text)
                        _l.info("Response parse error %s" % e)
                        file_content = response.text

                    file_report.upload_file(file_name=file_name, text=file_content, master_user=self.master_user)
                    file_report.master_user = self.master_user
                    file_report.name = file_name
                    file_report.file_name = file_name
                    file_report.type = 'procedure.requestdatafileprocedure'
                    file_report.notes = 'System File'
                    file_report.content_type = 'application/json'

                    file_report.save()

                    send_system_message(master_user=procedure_instance.master_user,
                                        performed_by='System',
                                        description="universal Broker. Procedure %s. Response Received" % procedure_instance.id,
                                        attachments=[file_report.id])

                    procedure_id = response_data['id']

                    master_user = MasterUser.objects.get(token=response_data['user']['token'])

                    procedure_instance = RequestDataFileProcedureInstance.objects.get(id=procedure_id,
                                                                                      master_user=master_user)

                    procedure_instance.status = RequestDataFileProcedureInstance.STATUS_DONE
                    procedure_instance.save()

                    send_system_message(master_user=procedure_instance.master_user,
                                        performed_by="System",
                                        description="universal Broker. Procedure %s. Done, start import" % procedure_instance.id,
                                        )

                    celery_task = CeleryTask.objects.create(master_user=master_user,
                                                            member=self.member,
                                                            notes='Import initiated by data procedure instance %s' % procedure_instance.id,
                                                            verbose_name="Transaction Import by %s" % self.member.username,
                                                            type='transaction_import')

                    options_object = {}

                    options_object['items'] = response_data['data']

                    celery_task.options_object = options_object

                    celery_task.save()

                    def run_tasks():

                        if procedure_instance.procedure.scheme_type == 'transaction_import':
                            complex_transaction_csv_file_import_by_procedure_json.apply_async(
                                kwargs={'procedure_instance_id': procedure_instance.id,
                                        'celery_task_id': celery_task.id,
                                        })

                        if procedure_instance.procedure.scheme_type == 'simple_import':
                            data_csv_file_import_by_procedure_json.apply_async(
                                kwargs={'procedure_instance_id': procedure_instance.id,
                                        'celery_task_id': celery_task.id,
                                        })

                    on_commit(run_tasks)

            except Exception as e:
                _l.error("universal broker error %s" % e)
                _l.error("universal broker traceback %s" % traceback.format_exc())
                send_system_message(master_user=self.master_user,
                                    performed_by="System",
                                    action_status="required", type="error",
                                    title="Data Procedure Failed. User Code: %s " % self.procedure.user_code,
                                    description="Universal Broker. Procedure is not created.  Something went wrong %s" % e,
                                    )


        elif settings.DATA_FILE_SERVICE_URL:

            with transaction.atomic():

                procedure_instance = RequestDataFileProcedureInstance.objects.create(procedure=self.procedure,
                                                                                     master_user=self.master_user,
                                                                                     status=RequestDataFileProcedureInstance.STATUS_PENDING,
                                                                                     schedule_instance=self.schedule_instance,
                                                                                     action='request_transaction_file',
                                                                                     provider='finmars',

                                                                                     action_verbose='Request file with Transactions',
                                                                                     provider_verbose='Finmars'

                                                                                     )

                if self.member:
                    procedure_instance.started_by = RequestDataFileProcedureInstance.STARTED_BY_MEMBER
                    procedure_instance.member = self.member

                if self.schedule_instance:
                    member = Member.objects.get(master_user=self.master_user, is_owner=True)

                    procedure_instance.member = member  # Add owner of ecosystem as member who stared schedule (Need to transaction expr execution)
                    procedure_instance.started_by = RequestDataFileProcedureInstance.STARTED_BY_SCHEDULE
                    procedure_instance.schedule_instance = self.schedule_instance

                rsa_cipher = RSACipher()
                private_key, public_key = rsa_cipher.createKey()

                procedure_instance.private_key = private_key
                procedure_instance.public_key = public_key

                procedure_instance.save()

                _l.debug("RequestDataFileProcedureInstance procedure_instance created id: %s" % procedure_instance.id)

            _l.debug(
                "DataProcedureProcess: Request_transaction_file. Master User: %s. Provider: %s, Scheme name: %s" % (
                    self.master_user, self.procedure.provider, self.procedure.scheme_user_code))

            item = TransactionFileResult.objects.create(
                procedure_instance=procedure_instance,
                master_user=self.master_user,
                provider=self.procedure.provider,
                scheme_user_code=self.procedure.scheme_user_code,
            )

            item.save()

            params = {}

            if self.procedure.provider.user_code == 'cim_bank':

                if self.procedure.data:

                    if 'filenamemask' in self.procedure.data and self.procedure.data['filenamemask']:
                        params['filenamemask'] = self.procedure.data['filenamemask']

            if self.procedure.provider.user_code == 'email_provider':

                if self.procedure.data:

                    if 'sender' in self.procedure.data and self.procedure.data['sender']:
                        params['sender'] = self.procedure.data['sender']

                    if 'filename' in self.procedure.data and self.procedure.data['filename']:
                        params['filename'] = self.procedure.data['filename']

                    if 'subject' in self.procedure.data and self.procedure.data['subject']:
                        params['subject'] = self.procedure.data['subject']

                    if 'hasNoDelete' in self.procedure.data:

                        if self.procedure.data['hasNoDelete']:  # pain
                            params['hasNoDelete'] = 'true'
                        else:
                            params['hasNoDelete'] = 'false'
                else:
                    send_system_message(master_user=self.master_user,
                                        performed_by="System",
                                        description="Email Provider Procedure is not configured")

            # TODO DEPRECATED DELETE SOON
            if self.procedure.provider.user_code == 'julius_baer':

                try:

                    credentials = Credentials.objects.get(master_user=self.master_user,
                                                          provider=self.procedure.provider)

                    params['sftpuser'] = credentials.username
                    params['sftpkeypath'] = credentials.path_to_private_key

                except Exception as error:
                    send_system_message(master_user=self.master_user,
                                        performed_by="System",
                                        type='error',
                                        description="Can't configure Julius Baer Provider")
            # TODO DEPRECATED DELETE SOON
            if self.procedure.provider.user_code == 'lombard_odier':

                try:

                    credentials = Credentials.objects.get(master_user=self.master_user,
                                                          provider=self.procedure.provider)

                    params['sftpuser'] = credentials.username
                    params['sftppassword'] = credentials.password

                    if self.procedure.data:

                        if 'archivepassword' in self.procedure.data and self.procedure.data['archivepassword']:
                            params['archivepassword'] = self.procedure.data['archivepassword']

                    else:
                        send_system_message(master_user=self.master_user,
                                            performed_by='System',
                                            type='error',
                                            description="Lombard Odier Provider Procedure is not configured")

                except Exception as error:
                    send_system_message(master_user=self.master_user,
                                        performed_by='System',
                                        type='error',
                                        description="Can't configure Lombard Odier Provider")

            # TODO DEPRECATED DELETE SOON
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
                                        performed_by='System',
                                        type='error',
                                        description="Revolut rovider Procedure is not configured")

            callback_url = 'https://' + settings.DOMAIN_NAME + '/' + settings.BASE_API_URL + '/api/internal/data/transactions/callback/'

            data = {
                "id": procedure_instance.id,
                "user": {
                    "token": self.master_user.token,
                    # "base_api_url": settings.BASE_API_URL,
                    "credentials": {},
                    "params": params
                },
                "public_key": public_key,
                # "date_from": self.procedure.date_from,
                # "date_to": self.procedure.date_to,
                "provider": self.procedure.provider.user_code,
                "scheme_name": self.procedure.scheme_user_code,
                "scheme_type": self.procedure.scheme_type,

                "files": [],
                "error_status": 0,
                "error_message": "",

                "callbackURL": callback_url
            }

            _l.info('callback_url %s' % callback_url)

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
                                performed_by='System',
                                type='error',
                                description="Data Service is unknown")


class ExpressionProcedureProcess(object):

    def __init__(self, procedure=None, master_user=None, member=None, schedule_instance=None, context=None):

        _l.debug('ExpressionProcedureProcess. Master user: %s. Procedure: %s' % (master_user, procedure))

        self.master_user = master_user
        self.procedure = procedure

        self.member = member
        self.schedule_instance = schedule_instance
        self.context = context

        if not self.context:
            self.context = {}

        if not 'master_user' in self.context:
            self.context.update({'master_user': master_user})
        if not 'member' in self.context:
            self.context.update({'member': member})

        self.execute_context_variables_expressions()

    def execute_context_variables_expressions(self):

        self.context_names = {}

        _l.info(
            'ExpressionProcedureProcess.execute_context_variables_expressions %s ' % self.procedure.context_variables.all())

        for item in self.procedure.context_variables.all():

            try:
                self.context_names[item.name] = formula.safe_eval(item.expression, names=self.context_names,
                                                                  context=self.context)

            except Exception as e:
                _l.info('execute_context_variables_expressions.e %s' % e)
                self.context_names[item.name] = 'Invalid Expression'

        _l.info('self.context_names %s' % self.context_names)

    def process(self):

        try:

            self.procedure_instance = ExpressionProcedureInstance.objects.create(procedure=self.procedure,
                                                                                 master_user=self.master_user,
                                                                                 member=self.member,
                                                                                 status=ExpressionProcedureInstance.STATUS_PENDING,
                                                                                 schedule_instance=self.schedule_instance,
                                                                                 action='execute_expression_procedure',
                                                                                 provider='finmars',

                                                                                 action_verbose='Execute Expression Procedure',
                                                                                 provider_verbose='Finmars'

                                                                                 )

            send_system_message(master_user=self.master_user,
                                performed_by='System',
                                description="Procedure %s. Start" % self.procedure_instance.id,
                                )

            names = self.procedure.data

            if not names:
                names = {}

            for key, value in self.context_names.items():
                names[key] = value

            self.context['names'] = names

            _l.info('ExpressionProcedureProcess.names %s' % names)
            _l.info('ExpressionProcedureProcess.context %s' % self.context)

            self.procedure_instance.notes = ''

            if 'execution_context' in self.context:
                self.procedure_instance.notes = self.procedure_instance.notes = 'Executed by: %s %s' % (
                    self.context['execution_context']['source'], self.context['execution_context']['actor']) + '\n'

            self.procedure_instance.notes = self.procedure_instance.notes + 'Content: \n' + str(names) + '\n'
            self.procedure_instance.notes = self.procedure_instance.notes + '==========\n'
            self.procedure_instance.notes = self.procedure_instance.notes + 'Code: ' + str(self.procedure.code)

            try:

                result, log = formula.safe_eval_with_logs(self.procedure.code, names=names, context=self.context)

                _l.debug('ExpressionProcedureProcess.result %s' % result)

                if result:
                    self.procedure_instance.result = result

                if log:
                    self.procedure_instance.log = log

                self.procedure_instance.status = ExpressionProcedureInstance.STATUS_DONE

                self.procedure_instance.save()

            except Exception as e:

                send_system_message(master_user=self.master_user, action_status="required", type="warning",
                                    title='Expression Procedure Failed. User Code: %s' % self.procedure.user_code,
                                    description=str(e))

                self.procedure_instance.status = ExpressionProcedureInstance.STATUS_ERROR

                self.procedure_instance.error_message = str(e)
                self.procedure_instance.save()

                _l.error("ExpressionProcedureProcess.safe_eval error %s" % e)
                _l.error("ExpressionProcedureProcess.safe_eval traceback %s" % traceback.print_exc())

            send_system_message(master_user=self.master_user,
                                performed_by='System',
                                description="Procedure %s. Done" % self.procedure_instance.id,
                                )

        except Exception as e:
            _l.error("ExpressionProcedureProcess.process error %s" % e)
            _l.error(traceback.print_exc())

            send_system_message(master_user=self.master_user, action_status="required", type="error",
                                title='Expression Procedure Unknown Exception. User Code: %s' % self.procedure.user_code,
                                description=str(e))
