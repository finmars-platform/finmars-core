import logging
import time
import traceback

from django.contrib.contenttypes.models import ContentType

from poms.currencies.models import Currency
from poms.instruments.models import GeneratedEvent, Instrument
from poms.obj_attrs.models import GenericAttributeType, GenericClassifier
from poms.transactions.handlers import TransactionTypeProcess
from poms.transactions.models import ComplexTransaction, TransactionType
from poms.users.models import EcosystemDefault

_l = logging.getLogger("poms.instruments")


class GeneratedEventProcess(TransactionTypeProcess):
    def __init__(self, generated_event=None, action=None, **kwargs):
        _l.info("GeneratedEventProcess")

        try:
            self.generated_event = generated_event
            self.action = action

            kwargs["transaction_type"] = TransactionType.objects.get(
                master_user=generated_event.master_user,
                user_code=action.transaction_type,
            )

            # Some Inputs can choose from which context variable it will take value
            context_values = kwargs.get("context_values", None) or {}
            context_values.update(
                {
                    "context_instrument": generated_event.instrument,
                    "context_pricing_currency": generated_event.instrument.pricing_currency,
                    "context_accrued_currency": generated_event.instrument.accrued_currency,
                    "context_portfolio": generated_event.portfolio,
                    "context_account": generated_event.account,
                    "context_strategy1": generated_event.strategy1,
                    "context_strategy2": generated_event.strategy2,
                    "context_strategy3": generated_event.strategy3,
                    "context_position": generated_event.position,
                    "context_effective_date": generated_event.effective_date,
                    "context_notification_date": generated_event.notification_date,
                    # not in context variables
                    # 'final_date': generated_event.event_schedule.final_date,
                    # 'maturity_date': generated_event.instrument.maturity_date
                }
            )

            _l.info(
                f"generated_event data {generated_event.data} action {action} "
                f"action.button_position {action.button_position}"
            )

            if generated_event.data and (
                "actions_parameters" in generated_event.data
                and (
                    str(action.button_position)
                    in generated_event.data["actions_parameters"]
                )
            ):
                for key, value in generated_event.data["actions_parameters"][
                    str(action.button_position)
                ].items():
                    _l.info(f"key {key}: value {value}")
                    context_values.update({key: value})

            kwargs["context_values"] = context_values

            if (
                generated_event.status != GeneratedEvent.ERROR
                and action.is_sent_to_pending
                or generated_event.status == GeneratedEvent.ERROR
            ):
                kwargs["complex_transaction_status"] = ComplexTransaction.PENDING
            else:
                kwargs["complex_transaction_status"] = ComplexTransaction.PRODUCTION

            super(GeneratedEventProcess, self).__init__(**kwargs)

        except Exception as e:
            _l.error(
                f"GeneratedEventProcess.error {repr(e)} trace {traceback.print_exc()}"
            )
            raise e


