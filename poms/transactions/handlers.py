import json
import logging
from datetime import date, datetime

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers.json import DjangoJSONEncoder
from django.db import DatabaseError, IntegrityError
from django.utils.translation import ugettext

from poms.accounts.models import Account
from poms.common import formula
from poms.common.utils import date_now, format_float, format_float_to_2
from poms.counterparties.models import Counterparty, Responsible
from poms.currencies.models import Currency
from poms.instruments.models import Instrument, DailyPricingModel, PaymentSizeDetail, PricingPolicy, Periodicity, \
    AccrualCalculationModel, InstrumentFactorSchedule, ManualPricingFormula, AccrualCalculationSchedule, EventSchedule, \
    EventScheduleAction
from poms.instruments.models import InstrumentType
from poms.integrations.models import PriceDownloadScheme
from poms.obj_perms.models import GenericObjectPermission
from poms.obj_perms.utils import assign_perms3, get_view_perms
from poms.portfolios.models import Portfolio
from poms.strategies.models import Strategy1, Strategy2, Strategy3
from poms.transactions.models import ComplexTransaction, TransactionTypeInput, Transaction, EventClass, \
    NotificationClass, RebookReactionChoice, ComplexTransactionInput, TransactionType
from poms.users.models import EcosystemDefault, Group
from django.apps import apps

_l = logging.getLogger('poms.transactions')


# CONTEXT_PROPERTIES = {
#     1: 'instrument',
#     2: 'pricing_currency',
#     3: 'accrued_currency',
#     4: 'portfolio',
#     5: 'account',
#     6: 'strategy1',
#     7: 'strategy2',
#     8: 'strategy3',
#     9:  'position',
#     10: 'effective_date',
# }


