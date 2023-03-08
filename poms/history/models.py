import json
import logging
import traceback

from deepdiff import DeepDiff
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.translation import gettext_lazy

from poms.celery_tasks.models import CeleryTask
from poms.common.celery import get_active_celery_task, get_active_celery_task_id
from poms.common.middleware import get_request
from poms.users.models import MasterUser, Member
from poms_app import settings

_l = logging.getLogger('poms.history')

# TODO important to keep this list up to date
# Just not to log history for too meta models
excluded_to_track_history_models = ['system_messages.systemmessage', 'obj_attrs.genericattribute',
                                    'pricing.instrumentpricingpolicy', 'pricing.currencypricingpolicy',

                                    'transactions.complextransactioninput',

                                    'django_celery_results.taskresult',

                                    'finmars_standardized_errors.errorrecord']


class HistoricalRecord(models.Model):
    ACTION_CREATE = 'create'
    ACTION_CHANGE = 'change'
    ACTION_DELETE = 'delete'

    ACTION_CHOICES = (
        (ACTION_CREATE, gettext_lazy('Create')),
        (ACTION_CHANGE, gettext_lazy('Change')),
        (ACTION_DELETE, gettext_lazy('Delete')),
    )

    '''
    2023.01 Feature
    It listen changes of models and store JSON output after save
    In Finmars Web interface users can check history of changes for specific entity e.g. Instrument, Complex Transaction
    TODO: probably need to store only diff with change, not the whole JSON output
    '''
    master_user = models.ForeignKey(MasterUser, verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)
    member = models.ForeignKey(Member, null=True, blank=True, verbose_name=gettext_lazy('member'),
                               on_delete=models.SET_NULL)

    user_code = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('user code'))
    action = models.CharField(max_length=25, default=ACTION_CHANGE, choices=ACTION_CHOICES,
                              verbose_name='action')
    content_type = models.ForeignKey(ContentType, verbose_name=gettext_lazy('content type'), on_delete=models.CASCADE)

    context_url = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('context_url'))

    notes = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('notes'))

    created = models.DateTimeField(auto_now_add=True, editable=False, null=True, db_index=True,
                                   verbose_name=gettext_lazy('created'))

    json_data = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('json data'))

    @property
    def data(self):
        if self.json_data:
            try:
                return json.loads(self.json_data)
            except (ValueError, TypeError):
                return None
        else:
            return None

    @data.setter
    def data(self, val):
        if val:
            self.json_data = json.dumps(val, cls=DjangoJSONEncoder, sort_keys=True)
        else:
            self.json_data = None

    def __str__(self):
        return self.member.username + ' changed ' + self.user_code + ' (' + str(self.content_type) + ') at ' + str(
            self.created.strftime("%Y-%m-%d, %H:%M:%S"))

    class Meta:
        verbose_name = gettext_lazy('history record')
        verbose_name_plural = gettext_lazy('history records')
        index_together = [
            ['user_code', 'content_type']
        ]
        ordering = ['-created']


def get_user_code_from_instance(instance):
    user_code = None

    if getattr(instance, 'transaction_unique_code', None):
        user_code = instance.transaction_unique_code
    elif getattr(instance, 'code', None):
        user_code = instance.code
    elif getattr(instance, 'user_code', None):
        user_code = instance.user_code
    elif getattr(instance, 'name', None):
        user_code = instance.name

    if not user_code:
        user_code = str(instance)

    return user_code


def get_model_content_type_as_text(sender):
    content_type = ContentType.objects.get_for_model(sender)
    return content_type.app_label + '.' + content_type.model


