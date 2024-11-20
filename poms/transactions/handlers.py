import contextlib
import json
import logging
import time
import traceback
from datetime import date, datetime

from django.apps import apps
# from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db import DatabaseError, IntegrityError
from django.utils.translation import gettext_lazy
from rest_framework.exceptions import ValidationError

from poms.accounts.models import Account
from poms.common.utils import date_now, format_float, format_float_to_2
from poms.counterparties.models import Counterparty, Responsible
from poms.currencies.models import Currency
from poms.expressions_engine import formula
from poms.instruments.models import (
    AccrualCalculationModel,
    AccrualCalculationSchedule,
    DailyPricingModel,
    EventSchedule,
    EventScheduleAction,
    Instrument,
    InstrumentFactorSchedule,
    InstrumentType,
    ManualPricingFormula,
    PaymentSizeDetail,
    Periodicity,
    PricingPolicy,
)
from poms.portfolios.models import Portfolio
from poms.reconciliation.models import TransactionTypeReconField
from poms.strategies.models import Strategy1, Strategy2, Strategy3
from poms.system_messages.handlers import send_system_message
from poms.transactions.models import (
    ComplexTransaction,
    ComplexTransactionInput,
    EventClass,
    NotificationClass,
    RebookReactionChoice,
    Transaction,
    TransactionType,
    TransactionTypeInput,
)
from poms.transactions.utils import generate_user_fields
from poms.users.models import EcosystemDefault

_l = logging.getLogger("poms.transactions")


class UniqueCodeError(ValidationError):
    message = "Unique code already exists"