class InstrumentTypeProcess(object):
    def __init__(self, instrument_type=None, context=None):
        self.instrument_type = instrument_type
        self.context = context

        self.ecosystem_default = EcosystemDefault.objects.get(
            master_user=self.instrument_type.master_user
        )

        self.instrument_object = {"instrument_type": instrument_type.id, "identifier": {}}
        self.fill_instrument_with_instrument_type_defaults()
        self.set_pricing_policies()

        self.instrument = self.instrument_object

    def fill_instrument_with_instrument_type_defaults(self):
        try:
            start_time = time.time()

            # Set system attributes

            if self.instrument_type.payment_size_detail:
                self.instrument_object[
                    "payment_size_detail"
                ] = self.instrument_type.payment_size_detail_id
            else:
                self.instrument_object["payment_size_detail"] = None

            if self.instrument_type.pricing_condition:
                self.instrument_object[
                    "pricing_condition"
                ] = self.instrument_type.pricing_condition_id
            else:
                self.instrument_object["pricing_condition"] = None

            if self.instrument_type.accrued_currency:
                self.instrument_object[
                    "accrued_currency"
                ] = self.instrument_type.accrued_currency_id
            else:
                self.instrument_object[
                    "accrued_currency"
                ] = self.ecosystem_default.currency.pk

            if self.instrument_type.pricing_currency:
                self.instrument_object[
                    "pricing_currency"
                ] = self.instrument_type.pricing_currency_id
            else:
                self.instrument_object[
                    "pricing_currency"
                ] = self.ecosystem_default.currency.pk

            # self.instrument_object["instrument_type_pricing_policies"] = []
            #
            # if self.instrument_type.pricing_policies:
            #     self.instrument_object[
            #         "_instrument_type_pricing_policies"
            #     ] = self.instrument_type.pricing_policies

            self.instrument_object["default_price"] = self.instrument_type.default_price
            self.instrument_object["maturity_date"] = self.instrument_type.maturity_date
            self.instrument_object[
                "maturity_price"
            ] = self.instrument_type.maturity_price

            self.instrument_object[
                "accrued_multiplier"
            ] = self.instrument_type.accrued_multiplier
            self.instrument_object[
                "price_multiplier"
            ] = self.instrument_type.price_multiplier

            self.instrument_object[
                "default_accrued"
            ] = self.instrument_type.default_accrued
            self.instrument_object[
                "reference_for_pricing"
            ] = self.instrument_type.reference_for_pricing
            self.instrument_object[
                "pricing_condition"
            ] = self.instrument_type.pricing_condition_id
            self.instrument_object[
                "position_reporting"
            ] = self.instrument_type.position_reporting

            if self.instrument_type.exposure_calculation_model:
                self.instrument_object[
                    "exposure_calculation_model"
                ] = self.instrument_type.exposure_calculation_model_id
            else:
                self.instrument_object["exposure_calculation_model"] = None

            try:
                self.instrument_object[
                    "long_underlying_instrument"
                ] = Instrument.objects.get(
                    master_user=self.instrument_type.master_user,
                    user_code=self.instrument_type.long_underlying_instrument,
                ).pk
            except Exception as e:
                _l.info("Could not set long_underlying_instrument, fallback to default")
                self.instrument_object[
                    "long_underlying_instrument"
                ] = self.ecosystem_default.instrument.pk

            self.instrument_object[
                "underlying_long_multiplier"
            ] = self.instrument_type.underlying_long_multiplier

            self.instrument_object[
                "short_underlying_instrument"
            ] = self.instrument_type.short_underlying_instrument

            try:
                self.instrument_object[
                    "short_underlying_instrument"
                ] = Instrument.objects.get(
                    master_user=self.instrument_type.master_user,
                    user_code=self.instrument_type.short_underlying_instrument,
                ).pk
            except Exception as e:
                _l.info(
                    f"Could not set short_underlying_instrument {repr(e)}, "
                    f"fallback to default"
                )
                self.instrument_object[
                    "short_underlying_instrument"
                ] = self.ecosystem_default.instrument.pk

            self.instrument_object[
                "underlying_short_multiplier"
            ] = self.instrument_type.underlying_short_multiplier

            self.instrument_object[
                "long_underlying_exposure"
            ] = self.instrument_type.long_underlying_exposure_id
            self.instrument_object[
                "short_underlying_exposure"
            ] = self.instrument_type.short_underlying_exposure_id

            try:
                self.instrument_object[
                    "co_directional_exposure_currency"
                ] = Currency.objects.get(
                    master_user=self.instrument_type.master_user,
                    user_code=self.instrument_type.co_directional_exposure_currency,
                ).pk
            except Exception as e:
                _l.info(
                    f"Could not set co_directional_exposure_currency, {repr(e)} "
                    f"fallback to default"
                )
                self.instrument_object[
                    "co_directional_exposure_currency"
                ] = self.ecosystem_default.currency.pk

            try:
                self.instrument_object[
                    "counter_directional_exposure_currency"
                ] = Currency.objects.get(
                    master_user=self.instrument_type.master_user,
                    user_code=self.instrument_type.counter_directional_exposure_currency,
                ).pk
            except Exception as e:
                _l.info(
                    f"Could not set counter_directional_exposure_currency {repr(e)}, "
                    f"fallback to default"
                )
                self.instrument_object[
                    "counter_directional_exposure_currency"
                ] = self.ecosystem_default.currency.pk

            # Set attributes
            self.instrument_object["attributes"] = []

            content_type = ContentType.objects.get(
                model="instrument", app_label="instruments"
            )

            for attribute in self.instrument_type.instrument_attributes.all():
                attribute_type = GenericAttributeType.objects.get(
                    master_user=self.instrument_type.master_user,
                    content_type=content_type,
                    user_code=attribute.attribute_type_user_code,
                )

                attr = {
                    "attribute_type": attribute_type.id,
                    "attribute_type_object": {
                        "id": attribute_type.id,
                        "name": attribute_type.name,
                        "user_code": attribute_type.user_code,
                        "value_type": attribute_type.value_type,
                    },
                    "value_string": None,
                    "value_float": None,
                    "value_date": None,
                    "classifier": None,
                    "classifier_object": None,
                }

                if attribute.value_type == 10:
                    attr["value_string"] = attribute.value_string

                elif attribute.value_type == 20:
                    attr["value_float"] = attribute.value_float

                elif attribute.value_type == 30:
                    try:
                        _l.info(
                            f"attribute.value_classifier {attribute.value_classifier}"
                        )

                        classifier = GenericClassifier.objects.filter(
                            name=attribute.value_classifier,
                            attribute_type=attribute_type,
                        )[0]

                        attr["classifier"] = classifier.id
                        attr["classifier_object"] = {
                            "id": classifier.id,
                            "level": classifier.level,
                            "parent": classifier.parent,
                            "name": classifier.name,
                        }
                    except Exception as e:
                        _l.info(f"GenericClassifier {repr(e)}")
                        attr["classifier"] = None
                        attr["classifier_object"] = None

                elif attribute.value_type == 40:
                    attr["value_date"] = attribute.value_date

                self.instrument_object["attributes"].append(attr)

            # Set Event Schedules

            self.instrument_object["event_schedules"] = []

            for instrument_type_event in self.instrument_type.events.all():
                event_schedule = {
                    "event_class": instrument_type_event.data["event_class"]
                }

                for item in instrument_type_event.data["items"]:
                    # TODO add check for value type
                    if "default_value" in item:
                        event_schedule[item["key"]] = item["default_value"]

                if "items2" in instrument_type_event.data:
                    for item in instrument_type_event.data["items2"]:
                        if "default_value" in item:
                            event_schedule[item["key"]] = item["default_value"]

                #
                event_schedule["is_auto_generated"] = True
                event_schedule["actions"] = []

                for instrument_type_action in instrument_type_event.data["actions"]:
                    action = {
                        "transaction_type": instrument_type_action["transaction_type"],
                        "text": instrument_type_action["text"],
                        "is_sent_to_pending": instrument_type_action[
                            "is_sent_to_pending"
                        ],
                        "is_book_automatic": instrument_type_action[
                            "is_book_automatic"
                        ],
                    }

                    event_schedule["actions"].append(action)

                self.instrument_object["event_schedules"].append(event_schedule)

            # Set Accruals

            self.instrument_object["accrual_calculation_schedules"] = []

            for instrument_type_accrual in self.instrument_type.accruals.all():
                accrual = {
                    item["key"]: item["default_value"]
                    for item in instrument_type_accrual.data["items"]
                    if "default_value" in item
                }
                self.instrument_object["accrual_calculation_schedules"].append(accrual)

            _l.info(
                f"InstrumentTypeProcess.fill_instrument_with_instrument_type_defaults instrument_object {self.instrument_object}"
            )

            _l.info(
                "InstrumentTypeProcess.fill_instrument_with_instrument_type_defaults %s seconds "
                % "{:3.3f}".format(time.time() - start_time)
            )

            return self.instrument_object

        except Exception as e:
            _l.info(
                f"set_defaults_from_instrument_type {repr(e)} {traceback.format_exc()}"
            )

            raise RuntimeError(
                f"InstrumentType is not configured correctly {repr(e)}"
            ) from e

    def set_pricing_policies(self):
        try:
            self.instrument_object["pricing_policies"] = []

            for it_pricing_policy in self.instrument_type.pricing_policies.all():
                pricing_policy = {
                    "pricing_policy_id": it_pricing_policy.pricing_policy.id,
                    "target_pricing_schema_user_code": it_pricing_policy.target_pricing_schema_user_code,
                    "options": it_pricing_policy.options,
                }

                self.instrument_object["pricing_policies"].append(pricing_policy)

        except Exception as e:
            _l.info(f"Can't set default pricing policy {e}")