def get_serialized_data(sender, instance):
    content_type_key = get_model_content_type_as_text(sender)

    record_context = get_record_context()

    context = {
        'master_user': record_context['master_user'],
        'member': record_context['member']
    }

    from poms.accounts.serializers import AccountSerializer
    from poms.accounts.serializers import AccountTypeSerializer

    from poms.instruments.serializers import InstrumentSerializer
    from poms.currencies.serializers import CurrencySerializer
    from poms.currencies.serializers import CurrencyHistorySerializer

    from poms.portfolios.serializers import PortfolioSerializer
    from poms.counterparties.serializers import CounterpartySerializer
    from poms.counterparties.serializers import ResponsibleSerializer

    from poms.instruments.serializers import InstrumentTypeSerializer
    from poms.instruments.serializers import PriceHistorySerializer
    from poms.instruments.serializers import PricingPolicySerializer
    from poms.instruments.serializers import GeneratedEventSerializer
    from poms.integrations.serializers import InstrumentDownloadSchemeSerializer
    from poms.integrations.serializers import ComplexTransactionImportSchemeSerializer
    from poms.portfolios.serializers import PortfolioRegisterSerializer
    from poms.transactions.serializers import ComplexTransactionSerializer
    from poms.transactions.serializers import TransactionTypeSerializer
    from poms.csv_import.serializers import CsvImportSchemeSerializer
    from poms.procedures.serializers import PricingProcedureSerializer
    from poms.procedures.serializers import RequestDataFileProcedureSerializer
    from poms.procedures.serializers import ExpressionProcedureSerializer
    from poms.schedules.serializers import ScheduleSerializer
    from poms.transactions.serializers import TransactionSerializer
    model_serializer_map = {
        'accounts.account': AccountSerializer,
        'accounts.accounttype': AccountTypeSerializer,

        'counterparties.counterparty': CounterpartySerializer,
        'counterparties.responsible': ResponsibleSerializer,
        'portfolios.portfolio': PortfolioSerializer,
        'portfolios.portfolioregister': PortfolioRegisterSerializer,

        'currencies.currency': CurrencySerializer,
        'currencies.currencyhistory': CurrencyHistorySerializer,

        'instruments.instrument': InstrumentSerializer,
        'instruments.instrumenttype': InstrumentTypeSerializer,
        'instruments.pricehistory': PriceHistorySerializer,
        'instruments.pricingpolicy': PricingPolicySerializer,
        'instruments.generatedevent': GeneratedEventSerializer,

        'integrations.instrumentdownloadscheme': InstrumentDownloadSchemeSerializer,
        'integrations.complextransactionimportscheme': ComplexTransactionImportSchemeSerializer,

        'csv_import.csvimportscheme': CsvImportSchemeSerializer,

        'transactions.complextransaction': ComplexTransactionSerializer,
        'transactions.transaction': TransactionSerializer,
        'transactions.transactiontype': TransactionTypeSerializer,

        'procedures.pricingprocedure': PricingProcedureSerializer,
        'procedures.requestdatafileprocedure': RequestDataFileProcedureSerializer,
        'procedures.expressionprocedure': ExpressionProcedureSerializer,

        'schedules.schedule': ScheduleSerializer

    }

    result = None

    try:
        result = model_serializer_map[content_type_key](instance=instance, context=context).data
    except Exception as e:
        try:
            result = json.dumps(instance, default=str)
        except Exception as e:
            pass

    return result


def get_notes_for_history_record(user_code, content_type, serialized_data):
    notes = None

    try:

        last_record = \
            HistoricalRecord.objects.filter(user_code=user_code, content_type=content_type).order_by('-created')[0]

        everything_is_dict = json.loads(
            json.dumps(serialized_data))  # because deep diff counts different Dict and Ordered dict

        result = DeepDiff(everything_is_dict, last_record.data,
                          ignore_string_type_changes=True,
                          ignore_order=True,
                          ignore_type_subclasses=True)

        # _l.info('result %s' % result)

        notes = result.to_json()

    except Exception as e:
        _l.error('get_notes_for_history_record e %s' % e)
        _l.error('get_notes_for_history_record traceback %s' % traceback.format_exc())
        pass

    return notes