class TransactionTypeProcess:
    # if store is false, then operations must be rollback outside,
    # for example, in view...
    MODE_BOOK = "book"
    MODE_REBOOK = "rebook"
    MODE_RECALCULATE = "recalculate"

    def record_execution_progress(self, message, obj=None):
        # _l.debug('record_execution_progress.message %s' % message)

        if self.record_execution_log:
            if not self.complex_transaction.execution_log:
                self.complex_transaction.execution_log = ""

            _time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            self.complex_transaction.execution_log = (
                    self.complex_transaction.execution_log
                    + "["
                    + str(_time)
                    + "] "
                    + message
                    + "\n"
            )

            if obj:
                self.complex_transaction.execution_log = (
                        self.complex_transaction.execution_log
                        + json.dumps(obj, indent=4, default=str)
                        + "\n"
                )

    def __init__(
            self,
            process_mode=None,
            transaction_type=None,
            default_values=None,
            values=None,
            recalculate_inputs=None,
            value_errors=None,
            general_errors=None,
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
            context_values=None,  # context_values = CONTEXT VARIABLES
            uniqueness_reaction=None,
            execution_context="manual",
            member=None,
            source=None,
            clear_execution_log=True,
            record_execution_log=True,
            linked_import_task=None,
    ):
        _l.info(
            f"TransactionTypeProcess transaction_type={transaction_type} "
            f"process_mode={process_mode} context_values={context_values} "
            f"linked_import_task={linked_import_task}"
        )

        master_user = transaction_type.master_user
        self.ecosystem_default = EcosystemDefault.objects.get(master_user=master_user)

        self.member = member
        self.transaction_type = transaction_type
        self.process_mode = process_mode or TransactionTypeProcess.MODE_BOOK
        self.execution_context = execution_context
        self.linked_import_task = linked_import_task
        self.clear_execution_log = clear_execution_log
        self.record_execution_log = record_execution_log
        self.default_values = default_values or {}
        self.context_values = context_values or {}
        self.value_errors = value_errors or []
        self.general_errors = general_errors or []
        self.transactions = transactions or []
        self.instruments = instruments or []
        self.instruments_errors = instruments_errors or []
        self.complex_transaction_errors = complex_transaction_errors or []
        self.complex_transaction_status = complex_transaction_status
        self.transactions_errors = transactions_errors or []
        self.recalculate_inputs = recalculate_inputs or []
        self.source = source  # JSON object that contains source dictionary from broker
        self.uniqueness_reaction = uniqueness_reaction or (
            self.transaction_type.transaction_unique_code_options
        )
        self._now = now or date_now()
        self.next_transaction_order = (
                transaction_order_gen or self._next_transaction_order_default
        )
        self.next_fake_id = fake_id_gen or self._next_fake_id_default
        self.uniqueness_status = None

        # set complex-transaction params
        self.complex_transaction: ComplexTransaction = complex_transaction
        if self.complex_transaction is None:
            self.complex_transaction = ComplexTransaction(
                transaction_type=self.transaction_type,
                date=self._now,
                master_user=master_user,
                owner=member,
            )
        self.complex_transaction.visibility_status = (
            self.transaction_type.visibility_status
        )
        self.complex_transaction.linked_import_task = self.linked_import_task

        self.complex_transaction_status = complex_transaction_status

        if complex_transaction_status:
            self.complex_transaction.status_id = complex_transaction_status

        if complex_transaction and not complex_transaction_status:
            self.complex_transaction_status = complex_transaction.status_id

        self._context = context
        self._context["transaction_type"] = self.transaction_type
        self._id_seq = 0
        self._transaction_order_seq = 0

        self.inputs = list(self.transaction_type.inputs.all())
        if values is None:
            # needs self.inputs to be defined, also checks complex_transaction inputs
            self._set_values()
        else:
            self.values = values
            for i in range(10):
                self.values[f"phantom_instrument_{i}"] = None

        if self.clear_execution_log:
            self.complex_transaction.execution_log = ""

        self.complex_transaction.owner = self.member
        # self.complex_transaction.save()  # it will create empty transaction in db!

        self.record_execution_progress("Booking Complex Transaction")
        self.record_execution_progress(f"Start {date_now()} ")
        self.record_execution_progress(
            f"Transaction Type: {self.transaction_type.user_code}"
        )
        self.record_execution_progress(f"Member: {self.member}")
        self.record_execution_progress(f"Execution_context: {execution_context}")
        self.record_execution_progress(f"Linked Import Task: {linked_import_task}")
        # self.record_execution_progress('==== INPUT CONTEXT VALUES ====', context_values)
        # self.record_execution_progress('==== INPUT VALUES ====', values)

    @property
    def is_book(self):
        return self.process_mode == self.MODE_BOOK

    @property
    def is_rebook(self):
        return self.process_mode == self.MODE_REBOOK and self.complex_transaction.id

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
        if action is None:
            return False

        if action.condition_expr is None or action.condition_expr == "":
            return True

        try:
            result = formula.safe_eval(
                action.condition_expr, names=self.values, context=self._context
            )

            return result not in ["False", False]

        except formula.InvalidExpression as e:
            # _l.debug('execute_action_condition.Action is skipped %s' % e)

            return False

    def _set_values(self):
        self.record_execution_progress("==== SETTINGS VALUES ====")

        def _get_val_by_model_cls_for_transaction_type_input(
                master_user, value, model_class
        ):
            try:
                if issubclass(model_class, Account):
                    return Account.objects.get(master_user=master_user, user_code=value)
                elif issubclass(model_class, Currency):
                    return Currency.objects.get(
                        master_user=master_user, user_code=value
                    )
                elif issubclass(model_class, Instrument):
                    return Instrument.objects.get(
                        master_user=master_user, user_code=value
                    )
                elif issubclass(model_class, InstrumentType):
                    return InstrumentType.objects.get(
                        master_user=master_user, user_code=value
                    )
                elif issubclass(model_class, Counterparty):
                    return Counterparty.objects.get(
                        master_user=master_user, user_code=value
                    )
                elif issubclass(model_class, Responsible):
                    return Responsible.objects.get(
                        master_user=master_user, user_code=value
                    )
                elif issubclass(model_class, Strategy1):
                    return Strategy1.objects.get(
                        master_user=master_user, user_code=value
                    )
                elif issubclass(model_class, Strategy2):
                    return Strategy2.objects.get(
                        master_user=master_user, user_code=value
                    )
                elif issubclass(model_class, Strategy3):
                    return Strategy3.objects.get(
                        master_user=master_user, user_code=value
                    )
                elif issubclass(model_class, PaymentSizeDetail):
                    return PaymentSizeDetail.objects.get(user_code=value)
                elif issubclass(model_class, Portfolio):
                    return Portfolio.objects.get(
                        master_user=master_user, user_code=value
                    )
                elif issubclass(model_class, PricingPolicy):
                    return PricingPolicy.objects.get(
                        master_user=master_user, user_code=value
                    )
                elif issubclass(model_class, Periodicity):
                    return Periodicity.objects.get(user_code=value)
                elif issubclass(model_class, AccrualCalculationModel):
                    return AccrualCalculationModel.objects.get(user_code=value)
                elif issubclass(model_class, EventClass):
                    return EventClass.objects.get(user_code=value)
                elif issubclass(model_class, NotificationClass):
                    return NotificationClass.objects.get(user_code=value)
            except Exception:
                _l.debug(f"Could not find default value relation {value}")
                return None

        def _get_val_by_model_cls_for_complex_transaction_input(
                master_user, obj, model_class
        ):
            try:
                if issubclass(model_class, Account):
                    return Account.objects.get(
                        master_user=master_user, user_code=obj.value_relation
                    )
                elif issubclass(model_class, Currency):
                    return Currency.objects.get(
                        master_user=master_user, user_code=obj.value_relation
                    )
                elif issubclass(model_class, Instrument):
                    return Instrument.objects.get(
                        master_user=master_user, user_code=obj.value_relation
                    )
                elif issubclass(model_class, InstrumentType):
                    return InstrumentType.objects.get(
                        master_user=master_user, user_code=obj.value_relation
                    )
                elif issubclass(model_class, Counterparty):
                    return Counterparty.objects.get(
                        master_user=master_user, user_code=obj.value_relation
                    )
                elif issubclass(model_class, Responsible):
                    return Responsible.objects.get(
                        master_user=master_user, user_code=obj.value_relation
                    )
                elif issubclass(model_class, Strategy1):
                    return Strategy1.objects.get(
                        master_user=master_user, user_code=obj.value_relation
                    )
                elif issubclass(model_class, Strategy2):
                    return Strategy2.objects.get(
                        master_user=master_user, user_code=obj.value_relation
                    )
                elif issubclass(model_class, Strategy3):
                    return Strategy3.objects.get(
                        master_user=master_user, user_code=obj.value_relation
                    )
                elif issubclass(model_class, PaymentSizeDetail):
                    return PaymentSizeDetail.objects.get(user_code=obj.value_relation)
                elif issubclass(model_class, Portfolio):
                    return Portfolio.objects.get(
                        master_user=master_user, user_code=obj.value_relation
                    )
                elif issubclass(model_class, PricingPolicy):
                    return PricingPolicy.objects.get(
                        master_user=master_user, user_code=obj.value_relation
                    )
                elif issubclass(model_class, Periodicity):
                    return Periodicity.objects.get(user_code=obj.value_relation)
                elif issubclass(model_class, AccrualCalculationModel):
                    return AccrualCalculationModel.objects.get(
                        user_code=obj.value_relation
                    )
                elif issubclass(model_class, EventClass):
                    return EventClass.objects.get(user_code=obj.value_relation)
                elif issubclass(model_class, NotificationClass):
                    return NotificationClass.objects.get(user_code=obj.value_relation)
            except Exception:
                _l.error(f"Could not find default value relation {obj.value_relation} ")
                return None

        self.values = {}

        # self.record_execution_progress('values: ', self.values)

        self.values.update(self.default_values)

        # self.record_execution_progress('values with defaults: ', self.values)

        self.values.update(self.context_values)

        # self.record_execution_progress('values with context: ', self.values)

        for i in range(10):
            self.values[f"phantom_instrument_{i}"] = None

        _l.debug(f"Transaction type values {self.values}")

        # if a complex transaction already exists
        if (
                self.complex_transaction
                and self.complex_transaction.id is not None
                and self.complex_transaction.id > 0
        ):
            # load previous values if need
            ci_qs = self.complex_transaction.inputs.all().select_related(
                "transaction_type_input", "transaction_type_input__content_type"
            )
            for ci in ci_qs:
                i = ci.transaction_type_input
                value = None
                if i.value_type in (
                        TransactionTypeInput.STRING,
                        TransactionTypeInput.SELECTOR,
                ):
                    value = ci.value_string
                elif i.value_type == TransactionTypeInput.NUMBER:
                    value = ci.value_float
                elif i.value_type == TransactionTypeInput.DATE:
                    value = ci.value_date
                elif i.value_type == TransactionTypeInput.RELATION:
                    value = _get_val_by_model_cls_for_complex_transaction_input(
                        self.complex_transaction.master_user,
                        ci,
                        i.content_type.model_class(),
                    )
                if value is not None:
                    self.values[i.name] = value

        # _l.debug('self.inputs %s' % self.inputs)

        self.record_execution_progress(
            "==== COMPLEX TRANSACTION VALUES ====", self.values
        )

        for i in self.inputs:
            # input could not be context
            if (i.name not in self.values) and ("context_" not in i.name):
                value = None

                if value is None:
                    if i.value_type == TransactionTypeInput.RELATION:
                        model_class = i.content_type.model_class()

                        if i.value:
                            errors = {}
                            try:
                                value = formula.safe_eval(
                                    i.value,
                                    names=self.values,
                                    now=self._now,
                                    context=self._context,
                                )

                                _l.debug(
                                    f"Set from default. input {i.name} "
                                    f"value {i.value}"
                                )

                            except formula.InvalidExpression as e:
                                self._set_eval_error(errors, i.name, i.value, e)
                                self.value_errors.append(errors)
                                _l.debug(
                                    f"ERROR Set from default. input {i.name} error {e}"
                                )
                                value = None

                        value = _get_val_by_model_cls_for_transaction_type_input(
                            self.complex_transaction.master_user, value, model_class
                        )

                        _l.debug(
                            f"Set from default. Relation input {i.name} "
                            f"value {value}"
                        )

                    else:
                        if i.value:
                            errors = {}
                            try:
                                value = formula.safe_eval(
                                    i.value,
                                    names=self.values,
                                    now=self._now,
                                    context=self._context,
                                )

                                _l.debug(
                                    f"Set from default. input {i.name} value {i.value}"
                                )

                            except formula.InvalidExpression as e:
                                self._set_eval_error(errors, i.name, i.value, e)
                                self.value_errors.append(errors)
                                _l.debug(f"ERROR Set from default. input {i.name}")
                                _l.debug(f"ERROR Set from default. error {e}")
                                value = None

                if value or value == 0:
                    self.values[i.name] = value
                else:
                    _l.debug(
                        f"Value is not set. No Context. No Default. input {i.name} "
                    )

        self.record_execution_progress("==== CALCULATED INPUTS ====")

        for key, value in self.values.items():
            self.record_execution_progress(
                f"Key: {key}. Value: {value}. Type: {type(self.values[key]).__name__}"
            )

    def book_create_instruments(
            self, actions, master_user, instrument_map, pass_download=False
    ):
        # object_permissions = self.transaction_type.object_permissions.select_related('permission').all()
        daily_pricing_model = DailyPricingModel.objects.get(pk=DailyPricingModel.SKIP)

        for order, action in enumerate(actions):
            try:
                action_instrument = action.transactiontypeactioninstrument
            except ObjectDoesNotExist:
                action_instrument = None

            if action_instrument and self.execute_action_condition(action_instrument):
                _l.debug(f"book_create_instruments init. Action {action.order}")

                # Calculate user code value
                errors = {}
                try:
                    _l.debug(f"Calulate user code. Values {self.values}")

                    user_code = formula.safe_eval(
                        action_instrument.user_code,
                        names=self.values,
                        now=self._now,
                        context=self._context,
                    )
                except formula.InvalidExpression as e:
                    self._set_eval_error(
                        errors, "user_code", action_instrument.user_code, e
                    )
                    user_code = None

                exist = False

                if isinstance(user_code, str) and user_code is not None:
                    try:
                        inst = Instrument.objects.get(
                            user_code=user_code, master_user=master_user
                        )
                        exist = True
                    except Instrument.DoesNotExist:
                        exist = False

                _l.debug(
                    f"action_instrument.rebook_reaction {action_instrument.rebook_reaction} "
                )

                if (
                        not exist
                        and isinstance(user_code, str)
                        and action_instrument.rebook_reaction
                        == RebookReactionChoice.TRY_DOWNLOAD_IF_ERROR_CREATE_DEFAULT
                        and pass_download == False
                ):
                    try:
                        from poms.integrations.tasks import download_instrument_cbond

                        _l.debug("Trying to download instrument from provider")
                        task, errors = download_instrument_cbond(
                            user_code, None, None, master_user, self.member
                        )

                        _l.debug(f"Download Instrument from provider. Task {task}")
                        _l.debug(f"Download Instrument from provider. Errors {errors}")

                        instrument = Instrument.objects.get(
                            id=task.result_object["instrument_id"],
                            master_user=master_user,
                        )

                        instrument_map[action.order] = instrument

                        self.values[f"phantom_instrument_{order}"] = instrument

                        _l.debug("Download instrument from provider. Success")

                    except Exception as e:
                        _l.error(f"Download instrument from provider. Error {e}")

                        self.book_create_instruments(
                            actions, master_user, instrument_map, pass_download=True
                        )

                else:
                    if pass_download:
                        _l.debug(
                            f"action_instrument download passed. "
                            f"Trying to create from scratch {user_code}"
                        )
                    _l.debug(
                        f"action_instrument user_code {user_code} instrument "
                        f"{action_instrument} process_mode {self.process_mode} "
                        f"rebook_reaction {action_instrument.rebook_reaction}"
                    )

                    instrument = None
                    instrument_exists = False

                    ecosystem_default = EcosystemDefault.objects.get(
                        master_user=master_user
                    )

                    if user_code:
                        try:
                            instrument = Instrument.objects.get(
                                master_user=master_user,
                                user_code=user_code,
                                is_deleted=False,
                            )
                            instrument_exists = True

                            _l.debug("Instrument found by user code")

                        except Instrument.DoesNotExist:
                            _l.debug(
                                f"Instrument DoesNotExist exception, rebook_reaction "
                                f"{action_instrument.rebook_reaction} "
                                f"RebookReactionChoice.FIND_OR_CREATE "
                                f"{RebookReactionChoice.FIND_OR_CREATE} "
                                f"self.process_mode {self.process_mode} "
                                f"self.MODE_REBOOK {self.MODE_REBOOK}"
                            )

                            if (
                                    action_instrument.rebook_reaction
                                    == RebookReactionChoice.FIND_OR_CREATE
                                    and self.process_mode == self.MODE_REBOOK
                            ):
                                instrument = ecosystem_default.instrument
                                instrument_exists = True

                                _l.debug(
                                    f"Rebook: Instrument is not exists, return Default"
                                    f" {instrument.user_code}"
                                )

                    if instrument is None:
                        instrument = Instrument.objects.create(
                            master_user=master_user,
                            user_code=user_code,
                            name=user_code,
                            owner=self.member,
                            identifier={},
                            instrument_type=ecosystem_default.instrument_type,
                            accrued_currency=ecosystem_default.currency,
                            pricing_currency=ecosystem_default.currency,
                            co_directional_exposure_currency=ecosystem_default.currency,
                            counter_directional_exposure_currency=ecosystem_default.currency,
                        )
                        _l.debug("Instrument is not exists. Create new.")

                    _l.debug(f"instrument.user_code {instrument.user_code} ")

                    object_data = {"user_code": instrument.user_code, "identifier": {}}

                    if instrument.user_code not in [
                        "-",
                        ecosystem_default.instrument.user_code,
                    ]:
                        self._set_rel(
                            errors=errors,
                            target=instrument,
                            target_attr_name="instrument_type",
                            model=InstrumentType,
                            source=action_instrument,
                            source_attr_name="instrument_type",
                            values=self.values,
                            default_value=ecosystem_default.instrument_type,
                        )

                        object_data["instrument_type"] = instrument.instrument_type.id

                        # _l.debug('set rel instrument.instrument_type %s' % instrument.instrument_type.id)

                        from poms.csv_import.handlers import (
                            set_defaults_from_instrument_type,
                        )

                        set_defaults_from_instrument_type(
                            object_data,
                            instrument.instrument_type,
                            ecosystem_default,
                        )

                        self._set_val(
                            errors=errors,
                            values=self.values,
                            default_value="",
                            target=instrument,
                            target_attr_name="name",
                            source=action_instrument,
                            source_attr_name="name",
                            object_data=object_data,
                        )
                        self._set_val(
                            errors=errors,
                            values=self.values,
                            default_value="",
                            target=instrument,
                            target_attr_name="short_name",
                            source=action_instrument,
                            source_attr_name="short_name",
                            object_data=object_data,
                        )
                        self._set_val(
                            errors=errors,
                            values=self.values,
                            default_value="",
                            target=instrument,
                            target_attr_name="public_name",
                            source=action_instrument,
                            source_attr_name="public_name",
                            object_data=object_data,
                        )

                        if getattr(action_instrument, "notes"):
                            self._set_val(
                                errors=errors,
                                values=self.values,
                                default_value="",
                                target=instrument,
                                target_attr_name="notes",
                                source=action_instrument,
                                source_attr_name="notes",
                                object_data=object_data,
                            )

                        self._set_rel(
                            errors=errors,
                            values=self.values,
                            default_value=ecosystem_default.currency,
                            model=Currency,
                            target=instrument,
                            target_attr_name="pricing_currency",
                            source=action_instrument,
                            source_attr_name="pricing_currency",
                            object_data=object_data,
                        )

                        self._set_rel(
                            errors=errors,
                            values=self.values,
                            default_value=ecosystem_default.currency,
                            model=Currency,
                            target=instrument,
                            target_attr_name="counter_directional_exposure_currency",
                            source=action_instrument,
                            source_attr_name="pricing_currency",
                            object_data=object_data,
                        )

                        self._set_rel(
                            errors=errors,
                            values=self.values,
                            default_value=ecosystem_default.currency,
                            model=Currency,
                            target=instrument,
                            target_attr_name="co_directional_exposure_currency",
                            source=action_instrument,
                            source_attr_name="pricing_currency",
                            object_data=object_data,
                        )

                        self._set_val(
                            errors=errors,
                            values=self.values,
                            default_value=0.0,
                            target=instrument,
                            target_attr_name="price_multiplier",
                            source=action_instrument,
                            source_attr_name="price_multiplier",
                            object_data=object_data,
                        )
                        self._set_rel(
                            errors=errors,
                            values=self.values,
                            default_value=ecosystem_default.currency,
                            model=Currency,
                            target=instrument,
                            target_attr_name="accrued_currency",
                            source=action_instrument,
                            source_attr_name="accrued_currency",
                            object_data=object_data,
                        )
                        self._set_val(
                            errors=errors,
                            values=self.values,
                            default_value=0.0,
                            target=instrument,
                            target_attr_name="accrued_multiplier",
                            source=action_instrument,
                            source_attr_name="accrued_multiplier",
                            object_data=object_data,
                        )
                        self._set_rel(
                            errors=errors,
                            values=self.values,
                            default_value=None,
                            target=instrument,
                            target_attr_name="payment_size_detail",
                            model=PaymentSizeDetail,
                            source=action_instrument,
                            source_attr_name="payment_size_detail",
                            object_data=object_data,
                        )
                        self._set_val(
                            errors=errors,
                            values=self.values,
                            default_value=0.0,
                            target=instrument,
                            target_attr_name="default_price",
                            source=action_instrument,
                            source_attr_name="default_price",
                            object_data=object_data,
                        )
                        self._set_val(
                            errors=errors,
                            values=self.values,
                            default_value=0.0,
                            target=instrument,
                            target_attr_name="default_accrued",
                            source=action_instrument,
                            source_attr_name="default_accrued",
                            object_data=object_data,
                        )
                        self._set_val(
                            errors=errors,
                            values=self.values,
                            default_value="",
                            target=instrument,
                            target_attr_name="user_text_1",
                            source=action_instrument,
                            source_attr_name="user_text_1",
                            object_data=object_data,
                        )
                        self._set_val(
                            errors=errors,
                            values=self.values,
                            default_value="",
                            target=instrument,
                            target_attr_name="user_text_2",
                            source=action_instrument,
                            source_attr_name="user_text_2",
                            object_data=object_data,
                        )
                        self._set_val(
                            errors=errors,
                            values=self.values,
                            default_value="",
                            target=instrument,
                            target_attr_name="user_text_3",
                            source=action_instrument,
                            source_attr_name="user_text_3",
                            object_data=object_data,
                        )
                        self._set_val(
                            errors=errors,
                            values=self.values,
                            default_value="",
                            target=instrument,
                            target_attr_name="reference_for_pricing",
                            source=action_instrument,
                            source_attr_name="reference_for_pricing",
                            object_data=object_data,
                        )
                        self._set_val(
                            errors=errors,
                            values=self.values,
                            default_value=date.max,
                            target=instrument,
                            target_attr_name="maturity_date",
                            source=action_instrument,
                            source_attr_name="maturity_date",
                            validator=formula.validate_date,
                            object_data=object_data,
                        )
                        self._set_val(
                            errors=errors,
                            values=self.values,
                            default_value=0.0,
                            target=instrument,
                            target_attr_name="maturity_price",
                            source=action_instrument,
                            source_attr_name="maturity_price",
                            object_data=object_data,
                        )

                    try:
                        rebook_reaction = action_instrument.rebook_reaction

                        _l.debug(f"rebook_reaction {rebook_reaction}")
                        _l.debug(f"instrument_exists {instrument_exists}")
                        _l.debug(f"object_data {object_data}")

                        from poms.instruments.serializers import InstrumentSerializer

                        serializer = InstrumentSerializer(
                            data=object_data,
                            instance=instrument,
                            context=self._context,
                        )

                        is_valid = serializer.is_valid(raise_exception=True)

                        if is_valid:
                            if self.process_mode == self.MODE_REBOOK:
                                if rebook_reaction == RebookReactionChoice.OVERWRITE:
                                    _l.debug("Rebook  OVERWRITE")

                                    instrument = serializer.save()

                                if (
                                        rebook_reaction == RebookReactionChoice.CREATE
                                        and not instrument_exists
                                ):
                                    _l.debug("Rebook CREATE")

                                    instrument = serializer.save()

                                if (
                                        rebook_reaction
                                        == RebookReactionChoice.FIND_OR_CREATE
                                        and not instrument_exists
                                ):
                                    _l.debug("Rebook FIND_OR_CREATE")

                                    instrument = serializer.save()

                            else:
                                if rebook_reaction == RebookReactionChoice.OVERWRITE:
                                    _l.debug("Book  OVERWRITE")

                                    instrument = serializer.save()

                                if (
                                        rebook_reaction == RebookReactionChoice.CREATE
                                        and not instrument_exists
                                ):
                                    _l.debug("Book  CREATE")

                                    instrument = serializer.save()

                                if (
                                        rebook_reaction
                                        == RebookReactionChoice.FIND_OR_CREATE
                                        and not instrument_exists
                                ):
                                    _l.debug("Book  FIND_OR_CREATE")

                                    instrument = serializer.save()

                            if (
                                    rebook_reaction
                                    == RebookReactionChoice.TRY_DOWNLOAD_IF_ERROR_CREATE_DEFAULT
                                    and not instrument_exists
                            ):
                                _l.debug("Book  TRY_DOWNLOAD_IF_ERROR_CREATE_DEFAULT")

                                instrument = serializer.save()

                        if rebook_reaction is None:
                            instrument = serializer.save()

                    except (IntegrityError, Exception) as e:
                        _l.error(f"Instrument save error {e}")

                        self._add_err_msg(
                            errors,
                            "non_field_errors",
                            gettext_lazy(
                                "Invalid instrument action fields (please, use type convertion)."
                            ),
                        )
                    except DatabaseError:
                        self._add_err_msg(
                            errors,
                            "non_field_errors",
                            gettext_lazy("General DB error."),
                        )
                    else:
                        instrument_map[action.order] = instrument

                        self.values[f"phantom_instrument_{action.order}"] = instrument

                    finally:
                        _l.debug(f"Instrument action errors {errors} ")

                        if bool(errors):
                            self.instruments_errors.append(errors)

        return instrument_map

    def book_create_factor_schedules(self, actions, instrument_map):
        for action in actions:
            try:
                action_instrument_factor_schedule = (
                    action.transactiontypeactioninstrumentfactorschedule
                )
            except ObjectDoesNotExist:
                action_instrument_factor_schedule = None

            if action_instrument_factor_schedule and self.execute_action_condition(
                    action_instrument_factor_schedule
            ):
                _l.debug(
                    "process factor schedule: %s", action_instrument_factor_schedule
                )

                errors = {}

                factor = InstrumentFactorSchedule()

                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=None,
                    target=factor,
                    target_attr_name="instrument",
                    model=Instrument,
                    source=action_instrument_factor_schedule,
                    source_attr_name="instrument",
                )
                if action_instrument_factor_schedule.instrument_phantom is not None:
                    factor.instrument = instrument_map[
                        action_instrument_factor_schedule.instrument_phantom_id
                    ]

                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value=self._now,
                    target=factor,
                    target_attr_name="effective_date",
                    validator=formula.validate_date,
                    source=action_instrument_factor_schedule,
                    source_attr_name="effective_date",
                )

                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value=0.0,
                    target=factor,
                    target_attr_name="factor_value",
                    source=action_instrument_factor_schedule,
                    source_attr_name="factor_value",
                )

                try:
                    rebook_reaction = action_instrument_factor_schedule.rebook_reaction

                    if rebook_reaction == RebookReactionChoice.CREATE:
                        factor.save()

                    if self.process_mode == self.MODE_REBOOK:
                        if rebook_reaction == RebookReactionChoice.CREATE_IF_NOT_EXIST:
                            _l.debug("Skip")

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE:
                            InstrumentFactorSchedule.objects.filter(
                                instrument=factor.instrument
                            ).delete()

                            factor.save()

                        if (
                                rebook_reaction
                                == RebookReactionChoice.CLEAR_AND_WRITE_OR_SKIP
                        ):
                            _l.debug("Skip")

                        if rebook_reaction == RebookReactionChoice.CLEAR:
                            InstrumentFactorSchedule.objects.filter(
                                instrument=factor.instrument
                            ).delete()

                    else:
                        if rebook_reaction == RebookReactionChoice.CREATE_IF_NOT_EXIST:
                            factor.save()

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE:
                            InstrumentFactorSchedule.objects.filter(
                                instrument=factor.instrument
                            ).delete()

                            factor.save()

                        if (
                                rebook_reaction
                                == RebookReactionChoice.CLEAR_AND_WRITE_OR_SKIP
                        ):
                            InstrumentFactorSchedule.objects.filter(
                                instrument=factor.instrument
                            ).delete()

                            factor.save()

                        if rebook_reaction == RebookReactionChoice.CLEAR:
                            InstrumentFactorSchedule.objects.filter(
                                instrument=factor.instrument
                            ).delete()

                        if rebook_reaction is None:
                            factor.save()

                except (ValueError, TypeError, IntegrityError):
                    self._add_err_msg(
                        errors,
                        "non_field_errors",
                        gettext_lazy(
                            "Invalid instrument factor schedule action fields (please, use type convertion)."
                        ),
                    )
                except DatabaseError:
                    self._add_err_msg(
                        errors, "non_field_errors", gettext_lazy("General DB error.")
                    )
                finally:
                    if bool(errors):
                        _l.debug(errors)
                        # self.instruments_errors.append(errors)

    def book_create_manual_pricing_formulas(self, actions, instrument_map):
        for action in actions:
            try:
                action_instrument_manual_pricing_formula = (
                    action.transactiontypeactioninstrumentmanualpricingformula
                )
            except ObjectDoesNotExist:
                action_instrument_manual_pricing_formula = None

            if (
                    action_instrument_manual_pricing_formula
                    and self.execute_action_condition(
                action_instrument_manual_pricing_formula
            )
            ):
                _l.debug(
                    "process manual pricing formula: %s",
                    action_instrument_manual_pricing_formula,
                )

                errors = {}

                manual_pricing_formula = ManualPricingFormula()

                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=None,
                    model=Instrument,
                    target=manual_pricing_formula,
                    target_attr_name="instrument",
                    source=action_instrument_manual_pricing_formula,
                    source_attr_name="instrument",
                )
                if (
                        action_instrument_manual_pricing_formula.instrument_phantom
                        is not None
                ):
                    manual_pricing_formula.instrument = instrument_map[
                        action_instrument_manual_pricing_formula.instrument_phantom_id
                    ]

                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=None,
                    model=PricingPolicy,
                    target=manual_pricing_formula,
                    target_attr_name="pricing_policy",
                    source=action_instrument_manual_pricing_formula,
                    source_attr_name="pricing_policy",
                )

                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value="",
                    target=manual_pricing_formula,
                    target_attr_name="expr",
                    source=action_instrument_manual_pricing_formula,
                    source_attr_name="expr",
                )

                if getattr(action_instrument_manual_pricing_formula, "notes"):
                    self._set_val(
                        errors=errors,
                        values=self.values,
                        default_value="",
                        target=manual_pricing_formula,
                        target_attr_name="notes",
                        source=action_instrument_manual_pricing_formula,
                        source_attr_name="notes",
                    )

                try:
                    rebook_reaction = (
                        action_instrument_manual_pricing_formula.rebook_reaction
                    )

                    if rebook_reaction == RebookReactionChoice.CREATE:
                        manual_pricing_formula.save()

                    if self.process_mode == self.MODE_REBOOK:
                        if rebook_reaction == RebookReactionChoice.CREATE_IF_NOT_EXIST:
                            _l.debug("Skip")

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE:
                            ManualPricingFormula.objects.filter(
                                instrument=manual_pricing_formula.instrument
                            ).delete()

                            manual_pricing_formula.save()

                        if (
                                rebook_reaction
                                == RebookReactionChoice.CLEAR_AND_WRITE_OR_SKIP
                        ):
                            _l.debug("Skip")

                    else:
                        if rebook_reaction == RebookReactionChoice.CREATE_IF_NOT_EXIST:
                            manual_pricing_formula.save()

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE:
                            ManualPricingFormula.objects.filter(
                                instrument=manual_pricing_formula.instrument
                            ).delete()

                            manual_pricing_formula.save()

                        if (
                                rebook_reaction
                                == RebookReactionChoice.CLEAR_AND_WRITE_OR_SKIP
                        ):
                            ManualPricingFormula.objects.filter(
                                instrument=manual_pricing_formula.instrument
                            ).delete()

                            manual_pricing_formula.save()

                    if rebook_reaction == RebookReactionChoice.CLEAR:
                        ManualPricingFormula.objects.filter(
                            instrument=manual_pricing_formula.instrument
                        ).delete()

                    if rebook_reaction is None:
                        manual_pricing_formula.save()

                except (ValueError, TypeError, IntegrityError):
                    self._add_err_msg(
                        errors,
                        "non_field_errors",
                        gettext_lazy(
                            "Invalid instrument manual pricing formula action fields (please, use type convertion)."
                        ),
                    )
                except DatabaseError:
                    self._add_err_msg(
                        errors, "non_field_errors", gettext_lazy("General DB error.")
                    )
                finally:
                    if bool(errors):
                        _l.debug(errors)

    def book_create_accrual_calculation_schedules(self, actions, instrument_map):
        for action in actions:
            try:
                action_instrument_accrual_calculation_schedule = (
                    action.transactiontypeactioninstrumentaccrualcalculationschedules
                )
            except ObjectDoesNotExist:
                action_instrument_accrual_calculation_schedule = None

            if (
                    action_instrument_accrual_calculation_schedule
                    and self.execute_action_condition(
                action_instrument_accrual_calculation_schedule
            )
            ):
                _l.debug(
                    "process accrual calculation schedule: %s",
                    action_instrument_accrual_calculation_schedule,
                )

                errors = {}

                accrual_calculation_schedule = AccrualCalculationSchedule()

                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=None,
                    model=Instrument,
                    target=accrual_calculation_schedule,
                    target_attr_name="instrument",
                    source=action_instrument_accrual_calculation_schedule,
                    source_attr_name="instrument",
                )
                if (
                        action_instrument_accrual_calculation_schedule.instrument_phantom
                        is not None
                ):
                    accrual_calculation_schedule.instrument = instrument_map[
                        action_instrument_accrual_calculation_schedule.instrument_phantom_id
                    ]

                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=None,
                    model=AccrualCalculationModel,
                    target=accrual_calculation_schedule,
                    target_attr_name="accrual_calculation_model",
                    source=action_instrument_accrual_calculation_schedule,
                    source_attr_name="accrual_calculation_model",
                )

                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=None,
                    model=Periodicity,
                    target=accrual_calculation_schedule,
                    target_attr_name="periodicity",
                    source=action_instrument_accrual_calculation_schedule,
                    source_attr_name="periodicity",
                )

                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value="",
                    validator=formula.validate_date,
                    target=accrual_calculation_schedule,
                    target_attr_name="accrual_start_date",
                    source=action_instrument_accrual_calculation_schedule,
                    source_attr_name="accrual_start_date",
                )

                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value="",
                    validator=formula.validate_date,
                    target=accrual_calculation_schedule,
                    target_attr_name="first_payment_date",
                    source=action_instrument_accrual_calculation_schedule,
                    source_attr_name="first_payment_date",
                )

                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value="",
                    target=accrual_calculation_schedule,
                    target_attr_name="accrual_size",
                    source=action_instrument_accrual_calculation_schedule,
                    source_attr_name="accrual_size",
                )

                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value="",
                    target=accrual_calculation_schedule,
                    target_attr_name="periodicity_n",
                    source=action_instrument_accrual_calculation_schedule,
                    source_attr_name="periodicity_n",
                )

                if getattr(action_instrument_accrual_calculation_schedule, "notes"):
                    self._set_val(
                        errors=errors,
                        values=self.values,
                        default_value="",
                        target=accrual_calculation_schedule,
                        target_attr_name="notes",
                        source=action_instrument_accrual_calculation_schedule,
                        source_attr_name="notes",
                    )

                try:
                    rebook_reaction = (
                        action_instrument_accrual_calculation_schedule.rebook_reaction
                    )

                    if rebook_reaction == RebookReactionChoice.CREATE:
                        accrual_calculation_schedule.save()

                    if self.process_mode == self.MODE_REBOOK:
                        if rebook_reaction == RebookReactionChoice.CREATE_IF_NOT_EXIST:
                            _l.debug("Skip")

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE:
                            AccrualCalculationSchedule.objects.filter(
                                instrument=accrual_calculation_schedule.instrument
                            ).delete()

                            accrual_calculation_schedule.save()

                        if (
                                rebook_reaction
                                == RebookReactionChoice.CLEAR_AND_WRITE_OR_SKIP
                        ):
                            _l.debug("Skip")

                        if rebook_reaction == RebookReactionChoice.CLEAR:
                            AccrualCalculationSchedule.objects.filter(
                                instrument=accrual_calculation_schedule.instrument
                            ).delete()

                    else:
                        if rebook_reaction == RebookReactionChoice.CREATE_IF_NOT_EXIST:
                            accrual_calculation_schedule.save()

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE:
                            AccrualCalculationSchedule.objects.filter(
                                instrument=accrual_calculation_schedule.instrument
                            ).delete()

                            accrual_calculation_schedule.save()

                        if (
                                rebook_reaction
                                == RebookReactionChoice.CLEAR_AND_WRITE_OR_SKIP
                        ):
                            AccrualCalculationSchedule.objects.filter(
                                instrument=accrual_calculation_schedule.instrument
                            ).delete()

                            accrual_calculation_schedule.save()

                        if rebook_reaction == RebookReactionChoice.CLEAR:
                            AccrualCalculationSchedule.objects.filter(
                                instrument=accrual_calculation_schedule.instrument
                            ).delete()

                        if rebook_reaction is None:
                            accrual_calculation_schedule.save()

                except (ValueError, TypeError, IntegrityError):
                    self._add_err_msg(
                        errors,
                        "non_field_errors",
                        gettext_lazy(
                            "Invalid instrument accrual calculation schedule action fields (please, use type convertion)."
                        ),
                    )
                except DatabaseError:
                    self._add_err_msg(
                        errors, "non_field_errors", gettext_lazy("General DB error.")
                    )
                finally:
                    if bool(errors):
                        _l.debug(errors)

    def book_create_event_schedules(self, actions, instrument_map, event_schedules_map):
        for action in actions:
            try:
                action_instrument_event_schedule = (
                    action.transactiontypeactioninstrumenteventschedule
                )
            except ObjectDoesNotExist:
                action_instrument_event_schedule = None

            if action_instrument_event_schedule and self.execute_action_condition(
                    action_instrument_event_schedule
            ):
                _l.debug("process event schedule: %s", action_instrument_event_schedule)
                _l.debug("instrument_map: %s", instrument_map)

                errors = {}

                event_schedule = EventSchedule()

                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=None,
                    model=Instrument,
                    target=event_schedule,
                    target_attr_name="instrument",
                    source=action_instrument_event_schedule,
                    source_attr_name="instrument",
                )

                if action_instrument_event_schedule.instrument_phantom is not None:
                    event_schedule.instrument = instrument_map[
                        action_instrument_event_schedule.instrument_phantom_id
                    ]

                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=None,
                    model=NotificationClass,
                    target=event_schedule,
                    target_attr_name="notification_class",
                    source=action_instrument_event_schedule,
                    source_attr_name="notification_class",
                )

                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=None,
                    model=Periodicity,
                    target=event_schedule,
                    target_attr_name="periodicity",
                    source=action_instrument_event_schedule,
                    source_attr_name="periodicity",
                )

                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=None,
                    model=EventClass,
                    target=event_schedule,
                    target_attr_name="event_class",
                    source=action_instrument_event_schedule,
                    source_attr_name="event_class",
                )

                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value="",
                    validator=formula.validate_date,
                    target=event_schedule,
                    target_attr_name="effective_date",
                    source=action_instrument_event_schedule,
                    source_attr_name="effective_date",
                )

                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value="",
                    validator=formula.validate_date,
                    target=event_schedule,
                    target_attr_name="final_date",
                    source=action_instrument_event_schedule,
                    source_attr_name="final_date",
                )

                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value="",
                    target=event_schedule,
                    target_attr_name="notify_in_n_days",
                    source=action_instrument_event_schedule,
                    source_attr_name="notify_in_n_days",
                )

                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value=False,
                    validator=formula.validate_bool,
                    target=event_schedule,
                    target_attr_name="is_auto_generated",
                    source=action_instrument_event_schedule,
                    source_attr_name="is_auto_generated",
                )

                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value="",
                    target=event_schedule,
                    target_attr_name="periodicity_n",
                    source=action_instrument_event_schedule,
                    source_attr_name="periodicity_n",
                )

                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value="",
                    target=event_schedule,
                    target_attr_name="name",
                    source=action_instrument_event_schedule,
                    source_attr_name="name",
                )

                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value="",
                    target=event_schedule,
                    target_attr_name="description",
                    source=action_instrument_event_schedule,
                    source_attr_name="description",
                )

                try:
                    rebook_reaction = action_instrument_event_schedule.rebook_reaction

                    if rebook_reaction == RebookReactionChoice.CREATE:
                        event_schedule.save()

                    if self.process_mode == self.MODE_REBOOK:
                        if rebook_reaction == RebookReactionChoice.CREATE_IF_NOT_EXIST:
                            _l.debug("Skip")

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE:
                            EventSchedule.objects.filter(
                                instrument=event_schedule.instrument
                            ).delete()

                            event_schedule.save()

                        if (
                                rebook_reaction
                                == RebookReactionChoice.CLEAR_AND_WRITE_OR_SKIP
                        ):
                            _l.debug("Skip")

                        if rebook_reaction == RebookReactionChoice.CLEAR:
                            EventSchedule.objects.filter(
                                instrument=event_schedule.instrument
                            ).delete()

                    else:
                        if rebook_reaction == RebookReactionChoice.CREATE_IF_NOT_EXIST:
                            event_schedule.save()

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE:
                            EventSchedule.objects.filter(
                                instrument=event_schedule.instrument
                            ).delete()

                            event_schedule.save()

                        if (
                                rebook_reaction
                                == RebookReactionChoice.CLEAR_AND_WRITE_OR_SKIP
                        ):
                            EventSchedule.objects.filter(
                                instrument=event_schedule.instrument
                            ).delete()

                            event_schedule.save()

                        if rebook_reaction == RebookReactionChoice.CLEAR:
                            EventSchedule.objects.filter(
                                instrument=event_schedule.instrument
                            ).delete()

                        if rebook_reaction is None:
                            event_schedule.save()

                except (ValueError, TypeError, IntegrityError):
                    self._add_err_msg(
                        errors,
                        "non_field_errors",
                        gettext_lazy(
                            "Invalid instrument event schedule action fields (please, use type convertion)."
                        ),
                    )
                except DatabaseError:
                    self._add_err_msg(
                        errors, "non_field_errors", gettext_lazy("General DB error.")
                    )
                else:
                    event_schedules_map[action.id] = event_schedule
                finally:
                    if bool(errors):
                        _l.debug(errors)
                        # self.instruments_errors.append(errors)

        return event_schedules_map

    def book_create_event_actions(self, actions, instrument_map, event_schedules_map):
        for action in actions:
            try:
                action_instrument_event_schedule_action = (
                    action.transactiontypeactioninstrumenteventscheduleaction
                )
            except ObjectDoesNotExist:
                action_instrument_event_schedule_action = None

            if (
                    action_instrument_event_schedule_action
                    and self.execute_action_condition(
                action_instrument_event_schedule_action
            )
            ):
                errors = {}

                event_schedule_action = EventScheduleAction()

                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=None,
                    target=event_schedule_action,
                    target_attr_name="event_schedule",
                    model=None,
                    source=action_instrument_event_schedule_action,
                    source_attr_name="event_schedule",
                )

                if (
                        action_instrument_event_schedule_action.event_schedule_phantom
                        is not None
                ):
                    event_schedule = event_schedules_map[
                        action_instrument_event_schedule_action.event_schedule_phantom_id
                    ]

                    _l.debug(
                        f"book_create_event_actions: event_schedule {event_schedule}"
                    )

                    event_schedule_action.event_schedule = event_schedule

                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=None,
                    target=event_schedule_action,
                    target_attr_name="transaction_type",
                    model=None,
                    source=event_schedule_action.event_schedule.instrument.instrument_type,
                    source_attr_name=action_instrument_event_schedule_action.transaction_type_from_instrument_type,
                )

                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value=False,
                    validator=formula.validate_bool,
                    target=event_schedule_action,
                    target_attr_name="is_sent_to_pending",
                    source=action_instrument_event_schedule_action,
                    source_attr_name="is_sent_to_pending",
                )

                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value=False,
                    validator=formula.validate_bool,
                    target=event_schedule_action,
                    target_attr_name="is_book_automatic",
                    source=action_instrument_event_schedule_action,
                    source_attr_name="is_book_automatic",
                )

                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value=0,
                    target=event_schedule_action,
                    target_attr_name="button_position",
                    source=action_instrument_event_schedule_action,
                    source_attr_name="button_position",
                )

                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value="",
                    target=event_schedule_action,
                    target_attr_name="text",
                    source=action_instrument_event_schedule_action,
                    source_attr_name="text",
                )

                try:
                    rebook_reaction = (
                        action_instrument_event_schedule_action.rebook_reaction
                    )

                    if rebook_reaction == RebookReactionChoice.CREATE:
                        event_schedule_action.save()

                    if self.process_mode == self.MODE_REBOOK:
                        if rebook_reaction == RebookReactionChoice.CREATE_IF_NOT_EXIST:
                            _l.debug("Skip")

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE:
                            EventScheduleAction.objects.filter(
                                event_schedule=event_schedule_action.event_schedule
                            ).delete()

                            event_schedule_action.save()

                        if (
                                rebook_reaction
                                == RebookReactionChoice.CLEAR_AND_WRITE_OR_SKIP
                        ):
                            _l.debug("Skip")

                        if rebook_reaction == RebookReactionChoice.CLEAR:
                            EventScheduleAction.objects.filter(
                                event_schedule=event_schedule_action.event_schedule
                            ).delete()

                    else:
                        if rebook_reaction == RebookReactionChoice.CREATE_IF_NOT_EXIST:
                            event_schedule_action.save()

                        if rebook_reaction == RebookReactionChoice.CLEAR_AND_WRITE:
                            EventScheduleAction.objects.filter(
                                event_schedule=event_schedule_action.event_schedule
                            ).delete()

                            event_schedule_action.save()

                        if (
                                rebook_reaction
                                == RebookReactionChoice.CLEAR_AND_WRITE_OR_SKIP
                        ):
                            EventScheduleAction.objects.filter(
                                event_schedule=event_schedule_action.event_schedule
                            ).delete()

                            event_schedule_action.save()

                        if rebook_reaction == RebookReactionChoice.CLEAR:
                            EventScheduleAction.objects.filter(
                                event_schedule=event_schedule_action.event_schedule
                            ).delete()

                        if rebook_reaction is None:
                            event_schedule_action.save()

                except (ValueError, TypeError, IntegrityError) as e:
                    self._add_err_msg(
                        errors,
                        "non_field_errors",
                        gettext_lazy(
                            "Invalid instrument event schedule action action fields (please, use type convertion)."
                        ),
                    )
                except DatabaseError:
                    self._add_err_msg(
                        errors, "non_field_errors", gettext_lazy("General DB error.")
                    )
                finally:
                    if bool(errors):
                        _l.debug(errors)

    def book_execute_commands(self, actions):
        for action in actions:
            try:
                execute_command = action.transactiontypeactionexecutecommand
            except ObjectDoesNotExist:
                execute_command = None

            if execute_command and self.execute_action_condition(execute_command):
                errors = {}

                names = {
                    key: formula.value_prepare(value)
                    for key, value in self.values.items()
                }
                # names = self.to_dict(names)

                try:
                    result = formula.safe_eval(
                        execute_command.expr, names=names, context=self._context
                    )

                    # _l.debug('result %s', result)

                except (
                        ValueError,
                        TypeError,
                        IntegrityError,
                        formula.InvalidExpression,
                ) as e:
                    # _l.debug("Execute command execute_command.expr %s " % execute_command.expr)
                    # _l.debug("Execute command execute_command.names %s " % names)
                    # _l.debug("Execute command error %s " % e)

                    self._add_err_msg(
                        errors,
                        "non_field_errors",
                        gettext_lazy("Invalid execute command (Invalid Expression)"),
                    )
                except DatabaseError:
                    self._add_err_msg(
                        errors, "non_field_errors", gettext_lazy("General DB error.")
                    )
                finally:
                    if bool(errors):
                        _l.debug(errors)
                        # self.instruments_errors.append(errors)

    def transaction_access_check(
            self, transaction, group, account_permissions, portfolio_permissions
    ):
        account_result = any(
            perm.group.id == group.id
            and (
                    (
                            transaction.account_position
                            and transaction.account_position.id == perm.object_id
                    )
                    and (
                            transaction.account_cash
                            and transaction.account_cash.id == perm.object_id
                    )
            )
            for perm in account_permissions
        )
        portfolio_result = any(
            perm.group.id == group.id
            and (transaction.portfolio and transaction.portfolio.id == perm.object_id)
            for perm in portfolio_permissions
        )
        return account_result and portfolio_result

    def book_create_transactions(self, actions, master_user, instrument_map):
        for action in actions:
            try:
                action_transaction = action.transactiontypeactiontransaction
            except ObjectDoesNotExist:
                action_transaction = None

            if action_transaction and self.execute_action_condition(action_transaction):
                if action_transaction.instrument_phantom is not None:
                    _l.debug(
                        "process transaction instrument_phantom.order: %s",
                        action_transaction.instrument_phantom.order,
                    )
                errors = {}
                transaction = Transaction(master_user=master_user)
                transaction.complex_transaction = self.complex_transaction
                transaction.complex_transaction_order = self.next_transaction_order()
                transaction.transaction_class = action_transaction.transaction_class

                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=None,
                    target=transaction,
                    target_attr_name="instrument",
                    model=Instrument,
                    source=action_transaction,
                    source_attr_name="instrument",
                )

                if action_transaction.instrument_phantom is not None:
                    transaction.instrument = instrument_map[
                        action_transaction.instrument_phantom.order
                    ]

                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=self.ecosystem_default.currency,
                    model=Currency,
                    target=transaction,
                    target_attr_name="transaction_currency",
                    source=action_transaction,
                    source_attr_name="transaction_currency",
                )
                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value=0.0,
                    target=transaction,
                    target_attr_name="position_size_with_sign",
                    source=action_transaction,
                    source_attr_name="position_size_with_sign",
                )

                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=self.ecosystem_default.currency,
                    model=Currency,
                    target=transaction,
                    target_attr_name="settlement_currency",
                    source=action_transaction,
                    source_attr_name="settlement_currency",
                )
                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value=0.0,
                    target=transaction,
                    target_attr_name="cash_consideration",
                    source=action_transaction,
                    source_attr_name="cash_consideration",
                )
                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value=0.0,
                    target=transaction,
                    target_attr_name="principal_with_sign",
                    source=action_transaction,
                    source_attr_name="principal_with_sign",
                )
                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value=0.0,
                    target=transaction,
                    target_attr_name="carry_with_sign",
                    source=action_transaction,
                    source_attr_name="carry_with_sign",
                )
                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value=0.0,
                    target=transaction,
                    target_attr_name="overheads_with_sign",
                    source=action_transaction,
                    source_attr_name="overheads_with_sign",
                )

                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=self.ecosystem_default.portfolio,
                    model=Portfolio,
                    target=transaction,
                    target_attr_name="portfolio",
                    source=action_transaction,
                    source_attr_name="portfolio",
                )
                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=self.ecosystem_default.account,
                    model=Account,
                    target=transaction,
                    target_attr_name="account_position",
                    source=action_transaction,
                    source_attr_name="account_position",
                )
                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=self.ecosystem_default.account,
                    model=Account,
                    target=transaction,
                    target_attr_name="account_cash",
                    source=action_transaction,
                    source_attr_name="account_cash",
                )
                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=self.ecosystem_default.account,
                    model=Account,
                    target=transaction,
                    target_attr_name="account_interim",
                    source=action_transaction,
                    source_attr_name="account_interim",
                )

                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value=self._now,
                    target=transaction,
                    target_attr_name="accounting_date",
                    source=action_transaction,
                    source_attr_name="accounting_date",
                    validator=formula.validate_date,
                )
                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value=self._now,
                    target=transaction,
                    target_attr_name="cash_date",
                    source=action_transaction,
                    source_attr_name="cash_date",
                    validator=formula.validate_date,
                )

                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=self.ecosystem_default.strategy1,
                    model=Strategy1,
                    target=transaction,
                    target_attr_name="strategy1_position",
                    source=action_transaction,
                    source_attr_name="strategy1_position",
                )
                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=self.ecosystem_default.strategy1,
                    model=Strategy1,
                    target=transaction,
                    target_attr_name="strategy1_cash",
                    source=action_transaction,
                    source_attr_name="strategy1_cash",
                )
                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=self.ecosystem_default.strategy2,
                    model=Strategy2,
                    target=transaction,
                    target_attr_name="strategy2_position",
                    source=action_transaction,
                    source_attr_name="strategy2_position",
                )
                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=self.ecosystem_default.strategy2,
                    model=Strategy2,
                    target=transaction,
                    target_attr_name="strategy2_cash",
                    source=action_transaction,
                    source_attr_name="strategy2_cash",
                )
                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=self.ecosystem_default.strategy3,
                    model=Strategy3,
                    target=transaction,
                    target_attr_name="strategy3_position",
                    source=action_transaction,
                    source_attr_name="strategy3_position",
                )
                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=self.ecosystem_default.strategy3,
                    model=Strategy3,
                    target=transaction,
                    target_attr_name="strategy3_cash",
                    source=action_transaction,
                    source_attr_name="strategy3_cash",
                )

                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=self.ecosystem_default.responsible,
                    model=Responsible,
                    target=transaction,
                    target_attr_name="responsible",
                    source=action_transaction,
                    source_attr_name="responsible",
                )
                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=self.ecosystem_default.counterparty,
                    model=Counterparty,
                    target=transaction,
                    target_attr_name="counterparty",
                    source=action_transaction,
                    source_attr_name="counterparty",
                )

                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=None,
                    model=Instrument,
                    target=transaction,
                    target_attr_name="linked_instrument",
                    source=action_transaction,
                    source_attr_name="linked_instrument",
                )

                if action_transaction.linked_instrument_phantom is not None:
                    # transaction.linked_instrument = instrument_map[action_transaction.linked_instrument_phantom_id]
                    transaction.linked_instrument = instrument_map[
                        action_transaction.linked_instrument_phantom.order
                    ]

                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=None,
                    model=Instrument,
                    target=transaction,
                    target_attr_name="allocation_balance",
                    source=action_transaction,
                    source_attr_name="allocation_balance",
                )
                if action_transaction.allocation_balance_phantom is not None:
                    # transaction.allocation_balance = instrument_map[action_transaction.allocation_balance_phantom_id]
                    transaction.allocation_balance = instrument_map[
                        action_transaction.allocation_balance_phantom.order
                    ]

                self._set_rel(
                    errors=errors,
                    values=self.values,
                    default_value=None,
                    model=Instrument,
                    target=transaction,
                    target_attr_name="allocation_pl",
                    source=action_transaction,
                    source_attr_name="allocation_pl",
                )
                if action_transaction.allocation_pl_phantom is not None:
                    # transaction.allocation_pl = instrument_map[action_transaction.allocation_pl_phantom_id]
                    transaction.allocation_pl = instrument_map[
                        action_transaction.allocation_pl_phantom.order
                    ]

                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value=0.0,
                    target=transaction,
                    target_attr_name="reference_fx_rate",
                    source=action_transaction,
                    source_attr_name="reference_fx_rate",
                )
                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value=0.0,
                    target=transaction,
                    target_attr_name="factor",
                    source=action_transaction,
                    source_attr_name="factor",
                )
                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value=0.0,
                    target=transaction,
                    target_attr_name="trade_price",
                    source=action_transaction,
                    source_attr_name="trade_price",
                )
                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value=0.0,
                    target=transaction,
                    target_attr_name="position_amount",
                    source=action_transaction,
                    source_attr_name="position_amount",
                )
                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value=0.0,
                    target=transaction,
                    target_attr_name="principal_amount",
                    source=action_transaction,
                    source_attr_name="principal_amount",
                )
                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value=0.0,
                    target=transaction,
                    target_attr_name="carry_amount",
                    source=action_transaction,
                    source_attr_name="carry_amount",
                )
                self._set_val(
                    errors=errors,
                    values=self.values,
                    default_value=0.0,
                    target=transaction,
                    target_attr_name="overheads",
                    source=action_transaction,
                    source_attr_name="overheads",
                )

                transaction.carry_with_sign = format_float_to_2(
                    transaction.carry_with_sign
                )
                transaction.principal_with_sign = format_float_to_2(
                    transaction.principal_with_sign
                )
                transaction.overheads_with_sign = format_float_to_2(
                    transaction.overheads_with_sign
                )

                transaction.cash_consideration = format_float_to_2(
                    transaction.cash_consideration
                )

                # _l.debug('action_transaction.notes')
                # _l.debug(action_transaction.notes)
                # _l.debug(self.values)

                if action_transaction.notes is not None:
                    self._set_val(
                        errors=errors,
                        values=self.values,
                        default_value="",
                        target=transaction,
                        target_attr_name="notes",
                        source=action_transaction,
                        source_attr_name="notes",
                    )

                if action_transaction.user_text_1 is not None:
                    self._set_val(
                        errors=errors,
                        values=self.values,
                        default_value="",
                        target=transaction,
                        target_attr_name="user_text_1",
                        source=action_transaction,
                        source_attr_name="user_text_1",
                    )

                if action_transaction.user_text_2 is not None:
                    self._set_val(
                        errors=errors,
                        values=self.values,
                        default_value="",
                        target=transaction,
                        target_attr_name="user_text_2",
                        source=action_transaction,
                        source_attr_name="user_text_2",
                    )

                if action_transaction.user_text_3 is not None:
                    self._set_val(
                        errors=errors,
                        values=self.values,
                        default_value="",
                        target=transaction,
                        target_attr_name="user_text_3",
                        source=action_transaction,
                        source_attr_name="user_text_3",
                    )

                if action_transaction.user_number_1 is not None:
                    self._set_val(
                        errors=errors,
                        values=self.values,
                        default_value=None,
                        target=transaction,
                        target_attr_name="user_number_1",
                        source=action_transaction,
                        source_attr_name="user_number_1",
                    )

                if action_transaction.user_number_2 is not None:
                    self._set_val(
                        errors=errors,
                        values=self.values,
                        default_value=None,
                        target=transaction,
                        target_attr_name="user_number_2",
                        source=action_transaction,
                        source_attr_name="user_number_2",
                    )

                if action_transaction.user_number_3 is not None:
                    self._set_val(
                        errors=errors,
                        values=self.values,
                        default_value=None,
                        target=transaction,
                        target_attr_name="user_number_3",
                        source=action_transaction,
                        source_attr_name="user_number_3",
                    )

                if action_transaction.user_date_1 is not None:
                    self._set_val(
                        errors=errors,
                        values=self.values,
                        default_value=None,
                        target=transaction,
                        target_attr_name="user_date_1",
                        source=action_transaction,
                        source_attr_name="user_date_1",
                    )

                if action_transaction.user_date_2 is not None:
                    self._set_val(
                        errors=errors,
                        values=self.values,
                        default_value=None,
                        target=transaction,
                        target_attr_name="user_date_2",
                        source=action_transaction,
                        source_attr_name="user_date_2",
                    )

                if action_transaction.user_date_3 is not None:
                    self._set_val(
                        errors=errors,
                        values=self.values,
                        default_value=None,
                        target=transaction,
                        target_attr_name="user_date_3",
                        source=action_transaction,
                        source_attr_name="user_date_3",
                    )

                if action_transaction.is_canceled is not None:
                    self._set_val(
                        errors=errors,
                        values=self.values,
                        default_value=False,
                        target=transaction,
                        target_attr_name="is_canceled",
                        source=action_transaction,
                        source_attr_name="is_canceled",
                    )

                transaction_date_source = "null"

                if transaction.accounting_date is None:
                    transaction.accounting_date = self._now
                else:
                    transaction_date_source = "accounting_date"

                if transaction.cash_date is None:
                    transaction.cash_date = self._now
                else:
                    transaction_date_source = "cash_date"

                # Set transaction date below

                if transaction_date_source == "accounting_date":
                    transaction.transaction_date = transaction.accounting_date
                elif transaction_date_source == "cash_date":
                    transaction.transaction_date = transaction.cash_date
                elif transaction_date_source == "null":
                    transaction.transaction_date = min(
                        transaction.accounting_date, transaction.cash_date
                    )

                try:

                    transaction.owner = self.member
                    # transaction.transaction_date = min(transaction.accounting_date, transaction.cash_date)
                    transaction.save()

                    self.record_execution_progress(f"Create Transaction {transaction}")

                    # self.assign_permissions_to_transaction(transaction)

                except (ValueError, TypeError, IntegrityError) as error:
                    _l.debug(error)

                    self._add_err_msg(errors, "non_field_errors", str(error))
                except DatabaseError:
                    self._add_err_msg(
                        errors,
                        "non_field_errors",
                        gettext_lazy("General DB error."),
                    )
                else:
                    self.transactions.append(transaction)
                finally:
                    # _l.debug("Transaction action errors %s " % errors)

                    if bool(errors):
                        self.transactions_errors.append(errors)

    def _save_inputs(self):
        self.complex_transaction.inputs.all().delete()

        inputs_to_create = []

        for ti in self.transaction_type.inputs.all():
            val = self.values.get(ti.name, None)

            ci = ComplexTransactionInput()
            ci.complex_transaction = self.complex_transaction
            ci.transaction_type_input = ti

            if ti.value_type in (
                    TransactionTypeInput.STRING,
                    TransactionTypeInput.SELECTOR,
            ):
                if val is None:
                    val = ""
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

                if val:
                    ci.value_relation = val.user_code

            inputs_to_create.append(ci)

        ComplexTransactionInput.objects.bulk_create(inputs_to_create)

    def execute_user_fields_expressions(self):
        ctrn = formula.value_prepare(self.complex_transaction)
        trns = self.complex_transaction.transactions.all()

        names = {
            "complex_transaction": ctrn,
            "transactions": trns,
        }

        for key, value in self.values.items():
            names[key] = value

        self.record_execution_progress("Calculating User Fields")

        _result_for_log = {}
        for field_key in generate_user_fields():

            if not hasattr(self.complex_transaction.transaction_type, field_key):
                continue

            field_value = getattr(self.complex_transaction.transaction_type, field_key)
            try:
                value = formula.safe_eval(
                    field_value,
                    names=names,
                    context=self._context
                )
                setattr(self.complex_transaction, field_key, value)
                _result_for_log[field_key] = value

            except Exception as e:
                _l.error(
                    f"execute_user_fields_expressions: formula.safe_eval resulted in {repr(e)} "
                    f"field {field_key} value {field_value} names {names} context {self._context}"
                )
                setattr(self.complex_transaction, field_key, None)
                _result_for_log[field_key] = f"value {field_value} error {e}"

        self.record_execution_progress("==== USER FIELDS ====", _result_for_log)

    def execute_recon_fields_expressions(self):
        try:
            from poms.reconciliation.models import ReconciliationComplexTransactionField

            ctrn = formula.value_prepare(self.complex_transaction)
            trns = self.complex_transaction.transactions.all()

            names = {
                "complex_transaction": ctrn,
                "transactions": trns,
            }

            for key, value in self.values.items():
                names[key] = value

            ReconciliationComplexTransactionField.objects.filter(
                master_user=self.transaction_type.master_user,
                complex_transaction=self.complex_transaction,
            ).delete()

            ttype_fields = TransactionTypeReconField.objects.filter(
                transaction_type=self.transaction_type
            )

            for ttype_field in ttype_fields:
                field = ReconciliationComplexTransactionField(
                    master_user=self.transaction_type.master_user,
                    complex_transaction=self.complex_transaction,
                )

                if ttype_field.value_string:
                    try:
                        field.value_string = formula.safe_eval(
                            ttype_field.value_string, names=names, context=self._context
                        )
                    except formula.InvalidExpression:
                        field.value_string = "<InvalidExpression>"
                if ttype_field.value_float:
                    with contextlib.suppress(formula.InvalidExpression):
                        field.value_float = formula.safe_eval(
                            ttype_field.value_float, names=names, context=self._context
                        )

                if ttype_field.value_date:
                    with contextlib.suppress(formula.InvalidExpression):
                        field.value_date = formula.safe_eval(
                            ttype_field.value_date, names=names, context=self._context
                        )
                field.reference_name = ttype_field.reference_name
                field.description = ttype_field.description
                field.save()

        except Exception as error:
            _l.error(f"execute_recon_fields_expressions {error}")

    def execute_complex_transaction_main_expressions(self):
        # _l.debug('execute_complex_transaction_main_expressions')

        self.record_execution_progress("Calculating Description")

        if self.complex_transaction.transaction_type.display_expr:
            names = self._prepare_names()
            try:
                self.complex_transaction.text = formula.safe_eval(
                    self.complex_transaction.transaction_type.display_expr,
                    names=names,
                    context=self._context,
                )
            except Exception as e:
                _l.debug(
                    f"Cant process text {repr(e)} names {names} "
                    f"self.complex_transaction.transaction_type.display_expr "
                    f"{self.complex_transaction.transaction_type.display_expr}"
                )

                self.complex_transaction.text = "<InvalidExpression>"

        self.record_execution_progress(f"Text: {self.complex_transaction.text}")

        self.record_execution_progress("Calculating Date")

        if self.complex_transaction.transaction_type.date_expr:
            names = self._prepare_names()
            self.complex_transaction.date = self._now  # as default

            try:
                self.complex_transaction.date = formula.safe_eval(
                    self.complex_transaction.transaction_type.date_expr,
                    names=names,
                    context=self._context,
                )
            except formula.InvalidExpression:
                self.complex_transaction.date = self._now

        else:
            self.complex_transaction.date = self._now

        self.record_execution_progress(f"Date: {self.complex_transaction.date}")

    def _prepare_names(self):
        names = {
            "complex_transaction": formula.value_prepare(self.complex_transaction),
            "transactions": self.complex_transaction.transactions.all(),
        }

        for key, value in self.values.items():
            names[key] = value

        return names

    def execute_uniqueness_expression(self):
        # _l.debug('execute_uniqueness_expression self.uniqueness_reaction %s' % self.uniqueness_reaction)

        self.record_execution_progress("Calculating Unique Code")

        names = dict(self.values.items())

        try:
            self.complex_transaction.transaction_unique_code = formula.safe_eval(
                self.complex_transaction.transaction_type.transaction_unique_code_expr,
                names=names,
                context=self._context,
            )

        except Exception as e:
            _l.error(
                f"execute_uniqueness_expression.e {e} names {names} "
                f"trace {traceback.format_exc()}"
            )
            self.complex_transaction.transaction_unique_code = None

        _l.info(
            f'self.complex_transaction.transaction_unique_code '
            f'{self.complex_transaction.transaction_unique_code}'
        )

        if self.is_rebook:
            try:
                exist = ComplexTransaction.objects.exclude(
                    code=self.complex_transaction.code
                ).filter(
                    master_user=self.transaction_type.master_user,
                    transaction_unique_code=self.complex_transaction.transaction_unique_code,
                )[
                    0
                ]
            except Exception as e:
                exist = None
                _l.error(f"execute_uniqueness_expression.is_rebook exist {repr(e)} ")

            if (
                    self.uniqueness_reaction == TransactionType.SKIP
                    and exist
                    and self.complex_transaction.transaction_unique_code
            ):
                self.skipped_book_unique_code_error()

            elif (
                    self.uniqueness_reaction == TransactionType.SKIP
                    and not exist
                    and self.complex_transaction.transaction_unique_code
            ):
                # Just create complex transaction
                self.uniqueness_status = "update"

                self.record_execution_progress(
                    "Unique code is owned by its transaction, can update transaction. "
                    "(TransactionType.SKIP)"
                )

            elif self.uniqueness_reaction == TransactionType.BOOK_WITHOUT_UNIQUE_CODE:
                self.book_without_unique_code()
            elif (
                    self.uniqueness_reaction == TransactionType.OVERWRITE
                    and self.complex_transaction.transaction_unique_code
            ):
                self.uniqueness_status = "overwrite"

                if exist:
                    exist.fake_delete()

                    self.record_execution_progress(
                        f"Unique Code is occupied, delete transaction {exist.code}"
                        f" (OVERWRITE)"
                    )
                else:
                    self.record_execution_progress(
                        "Unique Code is free, can create transaction (OVERWRITE)"
                    )

        else:
            # exist = ComplexTransaction.objects.filter(
            #     master_user=self.transaction_type.master_user,
            #     transaction_unique_code=self.complex_transaction.transaction_unique_code,
            # ).first()
            exist = ComplexTransaction.objects.filter(
                transaction_unique_code=self.complex_transaction.transaction_unique_code,
            ).first()

            _l.info(
                f"execute_uniqueness_expression.uniqueness_reaction="
                f"{self.uniqueness_reaction} exist={exist}"
            )

            if (
                    self.uniqueness_reaction == TransactionType.SKIP
                    and exist
                    and self.complex_transaction.transaction_unique_code
            ):
                self.skipped_book_unique_code_error()

            elif (
                    self.uniqueness_reaction == TransactionType.SKIP
                    and not exist
                    and self.complex_transaction.transaction_unique_code
            ):
                # Just create complex transaction
                self.uniqueness_status = "create"
                self.record_execution_progress(
                    "Unique code is free, can create transaction. (SKIP)"
                )

            elif self.uniqueness_reaction == TransactionType.BOOK_WITHOUT_UNIQUE_CODE:
                self.book_without_unique_code()

            elif (
                    self.uniqueness_reaction == TransactionType.OVERWRITE
                    and self.complex_transaction.transaction_unique_code
            ):
                if exist:
                    self.record_execution_progress(
                        "Unique Code is already in use, can create transaction. "
                        "Previous Transaction is deleted (OVERWRITE)"
                    )
                    exist.fake_delete()

                    self.uniqueness_status = "overwrite"
                    self.record_execution_progress(
                        f"Unique Code is occupied, delete transaction {exist.code} "
                    )

                else:
                    self.uniqueness_status = "create"
                    self.record_execution_progress(
                        "Unique Code is free, can create transaction (OVERWRITE)"
                    )

            elif (
                    self.uniqueness_reaction == TransactionType.TREAT_AS_ERROR
                    and exist
                    and self.complex_transaction.transaction_unique_code
            ):
                # TODO ask if behavior same as skip
                self.uniqueness_status = "error"
                self.complex_transaction.fake_delete()
                self.general_errors.append(
                    {
                        "reason": 410,
                        "message": "Skipped book. Transaction Unique code error",
                    }
                )
            else:
                self.uniqueness_status = "error"
                self.complex_transaction.fake_delete()
                msg = (
                    f"is_rebook={self.is_rebook} "
                    f"uniqueness_reaction={self.uniqueness_reaction} "
                    f"exist={exist} names={names}"
                    f"complex_transaction.transaction_unique_code="
                    f"{self.complex_transaction.transaction_unique_code}",
                )
                _l.error(f"execute_uniqueness_expression: invalid params: {msg}")
                self.general_errors.append(
                    {
                        "reason": 409,
                        "message": f"Skipped book. Invalid combination of params {msg}",
                    }
                )

        self.record_execution_progress(
            f"Unique Code: {self.complex_transaction.transaction_unique_code} "
        )

    def skipped_book_unique_code_error(self):
        # Do not create a new transaction if transaction with that code already exists
        self.uniqueness_status = "skip"
        self.general_errors.append(
            {
                "reason": 409,
                "message": "Skipped book. Transaction Unique Code error",
            }
        )

    def book_without_unique_code(self):
        self.uniqueness_status = "booked_without_unique_code"
        self.record_execution_progress("Book without Unique Code")
        self.complex_transaction.transaction_unique_code = None

    def run_procedures_after_book(self):
        # from poms.portfolios.tasks import (
        #     calculate_portfolio_register_price_history,
        #     calculate_portfolio_register_record,
        # )

        # _l.debug("TransactionTypeProcess.run_procedures_after_book. execution_context
        # %s" % self.execution_context)

        try:
            if self.execution_context == "manual":
                # cache.clear()

                if self.complex_transaction.status_id == ComplexTransaction.PRODUCTION:
                    date_from = None

                    transactions = self.complex_transaction.transactions.all()

                    for transaction in transactions:
                        _date_from = min(
                            transaction.accounting_date, transaction.cash_date
                        )

                        if date_from is None:
                            date_from = _date_from

                        if _date_from < date_from:
                            date_from = _date_from

                    # _l.debug("TransactionTypeProcess.run_procedures_after_book.
                    # recalculating from %s" % date_from)

                    # TODO trigger recalc after manual book properly
                    # calculate_portfolio_register_record.apply_async(link=[
                    #     calculate_portfolio_register_price_history.s(date_from=date_from)
                    # ])

        except Exception as e:
            _l.error(
                f"TransactionTypeProcess.run_procedures_after_book e {e} "
                f"traceback {traceback.format_exc()}"
            )

    def process_as_pending(self):
        _l.debug("Process as pending")

        complex_transaction_errors = {}
        if self.complex_transaction.date is None:
            self.complex_transaction.date = self._now  # set by default

            self._set_val(
                errors=complex_transaction_errors,
                values=self.values,
                default_value=self._now,
                target=self.complex_transaction,
                target_attr_name="date",
                source=self.transaction_type,
                source_attr_name="date_expr",
                validator=formula.validate_date,
            )

        if bool(complex_transaction_errors):
            self.complex_transaction_errors.append(complex_transaction_errors)

        self.complex_transaction.status_id = ComplexTransaction.PENDING

        self.execute_complex_transaction_main_expressions()

        self.execute_user_fields_expressions()

        if self.linked_import_task:
            self.complex_transaction.linked_import_task = self.linked_import_task

        self.complex_transaction.owner = self.member
        self.complex_transaction.save()

        self._save_inputs()

        # self.assign_permissions_to_pending_complex_transaction() FIXME no such !

        self.run_procedures_after_book()

        if self.execution_context == "manual":
            system_message_title = "New transactions (manual)"
            system_message_description = (
                f"New transactions created (manual) - "
                f"{str(self.complex_transaction.text)}"
            )

            if self.process_mode == self.MODE_REBOOK:
                system_message_title = "Edit transactions (manual)"
                system_message_description = (
                    f"Edit transaction - {str(self.complex_transaction.text)}"
                )

            send_system_message(
                master_user=self.transaction_type.master_user,
                performed_by=self.member.username,
                section="transactions",
                type="success",
                title=system_message_title,
                description=system_message_description,
            )

    def process(self):
        if self.process_mode == self.MODE_RECALCULATE:
            return self.process_recalculate()

        process_st = time.perf_counter()

        self.record_execution_progress("Booking Process Initialized")

        master_user = self.transaction_type.master_user

        instrument_map = {}
        event_schedules_map = {}
        actions = self.transaction_type.actions.order_by("order").all()

        """
        Creating instruments
        """
        instruments_st = time.perf_counter()
        instrument_map = self.book_create_instruments(
            actions, master_user, instrument_map
        )
        _l.debug(
            "TransactionTypeProcess: book_create_instruments done: %s",
            "{:3.3f}".format(time.perf_counter() - instruments_st),
        )

        """
        Creating instrument's factor schedules
        """
        create_factor_st = time.perf_counter()
        self.book_create_factor_schedules(actions, instrument_map)
        _l.debug(
            "TransactionTypeProcess: book_create_factor_schedules done: %s",
            "{:3.3f}".format(time.perf_counter() - create_factor_st),
        )

        """
        Creating instruments manual pricing formulas
        """
        create_manual_pricing_st = time.perf_counter()
        self.book_create_manual_pricing_formulas(actions, instrument_map)
        _l.debug(
            "TransactionTypeProcess: book_create_manual_pricing_formulas done: %s",
            "{:3.3f}".format(time.perf_counter() - create_manual_pricing_st),
        )

        """
        Creating instruments accrual schedules
        """
        create_accrual_calculation_st = time.perf_counter()
        self.book_create_accrual_calculation_schedules(actions, instrument_map)
        _l.debug(
            "TransactionTypeProcess: book_create_accrual_calculation_schedules done: %s",
            "{:3.3f}".format(time.perf_counter() - create_accrual_calculation_st),
        )

        """
        Creating instruments event schedules
        """
        create_event_schedules_st = time.perf_counter()
        event_schedules_map = self.book_create_event_schedules(
            actions, instrument_map, event_schedules_map
        )
        _l.debug(
            "TransactionTypeProcess: book_create_event_schedules done: %s",
            "{:3.3f}".format(time.perf_counter() - create_event_schedules_st),
        )

        """
        Creating instruments event schedules actions
        """
        create_event_st = time.perf_counter()
        self.book_create_event_actions(actions, instrument_map, event_schedules_map)
        _l.debug(
            "TransactionTypeProcess: book_create_event_actions done: %s",
            "{:3.3f}".format(time.perf_counter() - create_event_st),
        )

        """
        Executing transaction_unique_code
        """
        execute_uniqueness_expression_st = time.perf_counter()
        self.execute_uniqueness_expression()
        _l.debug(
            "TransactionTypeProcess: execute_uniqueness_expression done: %s",
            "{:3.3f}".format(time.perf_counter() - execute_uniqueness_expression_st),
        )

        """
        Creating complex_transaction itself
        """
        create_complex_transaction_st = time.perf_counter()
        complex_transaction_errors = {}
        if self.complex_transaction.date is None:
            self.complex_transaction.date = self._now  # set by default

        self._set_val(
            errors=complex_transaction_errors,
            values=self.values,
            default_value=self._now,
            target=self.complex_transaction,
            target_attr_name="date",
            source=self.transaction_type,
            source_attr_name="date_expr",
            validator=formula.validate_date,
        )

        if bool(complex_transaction_errors):
            self.complex_transaction_errors.append(complex_transaction_errors)

        if self.has_errors:
            return  # important to return here if we already had errors

        if self.complex_transaction_status is not None:
            self.complex_transaction.status_id = self.complex_transaction_status

        if self.source:
            self.complex_transaction.source = self.source

        if self.complex_transaction.transaction_unique_code:
            count = (
                ComplexTransaction.objects.filter(
                    transaction_unique_code=self.complex_transaction.transaction_unique_code
                )
                .exclude(code=self.complex_transaction.code)
                .count()
            )

            if self.uniqueness_status == "overwrite":
                # TODO this is weird logic, but ok for now

                items = ComplexTransaction.objects.filter(
                    transaction_unique_code=self.complex_transaction.transaction_unique_code
                ).exclude(code=self.complex_transaction.code)

                for item in items:
                    item.fake_delete()

            elif count > 0:
                raise RuntimeError("Transaction Unique Code must be unique")

        _l.debug(
            f"self.complex_transaction.transaction_unique_code"
            f" {self.complex_transaction.transaction_unique_code} "
            f"id {self.complex_transaction.id} "
            f"code {self.complex_transaction.code}"
        )

        self.complex_transaction.owner = self.member
        self.complex_transaction.save()  # save executed text and date expression
        self._context["complex_transaction"] = self.complex_transaction

        self._save_inputs()
        _l.debug(
            "TransactionTypeProcess: create_complex_transaction done: %s",
            "{:3.3f}".format(time.perf_counter() - create_complex_transaction_st),
        )

        """
        Executing command actions
        """
        book_execute_commands_st = time.perf_counter()
        self._context["values"] = self.values
        self.book_execute_commands(actions)
        _l.debug(
            "TransactionTypeProcess: book_execute_commands done: %s",
            "{:3.3f}".format(time.perf_counter() - book_execute_commands_st),
        )

        """
        Creating base transactions
        """
        delete_old_transactions_st = time.perf_counter()
        self.complex_transaction.transactions.all().delete()
        _l.debug(
            "TransactionTypeProcess: delete_old_transactions done: %s",
            "{:3.3f}".format(time.perf_counter() - delete_old_transactions_st),
        )

        book_create_transactions_st = time.perf_counter()
        self.book_create_transactions(actions, master_user, instrument_map)
        _l.debug(
            "TransactionTypeProcess: book_create_transactions_st done: %s",
            "{:3.3f}".format(time.perf_counter() - book_create_transactions_st),
        )

        is_canceled = any(
            trn.is_canceled for trn in self.complex_transaction.transactions.all()
        )
        if is_canceled:
            self.record_execution_progress("Complex Transaction is canceled")

        self.complex_transaction.is_canceled = is_canceled

        self.record_execution_progress(
            f"Complex Transaction {self.complex_transaction.code} Booked"
        )

        self.record_execution_progress("Saving Complex Transaction")
        self.record_execution_progress(" ")
        self.record_execution_progress("+====+====+")
        self.record_execution_progress(" ")

        """
        Executing complex_transaction.text expression
        """
        execute_complex_transaction_main_expressions_st = time.perf_counter()
        self.execute_complex_transaction_main_expressions()
        _l.debug(
            "TransactionTypeProcess: execute_complex_transaction_main_expressions done: %s",
            "{:3.3f}".format(
                time.perf_counter() - execute_complex_transaction_main_expressions_st
            ),
        )

        """
        Executing user_fields
        """
        execute_user_fields_expressions_st = time.perf_counter()
        self.execute_user_fields_expressions()
        _l.debug(
            "TransactionTypeProcess: execute_user_fields_expressions done: %s",
            "{:3.3f}".format(time.perf_counter() - execute_user_fields_expressions_st),
        )

        # _l.debug("LOG %s" % self.complex_transaction.execution_log)
        # self.assign_permissions_to_complex_transaction()

        self.run_procedures_after_book()

        if self.complex_transaction.status_id == ComplexTransaction.PENDING:
            self.complex_transaction.transactions.all().delete()

        if (
                self.complex_transaction.transaction_type.type
                == TransactionType.TYPE_PROCEDURE
        ):
            self.complex_transaction.fake_delete()
            self.complex_transaction = None

        self.record_execution_progress(
            "Process time: %s" % "{:3.3f}".format(time.perf_counter() - process_st)
        )

        if self.complex_transaction and not self.has_errors:
            self.complex_transaction.owner = self.member
            self.complex_transaction.save()  # save executed text and date expression

        _l.debug(
            "TransactionTypeProcess: process done: %s",
            "{:3.3f}".format(time.perf_counter() - process_st),
        )

        _l.debug(
            f"self.value_errors {self.value_errors} "
            f"instruments_errors {self.instruments_errors} "
            f"complex_transaction_errors {self.complex_transaction_errors} "
            f"transactions_errors {self.transactions_errors}"
        )

    def process_recalculate(self):
        if not self.recalculate_inputs:
            return

        process_recalculate_st = time.perf_counter()

        inputs = {i.name: i for i in self.inputs}

        _l.debug(f"self.recalculate_inputs {self.recalculate_inputs}")

        iteration_count = 5

        # szhitenev
        # need to handle case when we trying calculate inputs that required on other inputs beign calculated
        for i in range(iteration_count):
            for name in self.recalculate_inputs:
                inp = inputs[name]
                if inp.can_recalculate:

                    if inp.expression_iterations_count > i:

                        # _l.info('inp.expression_iterations_count %s' % inp.expression_iterations_count)
                        # _l.info('inp.i %s' % i)
                        # _l.info('inp %s' % name)

                        errors = {}

                        if inp.value_type in [TransactionTypeInput.RELATION]:
                            try:
                                res = formula.safe_eval(
                                    inp.value_expr,
                                    names=self.values,
                                    now=self._now,
                                    context=self._context,
                                )

                                Model = apps.get_model(
                                    app_label=inp.content_type.app_label,
                                    model_name=inp.content_type.model,
                                )

                                try:
                                    self.values[name] = Model.objects.get(
                                        master_user=self.transaction_type.master_user,
                                        user_code=res,
                                    )

                                except Model.DoesNotExist as e:
                                    raise formula.InvalidExpression from e

                            except formula.InvalidExpression as e:
                                ecosystem_default = EcosystemDefault.objects.get(
                                    master_user=self.transaction_type.master_user
                                )

                                _l.debug(f"error {repr(e)}")
                                _l.debug(inp.content_type)

                                entity_map = {
                                    "instrument": "instrument",
                                    "instrumenttype": "instrument_type",
                                    "account": "account",
                                    "currency": "currency",
                                    "counterparty": "counterparty",
                                    "responsible": "responsible",
                                    "portfolio": "portfolio",
                                    "strategy1": "strategy1",
                                    "strategy2": "strategy2",
                                    "strategy3": "strategy3",
                                    "dailypricingmodel": "daily_pricing_model",
                                    "paymentsizedetail": "payment_size_detail",
                                    "pricingpolicy": "pricing_policy",
                                    "periodicity": "periodicity",
                                    "accrualcalculationmodel": "accrual_calculation_model",
                                    "eventclass": "event_class",
                                    "notificationclass": "notification_class",
                                }

                                key = entity_map[inp.content_type.model]

                                if hasattr(ecosystem_default, key):
                                    res = getattr(ecosystem_default, key)
                                    self.values[name] = res
                                else:
                                    self._set_eval_error(errors, inp.name, inp.value_expr, e)
                                    self.value_errors.append(errors)

                        else:
                            _l.debug(f"inp {inp}")
                            _l.debug(f"inp {inp.value_expr}")

                            try:
                                res = formula.safe_eval(
                                    inp.value_expr,
                                    names=self.values,
                                    now=self._now,
                                    context=self._context,
                                )
                                self.values[name] = res

                                _l.debug(f"process_recalculate self.values {self.values}")

                            except formula.InvalidExpression as e:
                                self._handle_errors(e, inp, name, errors)
            _l.debug(
                "TransactionTypeProcess: process_recalculate done: %s",
                "{:3.3f}".format(time.perf_counter() - process_recalculate_st),
            )

    def _handle_errors(self, e, inp, name, errors):
        _l.error(
            f"process_recalculate {repr(e)} traceback {traceback.format_exc()} "
            f"self.values {self.values}"
        )

        if inp.value_type == TransactionTypeInput.STRING:
            self.values[name] = "Invalid Expression"
        else:
            self.values[name] = None

        self._set_eval_error(errors, inp.name, inp.value_expr, e)
        self.value_errors.append(errors)

    @property
    def has_errors(self):
        return (
                bool(self.instruments_errors)
                or any(bool(e) for e in self.general_errors)
                or any(bool(e) for e in self.value_errors)
                or any(bool(e) for e in self.complex_transaction_errors)
                or any(bool(e) for e in self.transactions_errors)
        )

    def _set_val(
            self,
            errors,
            values,
            default_value,
            target,
            target_attr_name,
            source,
            source_attr_name,
            validator=None,
            object_data=None,
    ):
        value = getattr(source, source_attr_name)
        if value:
            try:
                value = formula.safe_eval(
                    value, names=values, now=self._now, context=self._context
                )
            except formula.InvalidExpression as e:
                self._set_eval_error(errors, source_attr_name, value, e)
                return
            if callable(validator):
                value = validator(value)
        else:
            value = default_value

        if object_data:  # set default from instrument type?
            object_data[target_attr_name] = value

        setattr(target, target_attr_name, value)  # set computed value

    def _set_rel(
            self,
            errors,
            values,
            default_value,
            target,
            target_attr_name,
            source,
            source_attr_name,
            model,
            object_data=None,
    ):
        user_code = getattr(source, source_attr_name, None)  # got user_code
        value = None
        if user_code:
            # convert to id
            if model:
                # _l.debug('_set_rel model %s ' % model)
                # _l.debug('_set_rel value %s ' % user_code)

                try:
                    if model._meta.get_field("master_user"):
                        value = model.objects.get(
                            master_user=self.transaction_type.master_user,
                            user_code=user_code,
                        )

                except Exception as e:
                    try:
                        value = model.objects.get(user_code=user_code)
                    except Exception as e:
                        _l.debug(f"User code for default value is not found {e}")
        else:
            from_input = getattr(source, f"{source_attr_name}_input")
            if from_input:
                # _l.debug('_set_rel values %s ' % values)

                value = values[from_input.name]
        if not value:
            value = default_value
        if value is not None:
            setattr(target, target_attr_name, value)

            if object_data:
                object_data[target_attr_name] = value.id

    def _set_eval_error(self, errors, attr_name, expression, exc=None):
        msg = gettext_lazy('Invalid expression "%(expression)s".') % {
            "expression": expression,
        }
        return self._add_err_msg(errors, attr_name, msg)

    def _add_err_msg(self, errors, key, msg):
        msgs = errors.get(key, None) or []
        if msg not in msgs:
            msgs.append(msg)
            errors[key] = msgs
        return msgs