class TransactionTypeProcess(object):
    # if store is false then operations must be rollback outside, for example in view...
    MODE_BOOK = 'book'
    MODE_REBOOK = 'rebook'
    MODE_RECALCULATE = 'recalculate'

    def __init__(self,
                 process_mode=None,
                 transaction_type=None,
                 default_values=None,
                 values=None,
                 recalculate_inputs=None,
                 has_errors=False,
                 value_errors=None,
                 instruments=None,
                 instruments_errors=None,
                 complex_transaction=None,
                 complex_transaction_status=None,
                 complex_transaction_errors=None,
                 transactions=None,
                 transactions_errors=None,
                 fake_id_gen=None,
                 transaction_order_gen=None,
                 now=None,
                 context=None,  # for formula engine
                 context_values=None):  # context_values = CONTEXT VARIABLES

        self.transaction_type = transaction_type

        master_user = self.transaction_type.master_user

        self.process_mode = process_mode

        if self.process_mode is None:
            self.process_mode = TransactionTypeProcess.MODE_BOOK

        print('self.process_mode %s' % self.process_mode)

        self.default_values = default_values or {}
        self.context_values = context_values or {}

        print('TransactionTypeProcess.context_values %s' % context_values)

        # self.expressions = expressions or {}
        # self.expressions_error = None
        # self.expressions_result = None

        self.inputs = list(self.transaction_type.inputs.all())

        self.complex_transaction = complex_transaction
        if self.complex_transaction is None:
            self.complex_transaction = ComplexTransaction(transaction_type=self.transaction_type, date=None,
                                                          master_user=master_user)

        self.complex_transaction.visibility_status = self.transaction_type.visibility_status

        if complex_transaction_status is not None:
            self.complex_transaction.status = complex_transaction_status
        # if complex_transaction_date is not None:
        #     self.complex_transaction.date = complex_transaction_date

        self._now = now or date_now()
        self._context = context
        self._context['transaction_type'] = self.transaction_type

        self.recalculate_inputs = recalculate_inputs or []

        self.value_errors = value_errors or []
        self.transactions = transactions or []
        self.instruments = instruments or []
        self.instruments_errors = instruments_errors or []
        self.complex_transaction_errors = complex_transaction_errors or []
        self.transactions_errors = transactions_errors or []

        self._id_seq = 0
        self._transaction_order_seq = 0

        self.next_fake_id = fake_id_gen or self._next_fake_id_default
        self.next_transaction_order = transaction_order_gen or self._next_transaction_order_default

        if values is None:
            self._set_values()
        else:
            self.values = values

    @property
    def is_book(self):
        return self.process_mode == self.MODE_BOOK

    @property
    def is_rebook(self):
        return self.process_mode == self.MODE_REBOOK

    @property
    def is_recalculate(self):
        return self.process_mode == self.MODE_RECALCULATE

    def _next_fake_id_default(self):
        self._id_seq -= 1
        return self._id_seq

    def _next_transaction_order_default(self):
        self._transaction_order_seq += 1
        return self._transaction_order_seq

    def execute_action_condition(self, action):

        print('action.condition_expr')
        print(action.condition_expr)

        if action is None:
            return False

        if action.condition_expr is None or action.condition_expr == '':
            return True

        try:
            result = formula.safe_eval(action.condition_expr, names=self.values,
                                       context=self._context)

            print('Action is executed')
            print(result)

            if result == "False" or result == False:
                return False

            return True

        except formula.InvalidExpression as e:

            print('Action is skipped')

            return False

    def _set_values(self):
        def _get_val_by_model_cls(obj, model_class):
            if issubclass(model_class, Account):
                return obj.account
            elif issubclass(model_class, Currency):
                return obj.currency
            elif issubclass(model_class, Instrument):
                return obj.instrument
            elif issubclass(model_class, InstrumentType):
                return obj.instrument_type
            elif issubclass(model_class, Counterparty):
                return obj.counterparty
            elif issubclass(model_class, Responsible):
                return obj.responsible
            elif issubclass(model_class, Strategy1):
                return obj.strategy1
            elif issubclass(model_class, Strategy2):
                return obj.strategy2
            elif issubclass(model_class, Strategy3):
                return obj.strategy3
            elif issubclass(model_class, DailyPricingModel):
                return obj.daily_pricing_model
            elif issubclass(model_class, PaymentSizeDetail):
                return obj.payment_size_detail
            elif issubclass(model_class, Portfolio):
                return obj.portfolio
            elif issubclass(model_class, PriceDownloadScheme):
                return obj.price_download_scheme
            elif issubclass(model_class, PricingPolicy):
                return obj.pricing_policy
            elif issubclass(model_class, Periodicity):
                return obj.periodicity
            elif issubclass(model_class, AccrualCalculationModel):
                return obj.accrual_calculation_model
            elif issubclass(model_class, EventClass):
                return obj.event_class
            elif issubclass(model_class, NotificationClass):
                return obj.notification_class
            return None

        self.values = {}
        self.values.update(self.default_values)

        if self.complex_transaction and self.complex_transaction.id is not None and self.complex_transaction.id > 0:
            # load previous values if need
            ci_qs = self.complex_transaction.inputs.all().select_related(
                'transaction_type_input', 'transaction_type_input__content_type'
            )
            for ci in ci_qs:
                i = ci.transaction_type_input
                value = None
                if i.value_type == TransactionTypeInput.STRING or i.value_type == TransactionTypeInput.SELECTOR:
                    value = ci.value_string
                elif i.value_type == TransactionTypeInput.NUMBER:
                    value = ci.value_float
                elif i.value_type == TransactionTypeInput.DATE:
                    value = ci.value_date
                elif i.value_type == TransactionTypeInput.RELATION:
                    value = _get_val_by_model_cls(ci, i.content_type.model_class())
                if value is not None:
                    self.values[i.name] = value

        for i in self.inputs:

            if i.name in self.values:
                continue
            value = None

            if i.is_fill_from_context:

                try:
                    value = self.context_values[i.context_property]
                except KeyError:
                    print("Can't find context variable %s" % i.context_property)

                if value:
                    self.default_values[i.name] = value

            if i.value_type == TransactionTypeInput.RELATION:

                model_class = i.content_type.model_class()

                if i.is_fill_from_context:

                    for k, v in self.default_values.items():
                        if isinstance(v, model_class):
                            value = v
                            break
                else:

                    if value is None:
                        value = _get_val_by_model_cls(i, model_class)

            else:

                if i.name in self.default_values:
                    value = self.default_values[i.name]
                if value is None:

                    if i.value:
                        errors = {}
                        try:
                            value = formula.safe_eval(i.value, names=self.values, now=self._now, context=self._context)
                        except formula.InvalidExpression as e:
                            self._set_eval_error(errors, i.name, i.value, e)
                            self.value_errors.append(errors)
                            value = None

            self.values[i.name] = value

        # print('setvalues %s' % self.values)

    def book_create_instruments(self, actions, master_user, instrument_map):

        object_permissions = self.transaction_type.object_permissions.select_related('permission').all()
        daily_pricing_model = DailyPricingModel.objects.get(pk=DailyPricingModel.SKIP)

        for order, action in enumerate(actions):
            try:
                action_instrument = action.transactiontypeactioninstrument
            except ObjectDoesNotExist:
                action_instrument = None

            if action_instrument and self.execute_action_condition(action_instrument):

                print('action_instrument %s' % action_instrument)
                print('self.process_mode == self.MODE_REBOOK')
                print('self.process_mode %s ' % self.process_mode)
                print(self.process_mode == self.MODE_REBOOK)
                print('action_instrument.rebook_reaction %s' % action_instrument.rebook_reaction)

                _l.debug('process instrument: %s', action_instrument)
                errors = {}
                try:
                    user_code = formula.safe_eval(action_instrument.user_code, names=self.values, now=self._now,
                                                  context=self._context)
                except formula.InvalidExpression as e:
                    self._set_eval_error(errors, 'user_code', action_instrument.user_code, e)
                    user_code = None

                instrument = None
                instrument_exists = False

                ecosystem_default = EcosystemDefault.objects.get(master_user=master_user)

                if user_code:
                    try:

                        instrument = Instrument.objects.get(master_user=master_user, user_code=user_code,
                                                            is_deleted=False)
                        instrument_exists = True

                        print('Instrument found by user code')

                    except Instrument.DoesNotExist:

                        print("Instrument DoesNotExist exception")
                        print("action_instrument.rebook_reaction %s " % action_instrument.rebook_reaction)
                        print("RebookReactionChoice.FIND_OR_CREATE %s" % RebookReactionChoice.FIND_OR_CREATE)
                        print("self.process_mode %s" % self.process_mode)
                        print("self.MODE_REBOOK %s" % self.MODE_REBOOK)

                        if action_instrument.rebook_reaction == RebookReactionChoice.FIND_OR_CREATE and \
                                self.process_mode == self.MODE_REBOOK:
                            instrument = ecosystem_default.instrument
                            instrument_exists = True

                            print('Rebook: Instrument is not exists, return Default %s' % instrument.user_code)

                if instrument is None:
                    instrument = Instrument(master_user=master_user, user_code=user_code)
                    print("Instrument is not exists. Create new.")

                # instrument.user_code = user_code

                print('instrument.user_code %s ' % instrument.user_code)

                if instrument.user_code != '-' and instrument.user_code != ecosystem_default.instrument.user_code:

                    self._set_val(errors=errors, values=self.values, default_value='',
                                  target=instrument, target_attr_name='name',
                                  source=action_instrument, source_attr_name='name')
                    self._set_val(errors=errors, values=self.values, default_value='',
                                  target=instrument, target_attr_name='short_name',
                                  source=action_instrument, source_attr_name='short_name')
                    self._set_val(errors=errors, values=self.values, default_value='',
                                  target=instrument, target_attr_name='public_name',
                                  source=action_instrument, source_attr_name='public_name')

                    if getattr(action_instrument, 'notes'):
                        self._set_val(errors=errors, values=self.values, default_value='',
                                      target=instrument, target_attr_name='notes',
                                      source=action_instrument, source_attr_name='notes')

                    self._set_rel(errors=errors,
                                  target=instrument, target_attr_name='instrument_type',
                                  source=action_instrument, source_attr_name='instrument_type',
                                  values=self.values, default_value=master_user.instrument_type)
                    self._set_rel(errors=errors, values=self.values, default_value=master_user.currency,
                                  target=instrument, target_attr_name='pricing_currency',
                                  source=action_instrument, source_attr_name='pricing_currency')
                    self._set_val(errors=errors, values=self.values, default_value=0.0,
                                  target=instrument, target_attr_name='price_multiplier',
                                  source=action_instrument, source_attr_name='price_multiplier')
                    self._set_rel(errors=errors, values=self.values, default_value=master_user.currency,
                                  target=instrument, target_attr_name='accrued_currency',
                                  source=action_instrument, source_attr_name='accrued_currency')
                    self._set_val(errors=errors, values=self.values, default_value=0.0,
                                  target=instrument, target_attr_name='accrued_multiplier',
                                  source=action_instrument, source_attr_name='accrued_multiplier')
                    self._set_rel(errors=errors, values=self.values, default_value=None,
                                  target=instrument, target_attr_name='payment_size_detail',
                                  source=action_instrument, source_attr_name='payment_size_detail')
                    self._set_val(errors=errors, values=self.values, default_value=0.0,
                                  target=instrument, target_attr_name='default_price',
                                  source=action_instrument, source_attr_name='default_price')
                    self._set_val(errors=errors, values=self.values, default_value=0.0,
                                  target=instrument, target_attr_name='default_accrued',
                                  source=action_instrument, source_attr_name='default_accrued')
                    self._set_val(errors=errors, values=self.values, default_value='',
                                  target=instrument, target_attr_name='user_text_1',
                                  source=action_instrument, source_attr_name='user_text_1')
                    self._set_val(errors=errors, values=self.values, default_value='',
                                  target=instrument, target_attr_name='user_text_2',
                                  source=action_instrument, source_attr_name='user_text_2')
                    self._set_val(errors=errors, values=self.values, default_value='',
                                  target=instrument, target_attr_name='user_text_3',
                                  source=action_instrument, source_attr_name='user_text_3')
                    self._set_val(errors=errors, values=self.values, default_value='',
                                  target=instrument, target_attr_name='reference_for_pricing',
                                  source=action_instrument, source_attr_name='reference_for_pricing')
                    self._set_rel(errors=errors, values=self.values, default_value=None,
                                  target=instrument, target_attr_name='price_download_scheme',
                                  source=action_instrument, source_attr_name='price_download_scheme')
                    self._set_rel(errors=errors, values=self.values, default_value=daily_pricing_model,
                                  target=instrument, target_attr_name='daily_pricing_model',
                                  source=action_instrument, source_attr_name='daily_pricing_model')
                    self._set_val(errors=errors, values=self.values, default_value=date.max,
                                  target=instrument, target_attr_name='maturity_date',
                                  source=action_instrument, source_attr_name='maturity_date',
                                  validator=formula.validate_date)
                    self._set_val(errors=errors, values=self.values, default_value=0.0,
                                  target=instrument, target_attr_name='maturity_price',
                                  source=action_instrument, source_attr_name='maturity_price')

                try:

                    rebook_reaction = action_instrument.rebook_reaction

                    print('rebook_reaction %s' % rebook_reaction)
                    print('instrument_exists %s' % instrument_exists)

                    if self.process_mode == self.MODE_REBOOK:

                        if rebook_reaction == RebookReactionChoice.OVERWRITE:
                            print('Rebook  OVERWRITE')

                            instrument.save()

                        if rebook_reaction == RebookReactionChoice.CREATE and not instrument_exists:
                            print('Rebook CREATE')

                            instrument.save()

                        if rebook_reaction == RebookReactionChoice.FIND_OR_CREATE and not instrument_exists:
                            print('Rebook FIND_OR_CREATE')

                            instrument.save()

                    else:

                        if rebook_reaction == RebookReactionChoice.OVERWRITE:
                            print('Book  OVERWRITE')

                            instrument.save()

                        if rebook_reaction == RebookReactionChoice.CREATE and not instrument_exists:
                            print('Book  CREATE')

                            instrument.save()

                        if rebook_reaction == RebookReactionChoice.FIND_OR_CREATE and not instrument_exists:
                            print('Book  FIND_OR_CREATE')

                            instrument.save()

                    if rebook_reaction is None:
                        instrument.save()

                    self._instrument_assign_permission(instrument, object_permissions)

                except (ValueError, TypeError, IntegrityError):

                    self._add_err_msg(errors, 'non_field_errors',
                                      ugettext('Invalid instrument action fields (please, use type convertion).'))
                except DatabaseError:
                    self._add_err_msg(errors, 'non_field_errors', ugettext('General DB error.'))
                else:
                    instrument_map[action.id] = instrument
                finally:

                    _l.debug("Instrument action errors %s " % errors)

                    if bool(errors):
                        self.instruments_errors.append(errors)

        return instrument_map

    def book_create_factor_schedules(self, actions, instrument_map):

        for order, action in enumerate(actions):
            try:
                action_instrument_factor_schedule = action.transactiontypeactioninstrumentfactorschedule
            except ObjectDoesNotExist:
                action_instrument_factor_schedule = None

            if action_instrument_factor_schedule and self.execute_action_condition(action_instrument_factor_schedule):

                _l.debug('process factor schedule: %s', action_instrument_factor_schedule)

                errors = {}

                factor = InstrumentFactorSchedule()

                self._set_rel(errors=errors, values=self.values, default_value=None,
                              target=factor, target_attr_name='instrument',
                              source=action_instrument_factor_schedule, source_attr_name='instrument')
                if action_instrument_factor_schedule.instrument_phantom is not None:
                    factor.instrument = instrument_map[
                        action_instrument_factor_schedule.instrument_phantom_id]

                self._set_val(errors=errors, values=self.values, default_value=self._now,
                              target=factor, target_attr_name='effective_date', validator=formula.validate_date,
                              source=action_instrument_factor_schedule, source_attr_name='effective_date')

                self._set_val(errors=errors, values=self.values, default_value=0.0,
                              target=factor, target_attr_name='factor_value',
                              source=action_instrument_factor_schedule, source_attr_name='factor_value')

                try:

                    rebook_reaction = action_instrument_factor_schedule.rebook_reaction

                    if self.process_mode == self.MODE_REBOOK:

                        if rebook_reaction == RebookReactionChoice.CREATE:
                            factor.save()

                        if rebook_reaction == RebookReactionChoice.CREATE_IF_NOT_EXIST:
                            print('Skip')

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE:
                            InstrumentFactorSchedule.objects.filter(instrument=factor.instrument).delete()

                            factor.save()

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE_OR_SKIP:
                            print('Skip')

                        if rebook_reaction == RebookReactionChoice.CLEAR:
                            InstrumentFactorSchedule.objects.filter(instrument=factor.instrument).delete()

                    else:

                        if rebook_reaction == RebookReactionChoice.CREATE:
                            factor.save()

                        if rebook_reaction == RebookReactionChoice.CREATE_IF_NOT_EXIST:
                            factor.save()

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE:
                            InstrumentFactorSchedule.objects.filter(instrument=factor.instrument).delete()

                            factor.save()

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE_OR_SKIP:
                            InstrumentFactorSchedule.objects.filter(instrument=factor.instrument).delete()

                            factor.save()

                        if rebook_reaction == RebookReactionChoice.CLEAR:
                            InstrumentFactorSchedule.objects.filter(instrument=factor.instrument).delete()

                        if rebook_reaction is None:
                            factor.save()


                except (ValueError, TypeError, IntegrityError):

                    self._add_err_msg(errors, 'non_field_errors',
                                      ugettext(
                                          'Invalid instrument factor schedule action fields (please, use type convertion).'))
                except DatabaseError:
                    self._add_err_msg(errors, 'non_field_errors', ugettext('General DB error.'))
                finally:
                    if bool(errors):
                        _l.debug(errors)
                        # self.instruments_errors.append(errors)

    def book_create_manual_pricing_formulas(self, actions, instrument_map):

        for order, action in enumerate(actions):
            try:
                action_instrument_manual_pricing_formula = action.transactiontypeactioninstrumentmanualpricingformula
            except ObjectDoesNotExist:
                action_instrument_manual_pricing_formula = None

            if action_instrument_manual_pricing_formula and self.execute_action_condition(
                    action_instrument_manual_pricing_formula):

                _l.debug('process manual pricing formula: %s', action_instrument_manual_pricing_formula)

                errors = {}

                manual_pricing_formula = ManualPricingFormula()

                self._set_rel(errors=errors, values=self.values, default_value=None,
                              target=manual_pricing_formula, target_attr_name='instrument',
                              source=action_instrument_manual_pricing_formula, source_attr_name='instrument')
                if action_instrument_manual_pricing_formula.instrument_phantom is not None:
                    manual_pricing_formula.instrument = instrument_map[
                        action_instrument_manual_pricing_formula.instrument_phantom_id]

                self._set_rel(errors=errors, values=self.values, default_value=None,
                              target=manual_pricing_formula, target_attr_name='pricing_policy',
                              source=action_instrument_manual_pricing_formula, source_attr_name='pricing_policy')

                self._set_val(errors=errors, values=self.values, default_value='',
                              target=manual_pricing_formula, target_attr_name='expr',
                              source=action_instrument_manual_pricing_formula, source_attr_name='expr')

                if getattr(action_instrument_manual_pricing_formula, 'notes'):
                    self._set_val(errors=errors, values=self.values, default_value='',
                                  target=manual_pricing_formula, target_attr_name='notes',
                                  source=action_instrument_manual_pricing_formula, source_attr_name='notes')

                try:

                    rebook_reaction = action_instrument_manual_pricing_formula.rebook_reaction

                    if self.process_mode == self.MODE_REBOOK:

                        if rebook_reaction == RebookReactionChoice.CREATE:
                            manual_pricing_formula.save()

                        if rebook_reaction == RebookReactionChoice.CREATE_IF_NOT_EXIST:
                            print('Skip')

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE:
                            ManualPricingFormula.objects.filter(instrument=manual_pricing_formula.instrument).delete()

                            manual_pricing_formula.save()

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE_OR_SKIP:
                            print('Skip')

                        if rebook_reaction == RebookReactionChoice.CLEAR:
                            ManualPricingFormula.objects.filter(instrument=manual_pricing_formula.instrument).delete()

                    else:

                        if rebook_reaction == RebookReactionChoice.CREATE:
                            manual_pricing_formula.save()

                        if rebook_reaction == RebookReactionChoice.CREATE_IF_NOT_EXIST:
                            manual_pricing_formula.save()

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE:
                            ManualPricingFormula.objects.filter(instrument=manual_pricing_formula.instrument).delete()

                            manual_pricing_formula.save()

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE_OR_SKIP:
                            ManualPricingFormula.objects.filter(instrument=manual_pricing_formula.instrument).delete()

                            manual_pricing_formula.save()

                        if rebook_reaction == RebookReactionChoice.CLEAR:
                            ManualPricingFormula.objects.filter(instrument=manual_pricing_formula.instrument).delete()

                    if rebook_reaction is None:
                        manual_pricing_formula.save()

                except (ValueError, TypeError, IntegrityError):

                    self._add_err_msg(errors, 'non_field_errors',
                                      ugettext(
                                          'Invalid instrument manual pricing formula action fields (please, use type convertion).'))
                except DatabaseError:
                    self._add_err_msg(errors, 'non_field_errors', ugettext('General DB error.'))
                finally:
                    if bool(errors):
                        _l.debug(errors)
                        # self.instruments_errors.append(errors)

    def book_create_accrual_calculation_schedules(self, actions, instrument_map):

        for order, action in enumerate(actions):
            try:
                action_instrument_accrual_calculation_schedule = action.transactiontypeactioninstrumentaccrualcalculationschedules
            except ObjectDoesNotExist:
                action_instrument_accrual_calculation_schedule = None

            if action_instrument_accrual_calculation_schedule and self.execute_action_condition(
                    action_instrument_accrual_calculation_schedule):

                _l.debug('process accrual calculation schedule: %s', action_instrument_accrual_calculation_schedule)

                errors = {}

                accrual_calculation_schedule = AccrualCalculationSchedule()

                self._set_rel(errors=errors, values=self.values, default_value=None,
                              target=accrual_calculation_schedule, target_attr_name='instrument',
                              source=action_instrument_accrual_calculation_schedule, source_attr_name='instrument')
                if action_instrument_accrual_calculation_schedule.instrument_phantom is not None:
                    accrual_calculation_schedule.instrument = instrument_map[
                        action_instrument_accrual_calculation_schedule.instrument_phantom_id]

                self._set_rel(errors=errors, values=self.values, default_value=None,
                              target=accrual_calculation_schedule, target_attr_name='accrual_calculation_model',
                              source=action_instrument_accrual_calculation_schedule,
                              source_attr_name='accrual_calculation_model')

                self._set_rel(errors=errors, values=self.values, default_value=None,
                              target=accrual_calculation_schedule, target_attr_name='periodicity',
                              source=action_instrument_accrual_calculation_schedule, source_attr_name='periodicity')

                self._set_val(errors=errors, values=self.values, default_value='', validator=formula.validate_date,
                              target=accrual_calculation_schedule, target_attr_name='accrual_start_date',
                              source=action_instrument_accrual_calculation_schedule,
                              source_attr_name='accrual_start_date')

                self._set_val(errors=errors, values=self.values, default_value='', validator=formula.validate_date,
                              target=accrual_calculation_schedule, target_attr_name='first_payment_date',
                              source=action_instrument_accrual_calculation_schedule,
                              source_attr_name='first_payment_date')

                self._set_val(errors=errors, values=self.values, default_value='',
                              target=accrual_calculation_schedule, target_attr_name='accrual_size',
                              source=action_instrument_accrual_calculation_schedule,
                              source_attr_name='accrual_size')

                self._set_val(errors=errors, values=self.values, default_value='',
                              target=accrual_calculation_schedule, target_attr_name='periodicity_n',
                              source=action_instrument_accrual_calculation_schedule,
                              source_attr_name='periodicity_n')

                if getattr(action_instrument_accrual_calculation_schedule, 'notes'):
                    self._set_val(errors=errors, values=self.values, default_value='',
                                  target=accrual_calculation_schedule, target_attr_name='notes',
                                  source=action_instrument_accrual_calculation_schedule, source_attr_name='notes')

                try:

                    rebook_reaction = action_instrument_accrual_calculation_schedule.rebook_reaction

                    if self.process_mode == self.MODE_REBOOK:

                        if rebook_reaction == RebookReactionChoice.CREATE:
                            accrual_calculation_schedule.save()

                        if rebook_reaction == RebookReactionChoice.CREATE_IF_NOT_EXIST:
                            print('Skip')

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE:
                            AccrualCalculationSchedule.objects.filter(
                                instrument=accrual_calculation_schedule.instrument).delete()

                            accrual_calculation_schedule.save()

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE_OR_SKIP:
                            print('Skip')

                        if rebook_reaction == RebookReactionChoice.CLEAR:
                            AccrualCalculationSchedule.objects.filter(
                                instrument=accrual_calculation_schedule.instrument).delete()

                    else:

                        if rebook_reaction == RebookReactionChoice.CREATE:
                            accrual_calculation_schedule.save()

                        if rebook_reaction == RebookReactionChoice.CREATE_IF_NOT_EXIST:
                            accrual_calculation_schedule.save()

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE:
                            AccrualCalculationSchedule.objects.filter(
                                instrument=accrual_calculation_schedule.instrument).delete()

                            accrual_calculation_schedule.save()

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE_OR_SKIP:
                            AccrualCalculationSchedule.objects.filter(
                                instrument=accrual_calculation_schedule.instrument).delete()

                            accrual_calculation_schedule.save()

                        if rebook_reaction == RebookReactionChoice.CLEAR:
                            AccrualCalculationSchedule.objects.filter(
                                instrument=accrual_calculation_schedule.instrument).delete()

                        if rebook_reaction is None:
                            accrual_calculation_schedule.save()

                except (ValueError, TypeError, IntegrityError):

                    self._add_err_msg(errors, 'non_field_errors',
                                      ugettext(
                                          'Invalid instrument accrual calculation schedule action fields (please, use type convertion).'))
                except DatabaseError:
                    self._add_err_msg(errors, 'non_field_errors', ugettext('General DB error.'))
                finally:
                    if bool(errors):
                        _l.debug(errors)
                        # self.instruments_errors.append(errors)

    def book_create_event_schedules(self, actions, instrument_map, event_schedules_map):

        for order, action in enumerate(actions):
            try:
                action_instrument_event_schedule = action.transactiontypeactioninstrumenteventschedule
            except ObjectDoesNotExist:
                action_instrument_event_schedule = None

            if action_instrument_event_schedule and self.execute_action_condition(action_instrument_event_schedule):

                _l.debug('process event schedule: %s', action_instrument_event_schedule)
                _l.debug('instrument_map: %s', instrument_map)

                errors = {}

                event_schedule = EventSchedule()

                self._set_rel(errors=errors, values=self.values, default_value=None,
                              target=event_schedule, target_attr_name='instrument',
                              source=action_instrument_event_schedule, source_attr_name='instrument')

                if action_instrument_event_schedule.instrument_phantom is not None:
                    event_schedule.instrument = instrument_map[
                        action_instrument_event_schedule.instrument_phantom_id]

                self._set_rel(errors=errors, values=self.values, default_value=None,
                              target=event_schedule, target_attr_name='notification_class',
                              source=action_instrument_event_schedule, source_attr_name='notification_class')

                self._set_rel(errors=errors, values=self.values, default_value=None,
                              target=event_schedule, target_attr_name='periodicity',
                              source=action_instrument_event_schedule, source_attr_name='periodicity')

                self._set_rel(errors=errors, values=self.values, default_value=None,
                              target=event_schedule, target_attr_name='event_class',
                              source=action_instrument_event_schedule, source_attr_name='event_class')

                self._set_val(errors=errors, values=self.values, default_value='', validator=formula.validate_date,
                              target=event_schedule, target_attr_name='effective_date',
                              source=action_instrument_event_schedule, source_attr_name='effective_date')

                self._set_val(errors=errors, values=self.values, default_value='', validator=formula.validate_date,
                              target=event_schedule, target_attr_name='final_date',
                              source=action_instrument_event_schedule, source_attr_name='final_date')

                self._set_val(errors=errors, values=self.values, default_value='',
                              target=event_schedule, target_attr_name='notify_in_n_days',
                              source=action_instrument_event_schedule, source_attr_name='notify_in_n_days')

                self._set_val(errors=errors, values=self.values, default_value=False,
                              validator=formula.validate_bool,
                              target=event_schedule, target_attr_name='is_auto_generated',
                              source=action_instrument_event_schedule, source_attr_name='is_auto_generated')

                self._set_val(errors=errors, values=self.values, default_value='',
                              target=event_schedule, target_attr_name='periodicity_n',
                              source=action_instrument_event_schedule, source_attr_name='periodicity_n')

                self._set_val(errors=errors, values=self.values, default_value='',
                              target=event_schedule, target_attr_name='name',
                              source=action_instrument_event_schedule, source_attr_name='name')

                self._set_val(errors=errors, values=self.values, default_value='',
                              target=event_schedule, target_attr_name='description',
                              source=action_instrument_event_schedule, source_attr_name='description')

                try:

                    rebook_reaction = action_instrument_event_schedule.rebook_reaction

                    if self.process_mode == self.MODE_REBOOK:

                        if rebook_reaction == RebookReactionChoice.CREATE:
                            event_schedule.save()

                        if rebook_reaction == RebookReactionChoice.CREATE_IF_NOT_EXIST:
                            print('Skip')

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE:
                            EventSchedule.objects.filter(instrument=event_schedule.instrument).delete()

                            event_schedule.save()

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE_OR_SKIP:
                            print('Skip')

                        if rebook_reaction == RebookReactionChoice.CLEAR:
                            EventSchedule.objects.filter(instrument=event_schedule.instrument).delete()

                    else:

                        if rebook_reaction == RebookReactionChoice.CREATE:
                            event_schedule.save()

                        if rebook_reaction == RebookReactionChoice.CREATE_IF_NOT_EXIST:
                            event_schedule.save()

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE:
                            EventSchedule.objects.filter(instrument=event_schedule.instrument).delete()

                            event_schedule.save()

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE_OR_SKIP:
                            EventSchedule.objects.filter(instrument=event_schedule.instrument).delete()

                            event_schedule.save()

                        if rebook_reaction == RebookReactionChoice.CLEAR:
                            EventSchedule.objects.filter(instrument=event_schedule.instrument).delete()

                        if rebook_reaction is None:
                            event_schedule.save()

                except (ValueError, TypeError, IntegrityError):

                    self._add_err_msg(errors, 'non_field_errors',
                                      ugettext(
                                          'Invalid instrument event schedule action fields (please, use type convertion).'))
                except DatabaseError:
                    self._add_err_msg(errors, 'non_field_errors', ugettext('General DB error.'))
                else:
                    event_schedules_map[action.id] = event_schedule
                finally:
                    if bool(errors):
                        _l.debug(errors)
                        # self.instruments_errors.append(errors)

        return event_schedules_map

    def book_create_event_actions(self, actions, instrument_map, event_schedules_map):

        for order, action in enumerate(actions):
            try:
                action_instrument_event_schedule_action = action.transactiontypeactioninstrumenteventscheduleaction
            except ObjectDoesNotExist:
                action_instrument_event_schedule_action = None

            if action_instrument_event_schedule_action and self.execute_action_condition(
                    action_instrument_event_schedule_action):

                errors = {}

                event_schedule_action = EventScheduleAction()

                self._set_rel(errors=errors, values=self.values, default_value=None,
                              target=event_schedule_action, target_attr_name='event_schedule',
                              source=action_instrument_event_schedule_action, source_attr_name='event_schedule')

                if action_instrument_event_schedule_action.event_schedule_phantom is not None:
                    event_schedule = event_schedules_map[
                        action_instrument_event_schedule_action.event_schedule_phantom_id]

                    print('book_create_event_actions: event_schedule %s' % event_schedule)

                    event_schedule_action.event_schedule = event_schedule

                self._set_rel(errors=errors, values=self.values, default_value=None,
                              target=event_schedule_action, target_attr_name='transaction_type',
                              source=event_schedule_action.event_schedule.instrument.instrument_type,
                              source_attr_name=action_instrument_event_schedule_action.transaction_type_from_instrument_type)

                self._set_val(errors=errors, values=self.values, default_value=False,
                              validator=formula.validate_bool,
                              target=event_schedule_action, target_attr_name='is_sent_to_pending',
                              source=action_instrument_event_schedule_action, source_attr_name='is_sent_to_pending')

                self._set_val(errors=errors, values=self.values, default_value=False,
                              validator=formula.validate_bool,
                              target=event_schedule_action, target_attr_name='is_book_automatic',
                              source=action_instrument_event_schedule_action, source_attr_name='is_book_automatic')

                self._set_val(errors=errors, values=self.values, default_value=0,
                              target=event_schedule_action, target_attr_name='button_position',
                              source=action_instrument_event_schedule_action, source_attr_name='button_position')

                self._set_val(errors=errors, values=self.values, default_value='',
                              target=event_schedule_action, target_attr_name='text',
                              source=action_instrument_event_schedule_action, source_attr_name='text')

                try:

                    rebook_reaction = action_instrument_event_schedule_action.rebook_reaction

                    if self.process_mode == self.MODE_REBOOK:

                        if rebook_reaction == RebookReactionChoice.CREATE:
                            event_schedule_action.save()

                        if rebook_reaction == RebookReactionChoice.CREATE_IF_NOT_EXIST:
                            print('Skip')

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE:
                            EventScheduleAction.objects.filter(
                                event_schedule=event_schedule_action.event_schedule).delete()

                            event_schedule_action.save()

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE_OR_SKIP:
                            print('Skip')

                        if rebook_reaction == RebookReactionChoice.CLEAR:
                            EventScheduleAction.objects.filter(
                                event_schedule=event_schedule_action.event_schedule).delete()

                    else:

                        if rebook_reaction == RebookReactionChoice.CREATE:
                            event_schedule_action.save()

                        if rebook_reaction == RebookReactionChoice.CREATE_IF_NOT_EXIST:
                            event_schedule_action.save()

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE:
                            EventScheduleAction.objects.filter(
                                event_schedule=event_schedule_action.event_schedule).delete()

                            event_schedule_action.save()

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE_OR_SKIP:
                            EventScheduleAction.objects.filter(
                                event_schedule=event_schedule_action.event_schedule).delete()

                            event_schedule_action.save()

                        if rebook_reaction == RebookReactionChoice.CLEAR:
                            EventScheduleAction.objects.filter(
                                event_schedule=event_schedule_action.event_schedule).delete()

                        if rebook_reaction is None:
                            event_schedule_action.save()

                except (ValueError, TypeError, IntegrityError) as e:

                    self._add_err_msg(errors, 'non_field_errors',
                                      ugettext(
                                          'Invalid instrument event schedule action action fields (please, use type convertion).'))
                except DatabaseError:
                    self._add_err_msg(errors, 'non_field_errors', ugettext('General DB error.'))
                finally:
                    if bool(errors):
                        _l.debug(errors)
                        # self.instruments_errors.append(errors)

    # def to_dict(self, obj):
    #     return json.loads(json.dumps(obj, cls=DjangoJSONEncoder, sort_keys=True))

    def book_execute_commands(self, actions):

        print('book_execute_commands %s' % actions)

        for order, action in enumerate(actions):
            try:
                execute_command = action.transactiontypeactionexecutecommand
            except ObjectDoesNotExist:
                execute_command = None

            if execute_command and self.execute_action_condition(execute_command):

                # print('process execute command: %s', execute_command)
                # print('process execute command expr: %s', execute_command.expr)

                errors = {}

                names = {}

                for key, value in self.values.items():
                    names[key] = formula.value_prepare(value)

                # names = self.to_dict(names)

                try:
                    result = formula.safe_eval(execute_command.expr, names=names,
                                               context=self._context)

                    # print('result %s', result)

                except (ValueError, TypeError, IntegrityError, formula.InvalidExpression):

                    self._add_err_msg(errors, 'non_field_errors',
                                      ugettext(
                                          'Invalid execute command (Invalid Expression)'))
                except DatabaseError:
                    self._add_err_msg(errors, 'non_field_errors', ugettext('General DB error.'))
                finally:
                    if bool(errors):
                        _l.debug(errors)
                        # self.instruments_errors.append(errors)

    def transaction_access_check(self, transaction, group, account_permissions, portfolio_permissions):

        result = False

        account_result = False
        portfolio_result = False

        for perm in account_permissions:

            if perm.group.id == group.id:

                if (transaction.account_position and transaction.account_position.id == perm.object_id) and (
                        transaction.account_cash and transaction.account_cash.id == perm.object_id):
                    account_result = True

        for perm in portfolio_permissions:

            if perm.group.id == group.id:

                if transaction.portfolio and transaction.portfolio.id == perm.object_id:
                    portfolio_result = True

        if account_result and portfolio_result:
            result = True

        return result

    def get_access_to_inputs(self, group):

        result = None

        portfolios = []
        accounts = []

        for input in self.complex_transaction.inputs.all():

            if input.portfolio:
                portfolios.append(input.portfolio_id)

            if input.account:
                accounts.append(input.account_id)

        count = 0

        for id in portfolios:

            try:

                perm = GenericObjectPermission.objects.filter(object_id=id, group=group.id)

                if len(perm):
                    count = count + 1

            except GenericObjectPermission.DoesNotExist:
                pass

        for id in accounts:

            try:

                perm = GenericObjectPermission.objects.filter(object_id=id, group=group.id)

                if len(perm):
                    count = count + 1

            except GenericObjectPermission.DoesNotExist:
                pass

        if count == len(accounts) + len(portfolios):
            result = True

        if count > 0:
            result = 'partial_view'

        if count == 0:
            result = False

        return result

    def assign_permissions_to_transaction(self, transaction):

        perms = []

        groups = Group.objects.filter(master_user=self.transaction_type.master_user)

        account_codename = 'view_account'
        portfolio_codename = 'view_portfolio'

        account_permissions = GenericObjectPermission.objects.filter(group__in=groups,
                                                                     permission__codename=account_codename)
        portfolio_permissions = GenericObjectPermission.objects.filter(group__in=groups,
                                                                       permission__codename=portfolio_codename)

        for group in groups:

            has_access = self.transaction_access_check(transaction, group, account_permissions,
                                                       portfolio_permissions)

            if has_access:
                perms.append({'group': group, 'permission': 'view_transaction'})

        _l.debug('perms %s' % perms)

        assign_perms3(transaction, perms)

    def assign_permissions_to_complex_transaction(self):

        groups = Group.objects.filter(master_user=self.transaction_type.master_user)

        perms = []

        transactions = self.complex_transaction.transactions.all()

        ttype_permissions = self.transaction_type.object_permissions.all()

        permissions_total = len(transactions)

        for group in groups:

            codename = None

            ttype_access = False

            inputs_access = self.get_access_to_inputs(group)

            permissions_count = 0

            for transaction in transactions:

                for perm in transaction.object_permissions.all():

                    if perm.group.id == group.id:
                        permissions_count = permissions_count + 1

            # _l.debug('groupid %s permissions_count %s' % (group.name, permissions_count))

            print('permissions_count %s' % permissions_count)
            print('permissions_total %s' % permissions_total)

            if permissions_count == permissions_total:
                codename = 'view_complextransaction'

            if permissions_count < permissions_total and permissions_count != 0:

                if self.complex_transaction.visibility_status == ComplexTransaction.SHOW_PARAMETERS:
                    codename = 'view_complextransaction_show_parameters'

                if self.complex_transaction.visibility_status == ComplexTransaction.HIDE_PARAMETERS:
                    codename = 'view_complextransaction_hide_parameters'

            if permissions_count == 0:
                codename = None

            for perm in ttype_permissions:

                if perm.group:
                    if perm.group.id == group.id and perm.permission.codename == 'view_transactiontype':
                        ttype_access = True

            if not ttype_access and codename is not None:
                codename = 'view_complextransaction_hide_parameters'

            print('inputs_access %s' % inputs_access)
            print('ttype_access %s' % ttype_access)

            if inputs_access == 'partial_view':

                if self.complex_transaction.visibility_status == ComplexTransaction.SHOW_PARAMETERS:
                    codename = 'view_complextransaction_show_parameters'

                if self.complex_transaction.visibility_status == ComplexTransaction.HIDE_PARAMETERS:
                    codename = 'view_complextransaction_hide_parameters'

            if codename:
                perms.append({'group': group, 'permission': codename})

        _l.debug("complex transactions perms %s" % perms)

        assign_perms3(self.complex_transaction, perms)

    def assign_permissions_to_pending_complex_transaction(self):

        groups = Group.objects.filter(master_user=self.transaction_type.master_user)

        perms = []

        for group in groups:

            codename = None

            inputs_access = self.get_access_to_inputs(group)

            if inputs_access:

                codename = 'view_complextransaction'

            elif inputs_access == 'partial_view':

                if self.complex_transaction.visibility_status == ComplexTransaction.SHOW_PARAMETERS:
                    codename = 'view_complextransaction_show_parameters'

                if self.complex_transaction.visibility_status == ComplexTransaction.HIDE_PARAMETERS:
                    codename = 'view_complextransaction_hide_parameters'

            if codename:
                perms.append({'group': group, 'permission': codename})

        _l.debug("complex transactions pending perms %s" % perms)

        assign_perms3(self.complex_transaction, perms)

    def book_create_transactions(self, actions, master_user, instrument_map):

        for order, action in enumerate(actions):
            try:
                action_transaction = action.transactiontypeactiontransaction
            except ObjectDoesNotExist:
                action_transaction = None

            if action_transaction and self.execute_action_condition(action_transaction):

                _l.debug('process transaction: %s', action_transaction)
                errors = {}
                transaction = Transaction(master_user=master_user)
                transaction.complex_transaction = self.complex_transaction
                transaction.complex_transaction_order = self.next_transaction_order()
                transaction.transaction_class = action_transaction.transaction_class

                self._set_rel(errors=errors, values=self.values, default_value=None,
                              target=transaction, target_attr_name='instrument',
                              source=action_transaction, source_attr_name='instrument')
                if action_transaction.instrument_phantom is not None:
                    transaction.instrument = instrument_map[action_transaction.instrument_phantom_id]
                self._set_rel(errors=errors, values=self.values, default_value=master_user.currency,
                              target=transaction, target_attr_name='transaction_currency',
                              source=action_transaction, source_attr_name='transaction_currency')
                self._set_val(errors=errors, values=self.values, default_value=0.0,
                              target=transaction, target_attr_name='position_size_with_sign',
                              source=action_transaction, source_attr_name='position_size_with_sign')

                self._set_rel(errors=errors, values=self.values, default_value=master_user.currency,
                              target=transaction, target_attr_name='settlement_currency',
                              source=action_transaction, source_attr_name='settlement_currency')
                self._set_val(errors=errors, values=self.values, default_value=0.0,
                              target=transaction, target_attr_name='cash_consideration',
                              source=action_transaction, source_attr_name='cash_consideration')
                self._set_val(errors=errors, values=self.values, default_value=0.0,
                              target=transaction, target_attr_name='principal_with_sign',
                              source=action_transaction, source_attr_name='principal_with_sign')
                self._set_val(errors=errors, values=self.values, default_value=0.0,
                              target=transaction, target_attr_name='carry_with_sign',
                              source=action_transaction, source_attr_name='carry_with_sign')
                self._set_val(errors=errors, values=self.values, default_value=0.0,
                              target=transaction, target_attr_name='overheads_with_sign',
                              source=action_transaction, source_attr_name='overheads_with_sign')

                self._set_rel(errors=errors, values=self.values, default_value=master_user.portfolio,
                              target=transaction, target_attr_name='portfolio',
                              source=action_transaction, source_attr_name='portfolio')
                self._set_rel(errors=errors, values=self.values, default_value=master_user.account,
                              target=transaction, target_attr_name='account_position',
                              source=action_transaction, source_attr_name='account_position')
                self._set_rel(errors=errors, values=self.values, default_value=master_user.account,
                              target=transaction, target_attr_name='account_cash',
                              source=action_transaction, source_attr_name='account_cash')
                self._set_rel(errors=errors, values=self.values, default_value=master_user.account,
                              target=transaction, target_attr_name='account_interim',
                              source=action_transaction, source_attr_name='account_interim')

                self._set_val(errors=errors, values=self.values, default_value=self._now,
                              target=transaction, target_attr_name='accounting_date',
                              source=action_transaction, source_attr_name='accounting_date',
                              validator=formula.validate_date)
                self._set_val(errors=errors, values=self.values, default_value=self._now,
                              target=transaction, target_attr_name='cash_date',
                              source=action_transaction, source_attr_name='cash_date',
                              validator=formula.validate_date)

                self._set_rel(errors=errors, values=self.values, default_value=master_user.strategy1,
                              target=transaction, target_attr_name='strategy1_position',
                              source=action_transaction, source_attr_name='strategy1_position')
                self._set_rel(errors=errors, values=self.values, default_value=master_user.strategy1,
                              target=transaction, target_attr_name='strategy1_cash',
                              source=action_transaction, source_attr_name='strategy1_cash')
                self._set_rel(errors=errors, values=self.values, default_value=master_user.strategy2,
                              target=transaction, target_attr_name='strategy2_position',
                              source=action_transaction, source_attr_name='strategy2_position')
                self._set_rel(errors=errors, values=self.values, default_value=master_user.strategy2,
                              target=transaction, target_attr_name='strategy2_cash',
                              source=action_transaction, source_attr_name='strategy2_cash')
                self._set_rel(errors=errors, values=self.values, default_value=master_user.strategy3,
                              target=transaction, target_attr_name='strategy3_position',
                              source=action_transaction, source_attr_name='strategy3_position')
                self._set_rel(errors=errors, values=self.values, default_value=master_user.strategy3,
                              target=transaction, target_attr_name='strategy3_cash',
                              source=action_transaction, source_attr_name='strategy3_cash')

                self._set_rel(errors=errors, values=self.values, default_value=master_user.responsible,
                              target=transaction, target_attr_name='responsible',
                              source=action_transaction, source_attr_name='responsible')
                self._set_rel(errors=errors, values=self.values, default_value=master_user.counterparty,
                              target=transaction, target_attr_name='counterparty',
                              source=action_transaction, source_attr_name='counterparty')

                self._set_rel(errors=errors, values=self.values, default_value=None,
                              target=transaction, target_attr_name='linked_instrument',
                              source=action_transaction, source_attr_name='linked_instrument')
                if action_transaction.linked_instrument_phantom is not None:
                    transaction.linked_instrument = instrument_map[action_transaction.linked_instrument_phantom_id]

                self._set_rel(errors=errors, values=self.values, default_value=None,
                              target=transaction, target_attr_name='allocation_balance',
                              source=action_transaction, source_attr_name='allocation_balance')
                if action_transaction.allocation_balance_phantom is not None:
                    transaction.allocation_balance = instrument_map[action_transaction.allocation_balance_phantom_id]

                self._set_rel(errors=errors, values=self.values, default_value=None,
                              target=transaction, target_attr_name='allocation_pl',
                              source=action_transaction, source_attr_name='allocation_pl')
                if action_transaction.allocation_pl_phantom is not None:
                    transaction.allocation_pl = instrument_map[action_transaction.allocation_pl_phantom_id]

                self._set_val(errors=errors, values=self.values, default_value=0.0,
                              target=transaction, target_attr_name='reference_fx_rate',
                              source=action_transaction, source_attr_name='reference_fx_rate')
                self._set_val(errors=errors, values=self.values, default_value=0.0,
                              target=transaction, target_attr_name='factor',
                              source=action_transaction, source_attr_name='factor')
                self._set_val(errors=errors, values=self.values, default_value=0.0,
                              target=transaction, target_attr_name='trade_price',
                              source=action_transaction, source_attr_name='trade_price')
                self._set_val(errors=errors, values=self.values, default_value=0.0,
                              target=transaction, target_attr_name='position_amount',
                              source=action_transaction, source_attr_name='position_amount')
                self._set_val(errors=errors, values=self.values, default_value=0.0,
                              target=transaction, target_attr_name='principal_amount',
                              source=action_transaction, source_attr_name='principal_amount')
                self._set_val(errors=errors, values=self.values, default_value=0.0,
                              target=transaction, target_attr_name='carry_amount',
                              source=action_transaction, source_attr_name='carry_amount')
                self._set_val(errors=errors, values=self.values, default_value=0.0,
                              target=transaction, target_attr_name='overheads',
                              source=action_transaction, source_attr_name='overheads')

                transaction.carry_with_sign = format_float_to_2(transaction.carry_with_sign)
                transaction.principal_with_sign = format_float_to_2(transaction.principal_with_sign)
                transaction.overheads_with_sign = format_float_to_2(transaction.overheads_with_sign)

                transaction.cash_consideration = format_float_to_2(transaction.cash_consideration)

                print('action_transaction.notes')
                print(action_transaction.notes)
                print(self.values)

                if action_transaction.notes is not None:
                    self._set_val(errors=errors, values=self.values, default_value='',
                                  target=transaction, target_attr_name='notes',
                                  source=action_transaction, source_attr_name='notes')

                transaction_date_source = 'null'

                if transaction.accounting_date is None:
                    transaction.accounting_date = self._now
                else:
                    transaction_date_source = 'accounting_date'

                if transaction.cash_date is None:
                    transaction.cash_date = self._now
                else:
                    transaction_date_source = 'cash_date'

                # Set transaction date below

                if transaction_date_source == 'accounting_date':
                    transaction.transaction_date = transaction.accounting_date
                elif transaction_date_source == 'cash_date':
                    transaction.transaction_date = transaction.cash_date
                elif transaction_date_source == 'null':
                    transaction.transaction_date = min(transaction.accounting_date, transaction.cash_date)

                try:
                    # transaction.transaction_date = min(transaction.accounting_date, transaction.cash_date)
                    transaction.save()
                    self.assign_permissions_to_transaction(transaction)

                except (ValueError, TypeError, IntegrityError) as error:

                    _l.debug(error)

                    self._add_err_msg(errors, 'non_field_errors',
                                      ugettext('Invalid transaction action fields (please, use type convertion).'))
                except DatabaseError:
                    self._add_err_msg(errors, 'non_field_errors', ugettext('General DB error.'))
                else:
                    self.transactions.append(transaction)
                finally:

                    _l.debug("Transaction action errors %s " % errors)

                    if bool(errors):
                        self.transactions_errors.append(errors)

    def _save_inputs(self):

        self.complex_transaction.inputs.all().delete()

        for ti in self.transaction_type.inputs.all():
            val = self.values.get(ti.name, None)

            ci = ComplexTransactionInput()
            ci.complex_transaction = self.complex_transaction
            ci.transaction_type_input = ti

            if ti.value_type == TransactionTypeInput.STRING or ti.value_type == TransactionTypeInput.SELECTOR:
                if val is None:
                    val = ''
                ci.value_string = val
            elif ti.value_type == TransactionTypeInput.NUMBER:
                if val is None:
                    val = 0.0
                ci.value_float = format_float(val)
            elif ti.value_type == TransactionTypeInput.DATE:
                if val is None:
                    val = date.min
                ci.value_date = val
            elif ti.value_type == TransactionTypeInput.RELATION:

                model_class = ti.content_type.model_class()

                if issubclass(model_class, Account):
                    ci.account = val
                elif issubclass(model_class, Currency):
                    ci.currency = val
                elif issubclass(model_class, Instrument):
                    ci.instrument = val
                elif issubclass(model_class, InstrumentType):
                    ci.instrument_type = val
                elif issubclass(model_class, Counterparty):
                    ci.counterparty = val
                elif issubclass(model_class, Responsible):
                    ci.responsible = val
                elif issubclass(model_class, Strategy1):
                    ci.strategy1 = val
                elif issubclass(model_class, Strategy2):
                    ci.strategy2 = val
                elif issubclass(model_class, Strategy3):
                    ci.strategy3 = val
                elif issubclass(model_class, DailyPricingModel):
                    ci.daily_pricing_model = val
                elif issubclass(model_class, PaymentSizeDetail):
                    ci.payment_size_detail = val
                elif issubclass(model_class, Portfolio):
                    ci.portfolio = val
                elif issubclass(model_class, PriceDownloadScheme):
                    ci.price_download_scheme = val
                elif issubclass(model_class, PricingPolicy):
                    ci.pricing_policy = val
                elif issubclass(model_class, Periodicity):
                    ci.periodicity = val
                elif issubclass(model_class, AccrualCalculationModel):
                    ci.accrual_calculation_model = val
                elif issubclass(model_class, EventClass):
                    ci.event_class = val
                elif issubclass(model_class, NotificationClass):
                    ci.notification_class = val

            ci.save()

    def execute_user_fields_expressions(self):

        print('execute_user_fields_expressions')

        ctrn = formula.value_prepare(self.complex_transaction)
        trns = self.complex_transaction.transactions.all()

        names = {
            'complex_transaction': ctrn,
            'transactions': trns,
        }

        for key, value in self.values.items():
            names[key] = value

        fields = [
            'user_text_1', 'user_text_2', 'user_text_3', 'user_text_4', 'user_text_5',
            'user_text_6', 'user_text_7', 'user_text_8', 'user_text_9', 'user_text_10',

            'user_text_11', 'user_text_12', 'user_text_13', 'user_text_14', 'user_text_15',
            'user_text_16', 'user_text_17', 'user_text_18', 'user_text_19', 'user_text_20',

            'user_number_1', 'user_number_2', 'user_number_3', 'user_number_4', 'user_number_5',
            'user_number_6', 'user_number_7', 'user_number_8', 'user_number_9', 'user_number_10',

            'user_number_11', 'user_number_12', 'user_number_13', 'user_number_14', 'user_number_15',
            'user_number_16', 'user_number_17', 'user_number_18', 'user_number_19', 'user_number_20',

            'user_date_1', 'user_date_2', 'user_date_3', 'user_date_4', 'user_date_5'
        ]

        for field_key in fields:

            # print('field_key')

            if getattr(self.complex_transaction.transaction_type, field_key):

                try:

                    # print('epxr %s' % getattr(self.complex_transaction.transaction_type, field_key))

                    setattr(self.complex_transaction, field_key, formula.safe_eval(
                        getattr(self.complex_transaction.transaction_type, field_key), names=names,
                        context=self._context))

                except formula.InvalidExpression:
                    setattr(self.complex_transaction, field_key, '<InvalidExpression>')

    def execute_complex_transaction_text_and_date(self):

        print('execute_complex_transaction_text_and_date')

        if self.complex_transaction.transaction_type.display_expr:

            ctrn = formula.value_prepare(self.complex_transaction)
            trns = self.complex_transaction.transactions.all()

            names = {
                'complex_transaction': ctrn,
                'transactions': trns,
            }

            for key, value in self.values.items():
                names[key] = value

            try:
                self.complex_transaction.text = formula.safe_eval(
                    self.complex_transaction.transaction_type.display_expr, names=names,
                    context=self._context)
            except formula.InvalidExpression:
                self.complex_transaction.text = '<InvalidExpression>'

        if self.complex_transaction.transaction_type.date_expr:

            ctrn = formula.value_prepare(self.complex_transaction)
            trns = self.complex_transaction.transactions.all()

            names = {
                'complex_transaction': ctrn,
                'transactions': trns,
            }

            for key, value in self.values.items():
                names[key] = value

            self.complex_transaction.date = self._now  # as default

            try:
                self.complex_transaction.date = formula.safe_eval(self.complex_transaction.transaction_type.date_expr,
                                                                  names=names,
                                                                  context=self._context)
            except formula.InvalidExpression:

                self.complex_transaction.date = self._now

        else:
            self.complex_transaction.date = self._now

    def process_as_pending(self):

        complex_transaction_errors = {}
        if self.complex_transaction.date is None:
            self.complex_transaction.date = self._now  # set by default

            self._set_val(errors=complex_transaction_errors, values=self.values, default_value=self._now,
                          target=self.complex_transaction, target_attr_name='date',
                          source=self.transaction_type, source_attr_name='date_expr',
                          validator=formula.validate_date)

        if bool(complex_transaction_errors):
            self.complex_transaction_errors.append(complex_transaction_errors)

        self.complex_transaction.status = ComplexTransaction.PENDING

        self.complex_transaction.save()

        self.execute_complex_transaction_text_and_date()

        self.execute_user_fields_expressions()

        self.complex_transaction.save()

        self._save_inputs()

        self.assign_permissions_to_pending_complex_transaction()

    def process(self):

        if self.process_mode == self.MODE_RECALCULATE:

            return self.process_recalculate()

        _l.debug('process: %s, values=%s', self.transaction_type, self.values)

        print('process self.process_mode %s' % self.process_mode)

        master_user = self.transaction_type.master_user

        instrument_map = {}
        event_schedules_map = {}
        actions = self.transaction_type.actions.order_by('order').all()

        instrument_map = self.book_create_instruments(actions, master_user, instrument_map)

        print('instrument_map process %s ' % instrument_map)

        self.book_create_factor_schedules(actions, instrument_map)
        self.book_create_manual_pricing_formulas(actions, instrument_map)
        self.book_create_accrual_calculation_schedules(actions, instrument_map)
        event_schedules_map = self.book_create_event_schedules(actions, instrument_map, event_schedules_map)

        self.book_create_event_actions(actions, instrument_map, event_schedules_map)

        self.book_execute_commands(actions)

        # complex_transaction
        complex_transaction_errors = {}
        if self.complex_transaction.date is None:
            self.complex_transaction.date = self._now  # set by default

            self._set_val(errors=complex_transaction_errors, values=self.values, default_value=self._now,
                          target=self.complex_transaction, target_attr_name='date',
                          source=self.transaction_type, source_attr_name='date_expr',
                          validator=formula.validate_date)

        if bool(complex_transaction_errors):
            self.complex_transaction_errors.append(complex_transaction_errors)

        print("complex_transaction.date %s" % self.complex_transaction.date)

        self.complex_transaction.save()

        self._save_inputs()

        # print(self.complex_transaction.transactions.all())

        self.complex_transaction.transactions.all().delete()

        self.book_create_transactions(actions, master_user, instrument_map)

        self.execute_complex_transaction_text_and_date()

        self.execute_user_fields_expressions()

        self.complex_transaction.save()  # save executed text and date expression

        self.assign_permissions_to_complex_transaction()

        if not self.has_errors and self.transactions:
            for trn in self.transactions:
                trn.calc_cash_by_formulas()

        if self.complex_transaction.status == ComplexTransaction.PENDING:
            self.complex_transaction.transactions.all().delete()

        if self.complex_transaction.transaction_type.type == TransactionType.TYPE_PROCEDURE:
            self.complex_transaction.delete()

    def process_recalculate(self):
        if not self.recalculate_inputs:
            return

        inputs = {i.name: i for i in self.inputs}

        for name in self.recalculate_inputs:
            inp = inputs[name]
            if inp.can_recalculate:

                if inp.value_type in [TransactionTypeInput.RELATION]:

                    errors = {}
                    try:
                        res = formula.safe_eval(inp.value_expr, names=self.values, now=self._now, context=self._context)

                        Model = apps.get_model(app_label=inp.content_type.app_label, model_name=inp.content_type.model)

                        try:

                            if inp.content_type.model == 'pricedownloadscheme':
                                self.values[name] = Model.objects.get(
                                    master_user=self.transaction_type.master_user,
                                    scheme_name='-')
                            elif inp.content_type.model == 'dailypricingmodel' or inp.content_type.model == 'paymentsizedetail':
                                self.values[name] = Model.objects.get(system_code='-')
                            else:
                                self.values[name] = Model.objects.get(master_user=self.transaction_type.master_user,
                                                                      user_code=res)
                        except Model.DoesNotExist:
                            raise formula.InvalidExpression

                    except formula.InvalidExpression as e:

                        ecosystem_default = EcosystemDefault.objects.get(master_user=self.transaction_type.master_user)

                        print('error')
                        print(inp.content_type)

                        entity_map = {
                            'instrument': 'instrument',
                            'instrumenttype': 'instrument_type',
                            'account': 'account',
                            'currency': 'currency',
                            'counterparty': 'counterparty',
                            'responsible': 'responsible',
                            'portfolio': 'portfolio',
                            'strategy1': 'strategy1',
                            'strategy2': 'strategy2',
                            'strategy3': 'strategy3',
                            'dailypricingmodel': 'daily_pricing_model',
                            'paymentsizedetail': 'payment_size_detail',
                            'pricedownloadscheme': 'price_download_scheme',
                            'pricingpolicy': 'pricing_policy',
                            'periodicity': 'periodicity',
                            'accrualcalculationmodel': 'accrual_calculation_model',
                            'eventclass': 'event_class',
                            'notificationclass': 'notification_class',
                        }

                        key = entity_map[inp.content_type.model]

                        if hasattr(ecosystem_default, key):
                            res = getattr(ecosystem_default, key)
                            self.values[name] = res
                        else:
                            self._set_eval_error(errors, inp.name, inp.value_expr, e)
                            self.value_errors.append(errors)

                else:
                    errors = {}
                    try:
                        res = formula.safe_eval(inp.value_expr, names=self.values, now=self._now, context=self._context)
                        self.values[name] = res
                    except formula.InvalidExpression as e:
                        self._set_eval_error(errors, inp.name, inp.value_expr, e)
                        self.value_errors.append(errors)

    @property
    def has_errors(self):
        return bool(self.instruments_errors) or \
               any(bool(e) for e in self.value_errors) or \
               any(bool(e) for e in self.complex_transaction_errors) or \
               any(bool(e) for e in self.transactions_errors)

    def _set_val(self, errors, values, default_value, target, target_attr_name, source, source_attr_name,
                 validator=None):
        value = getattr(source, source_attr_name)
        if value:
            try:
                value = formula.safe_eval(value, names=values, now=self._now, context=self._context)
            except formula.InvalidExpression as e:
                self._set_eval_error(errors, source_attr_name, value, e)
                return
            if callable(validator):
                value = validator(value)
        else:
            value = default_value
        setattr(target, target_attr_name, value)

    def _set_rel(self, errors, values, default_value, target, target_attr_name, source, source_attr_name):
        value = getattr(source, source_attr_name, None)
        if value:
            pass
        else:
            from_input = getattr(source, '%s_input' % source_attr_name)
            if from_input:
                value = values[from_input.name]
        if not value:
            value = default_value
        if value is not None:
            setattr(target, target_attr_name, value)

    def _instrument_assign_permission(self, instr, object_permissions):
        perms = []
        for op in object_permissions:
            perms.append({
                'group': op.group,
                'member': op.member,
                'permission': op.permission.codename.replace('_transactiontype', '_instrument')
            })
        assign_perms3(instr, perms)

    def _set_eval_error(self, errors, attr_name, expression, exc=None):
        msg = ugettext('Invalid expression "%(expression)s".') % {
            'expression': expression,
        }
        return self._add_err_msg(errors, attr_name, msg)

    def _add_err_msg(self, errors, key, msg):
        msgs = errors.get(key, None) or []
        if msg not in msgs:
            msgs.append(msg)
            errors[key] = msgs
        return msgs

        # def process_expressions(self):
        #     self.expressions_error = {}
        #     self.expressions_result = {}
        #     if not self.expressions:
        #         return
        #     for key, expr in self.expressions.items():
        #         self.expressions_result[key] = None
        #         self.expressions_error[key] = None
        #         if expr:
        #             try:
        #                 self.expressions_result[key] = formula.safe_eval(expr, names=self.values, now=self._now,
        #                                                                  context=self._context)
        #             except formula.InvalidExpression as e:
        #                 self._set_eval_error(self.expressions_error, key, expr, e)