def get_record_context():
    result = {
        'master_user': None,
        'member': None,
        'context_url': "Unknown"
    }

    request = get_request()


    # if we have request (normal way)

    if request:
        context_url = request.path

        result['master_user'] = request.user.master_user
        result['member'] = request.user.member
        result['context_url'] = context_url

    else:  # in case if we have celery context

        try:

            celery_task_id = get_active_celery_task_id()
            lib_celery_task = get_active_celery_task()

            _l.info('celery_task_id %s' % celery_task_id)

            try:

                celery_task = CeleryTask.objects.get(celery_task_id=celery_task_id)

                result['member'] = celery_task.member
                result['master_user'] = celery_task.master_user
                result['context_url'] = celery_task.type + ' [' + str(celery_task.id) + ']'

            except Exception as e:

                _l.error('get_record_context.celery celery_task_id lookup error e %s' % e)

                finmars_bot = Member.objects.get(username='finmars_bot')
                master_user = MasterUser.objects.get(base_api_url=settings.BASE_API_URL)

                result['master_user'] = master_user
                result['member'] = finmars_bot

                _l.info('lib_celery_task.name %s' % lib_celery_task.name)

                result['context_url'] = lib_celery_task.name
        except Exception as e:
            _l.error("Error getting context for celery exception %s" % e)
            _l.error("Error getting context for celery traceback %s" % traceback.format_exc())


    return result


def post_save(sender, instance, created, using=None, update_fields=None, **kwargs):
    # _l.info('post_save.sender %s' % sender)
    # _l.info('post_save.update_fields %s' % update_fields)

    try:

        record_context = get_record_context()

        content_type = ContentType.objects.get_for_model(sender)
        content_type_key = get_model_content_type_as_text(sender)

        '''General logic for most of the entities'''
        action = HistoricalRecord.ACTION_CREATE

        if not created:
            action = HistoricalRecord.ACTION_CHANGE

        '''
        Special logic for transactions 
        '''
        if content_type_key == 'complextransaction':
            try:

                if getattr(instance, 'transaction_unique_code', None):
                    exist = sender.objects.get(transaction_unique_code=instance.transaction_unique_code)

                elif getattr(instance, 'code', None):
                    exist = sender.objects.get(code=instance.code)

                action = HistoricalRecord.ACTION_CHANGE
            except Exception as e:
                action = HistoricalRecord.ACTION_CREATE
        elif getattr(instance, 'user_code', None):
            '''
            Special logic for user_coded entities 
            '''

            try:
                exist = sender.objects.get(user_code=instance.user_code)
                action = HistoricalRecord.ACTION_CHANGE
            except Exception as e:
                action = HistoricalRecord.ACTION_CREATE

        user_code = get_user_code_from_instance(instance)

        data = get_serialized_data(sender, instance)

        notes = get_notes_for_history_record(user_code, content_type, data)

        HistoricalRecord.objects.create(
            master_user=record_context['master_user'],
            member=record_context['member'],
            action=action,
            context_url=record_context['context_url'],
            data=data,
            notes=notes,
            user_code=user_code,
            content_type=content_type
        )

    except Exception as e:
        _l.error("Could not save history exception %s" % e)
        _l.error("Could not save history traceback %s" % traceback.format_exc())


def post_delete(sender, instance, using=None, **kwargs):
    try:

        record_context = get_record_context()

        action = HistoricalRecord.ACTION_DELETE

        content_type = ContentType.objects.get_for_model(sender)

        user_code = get_user_code_from_instance(instance)

        data = get_serialized_data(sender, instance)

        HistoricalRecord.objects.create(
            master_user=record_context['master_user'],
            member=record_context['member'],
            context_url=record_context['context_url'],
            action=action,
            data=data,
            user_code=user_code,
            content_type=content_type
        )

    except Exception as e:
        _l.error("Could not save history record exception %s" % e)
        _l.error("Could not save history record tracback %s " % traceback.format_exc())


def add_history_listeners(sender, **kwargs):
    # _l.debug("History listener registered Entity %s" % sender)

    content_type_key = get_model_content_type_as_text(sender)

    if content_type_key not in excluded_to_track_history_models:
        models.signals.post_save.connect(post_save, sender=sender, weak=False)
        models.signals.post_delete.connect(post_delete, sender=sender, weak=False)


models.signals.class_prepared.connect(add_history_listeners, weak=False)
