import copy
import csv
import json
import os
import re
import traceback
from logging import getLogger
from tempfile import NamedTemporaryFile

from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import now

from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string

from poms.accounts.models import AccountType
from poms.celery_tasks.models import CeleryTask
from poms.common import formula
from poms.common.models import ProxyRequest, ProxyUser
from poms.common.storage import get_storage
from poms.common.utils import get_serializer
from poms.counterparties.models import CounterpartyGroup, ResponsibleGroup
from poms.csv_import.models import (
    CsvImportScheme,
    ProcessType,
    SimpleImportConversionItem,
    SimpleImportImportedItem,
    SimpleImportProcessItem,
    SimpleImportProcessPreprocessItem,
    SimpleImportResult,
)
from poms.csv_import.serializers import SimpleImportResultSerializer
from poms.currencies.models import Currency
from poms.file_reports.models import FileReport
from poms.instruments.models import (
    AccrualCalculationModel,
    Country,
    DailyPricingModel,
    Instrument,
    InstrumentType,
    PaymentSizeDetail,
    Periodicity,
    PricingCondition,
    PricingPolicy,
)
from poms.obj_attrs.models import GenericAttributeType, GenericClassifier
from poms.procedures.models import RequestDataFileProcedureInstance
from poms.strategies.models import (
    Strategy1Subgroup,
    Strategy2Subgroup,
    Strategy3Subgroup,
)
from poms.system_messages.handlers import send_system_message
from poms.users.models import EcosystemDefault

storage = get_storage()

_l = getLogger("poms.csv_import")


## Probably DEPRECATED, Use InstrumentTypeProcess.fill_instrument_with_instrument_type_defaults
def set_defaults_from_instrument_type(
    instrument_object, instrument_type, ecosystem_default
):
    try:
        # Set system attributes

        if instrument_type.payment_size_detail_id:
            instrument_object[
                "payment_size_detail"
            ] = instrument_type.payment_size_detail_id
        else:
            instrument_object["payment_size_detail"] = None

        if instrument_type.accrued_currency_id:
            instrument_object["accrued_currency"] = instrument_type.accrued_currency_id
        else:
            instrument_object["accrued_currency"] = None

        instrument_object["price_multiplier"] = instrument_type.price_multiplier
        instrument_object["default_price"] = instrument_type.default_price
        instrument_object["maturity_date"] = instrument_type.maturity_date
        instrument_object["maturity_price"] = instrument_type.maturity_price

        instrument_object["accrued_multiplier"] = instrument_type.accrued_multiplier
        instrument_object["default_accrued"] = instrument_type.default_accrued

        if instrument_type.exposure_calculation_model_id:
            instrument_object[
                "exposure_calculation_model"
            ] = instrument_type.exposure_calculation_model_id
        else:
            instrument_object["exposure_calculation_model"] = None

        if instrument_type.pricing_condition_id:
            instrument_object[
                "pricing_condition"
            ] = instrument_type.pricing_condition_id
        else:
            instrument_object["pricing_condition"] = None

        try:
            instrument_object["long_underlying_instrument"] = Instrument.objects.get(
                master_user=instrument_type.master_user,
                user_code=instrument_type.long_underlying_instrument,
            ).pk
        except Exception as e:
            _l.info("Could not set long_underlying_instrument, fallback to default")
            instrument_object[
                "long_underlying_instrument"
            ] = ecosystem_default.instrument.pk

        instrument_object[
            "underlying_long_multiplier"
        ] = instrument_type.underlying_long_multiplier

        try:
            instrument_object["short_underlying_instrument"] = Instrument.objects.get(
                master_user=instrument_type.master_user,
                user_code=instrument_type.short_underlying_instrument,
            ).pk
        except Exception as e:
            _l.info("Could not set short_underlying_instrument, fallback to default")
            instrument_object[
                "short_underlying_instrument"
            ] = ecosystem_default.instrument.pk

        instrument_object[
            "underlying_short_multiplier"
        ] = instrument_type.underlying_short_multiplier

        instrument_object[
            "long_underlying_exposure"
        ] = instrument_type.long_underlying_exposure_id
        instrument_object[
            "short_underlying_exposure"
        ] = instrument_type.short_underlying_exposure_id

        try:
            instrument_object[
                "co_directional_exposure_currency"
            ] = Currency.objects.get(
                master_user=instrument_type.master_user,
                user_code=instrument_type.co_directional_exposure_currency,
            ).pk
        except Exception as e:
            _l.info(
                "Could not set co_directional_exposure_currency, fallback to default"
            )
            instrument_object[
                "co_directional_exposure_currency"
            ] = ecosystem_default.currency.pk

        try:
            instrument_object[
                "counter_directional_exposure_currency"
            ] = Currency.objects.get(
                master_user=instrument_type.master_user,
                user_code=instrument_type.counter_directional_exposure_currency,
            ).pk
        except Exception as e:
            _l.info(
                "Could not set counter_directional_exposure_currency, fallback to default"
            )
            instrument_object[
                "counter_directional_exposure_currency"
            ] = ecosystem_default.currency.pk

        # Set attributes
        instrument_object["attributes"] = []

        content_type = ContentType.objects.get(
            app_label="instruments", model="instrument"
        )

        for attribute in instrument_type.instrument_attributes.all():
            attribute_type = GenericAttributeType.objects.get(
                master_user=instrument_type.master_user,
                content_type=content_type,
                user_code=attribute.attribute_type_user_code,
            )

            attr = {"attribute_type": attribute_type.id}

            if attribute.value_type == 10:
                attr["value_string"] = attribute.value_string

            if attribute.value_type == 20:
                attr["value_float"] = attribute.value_float

            if attribute.value_type == 30:
                try:
                    item = GenericClassifier.objects.get(
                        attribute_type__user_code=attribute.attribute_type_user_code,
                        name=attribute.value_classifier,
                    )

                    attr["classifier"] = item.id
                    attr["classifier_object"] = {"id": item.id, "name": item.name}
                except Exception as e:
                    _l.info("Exception %s e " % e)

                    attr["classifier"] = None

            if attribute.value_type == 40:
                attr["value_date"] = attribute.value_date

            instrument_object["attributes"].append(attr)

        # Set Event Schedules

        instrument_object["event_schedules"] = []

        for instrument_type_event in instrument_type.events.all():
            event_schedule = {
                # 'name': instrument_type_event.name,
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
                action = {}
                action["transaction_type"] = instrument_type_action[
                    "transaction_type"
                ]  # TODO check if here user code instead of id
                action["text"] = instrument_type_action["text"]
                action["is_sent_to_pending"] = instrument_type_action[
                    "is_sent_to_pending"
                ]
                action["is_book_automatic"] = instrument_type_action[
                    "is_book_automatic"
                ]

                event_schedule["actions"].append(action)

            instrument_object["event_schedules"].append(event_schedule)

        # Set Accruals

        instrument_object["accrual_calculation_schedules"] = []

        for instrument_type_accrual in instrument_type.accruals.all():
            accrual = {}

            for item in instrument_type_accrual.data["items"]:
                # TODO add check for value type
                if "default_value" in item:
                    accrual[item["key"]] = item["default_value"]

            instrument_object["accrual_calculation_schedules"].append(accrual)

        # Set Pricing Policy

        try:
            instrument_object["pricing_policies"] = []

            for it_pricing_policy in instrument_type.pricing_policies.all():
                pricing_policy = {}

                pricing_policy["pricing_policy"] = it_pricing_policy.pricing_policy.id
                pricing_policy["pricing_scheme"] = it_pricing_policy.pricing_scheme.id
                pricing_policy["notes"] = it_pricing_policy.notes
                pricing_policy["default_value"] = it_pricing_policy.default_value
                pricing_policy["attribute_key"] = it_pricing_policy.attribute_key
                pricing_policy["json_data"] = it_pricing_policy.json_data

                instrument_object["pricing_policies"].append(pricing_policy)

        except Exception as e:
            _l.info("Can't set default pricing policy %s" % e)

        _l.info("instrument_object %s" % instrument_object)

        return instrument_object

    except Exception as e:
        _l.info("set_defaults_from_instrument_type e %s" % e)
        _l.info(traceback.format_exc())

        raise Exception("Instrument Type is not configured correctly %s" % e)


def set_events_for_instrument(instrument_object, data_object, instrument_type_obj):
    instrument_type = instrument_type_obj.user_code.lower()

    maturity = None

    if "maturity" in data_object:
        maturity = data_object["maturity"]

    if "maturity_date" in data_object:
        maturity = data_object["maturity_date"]

    if maturity:
        if instrument_type in {
            "bonds",
            "convertible_bonds",
            "index_linked_bonds",
            "short_term_notes",
        }:
            if len(instrument_object["event_schedules"]):
                # C
                coupon_event = instrument_object["event_schedules"][0]

                # coupon_event['periodicity'] = data_object['periodicity']

                if "first_coupon_date" in data_object:
                    coupon_event["effective_date"] = data_object["first_coupon_date"]

                coupon_event["final_date"] = maturity

                if len(instrument_object["event_schedules"]) == 2:
                    # M
                    expiration_event = instrument_object["event_schedules"][1]

                    expiration_event["effective_date"] = maturity
                    expiration_event["final_date"] = maturity

        if instrument_type in {
            "bond_futures",
            "fx_forwards",
            "forwards",
            "futures",
            "commodity_futures",
            "call_options",
            "etfs",
            "funds",
            "index_futures",
            "index_options",
            "put_options",
            "tbills",
            "warrants",
        }:
            # M
            expiration_event = instrument_object["event_schedules"][0]

            expiration_event["effective_date"] = maturity
            expiration_event["final_date"] = maturity


def set_accruals_for_instrument(instrument_object, data_object, instrument_type_obj):
    # instrument_type = data_object['instrument_type']

    instrument_type = instrument_type_obj.user_code.lower()

    if instrument_type == "bonds":
        if len(instrument_object["accrual_calculation_schedules"]):
            accrual = instrument_object["accrual_calculation_schedules"][0]

            accrual["effective_date"] = data_object["first_coupon_date"]
            accrual["accrual_end_date"] = data_object["maturity"]
            # accrual['accrual_size'] = data_object['accrual_size']
            # accrual['periodicity'] = data_object['periodicity']
            # accrual['periodicity_n'] = data_object['periodicity_n']


# Global method for create instrument object from Instrument Type Defaults
def handler_instrument_object(
    source_data, instrument_type, master_user, ecosystem_default, attribute_types
):
    object_data = {"instrument_type": instrument_type.id}
    # object_data = source_data.copy()

    set_defaults_from_instrument_type(object_data, instrument_type, ecosystem_default)

    _l.info("Settings defaults for instrument done")

    try:
        # TODO remove, when finmars.database.com will be deployed
        if isinstance(source_data["pricing_currency"], str):
            object_data["pricing_currency"] = Currency.objects.get(
                master_user=master_user,
                user_code=source_data["pricing_currency"],
            ).id
        else:
            object_data["pricing_currency"] = Currency.objects.get(
                master_user=master_user,
                user_code=source_data["pricing_currency"]["code"],
            ).id

    except Exception:
        object_data["pricing_currency"] = ecosystem_default.currency.id

    # try:
    #     object_data['accrued_currency'] = Currency.objects.get(master_user=master_user,
    #                                                            user_code=source_data['accrued_currency']).id
    # except Exception as e:
    #
    #     object_data['accrued_currency'] = ecosystem_default.currency.id

    object_data["public_name"] = source_data["name"]
    object_data["user_code"] = source_data["user_code"]
    object_data["name"] = source_data["name"]
    object_data["short_name"] = source_data["short_name"]

    object_data["accrued_currency"] = object_data["pricing_currency"]
    object_data["co_directional_exposure_currency"] = object_data["pricing_currency"]
    object_data["counter_directional_exposure_currency"] = object_data[
        "pricing_currency"
    ]

    try:
        object_data["payment_size_detail"] = PaymentSizeDetail.objects.get(
            user_code=source_data["payment_size_detail"]
        ).id
    except Exception as e:
        object_data["payment_size_detail"] = ecosystem_default.payment_size_detail.id

    # try:
    #     object_data['pricing_condition'] = PricingCondition.objects.get(
    #         user_code=source_data['pricing_condition']).id
    # except Exception as e:
    #
    #     object_data['pricing_condition'] = ecosystem_default.pricing_condition.id

    if "maturity_price" in source_data:
        try:
            object_data["maturity_price"] = float(source_data["maturity_price"])
        except Exception as e:
            _l.warning(f"Could not set maturity price {repr(e)}")

    if "maturity" in source_data and source_data["maturity"] != "":
        object_data["maturity_date"] = source_data["maturity"]

    elif "maturity_date" in source_data and source_data["maturity_date"] != "":
        if (
            source_data["maturity_date"] == "null"
            or source_data["maturity_date"] == "9999-00-00"
        ):
            object_data["maturity_date"] = "2999-01-01"
        else:
            object_data["maturity_date"] = source_data["maturity_date"]
    else:
        object_data["maturity_date"] = "2999-01-01"

    try:
        if "country" in source_data:
            country = Country.objects.get(alpha_2=source_data["country"]["code"])

            object_data["country"] = country.id

    except Exception as e:
        _l.error(f"Could not set country {repr(e)}")

    try:
        if "sector" in source_data:
            sector_attribute = GenericAttributeType.objects.get(user_code="sector")

            attribute = {}
            exist = False

            for attribute in object_data["attributes"]:
                if attribute["attribute_type"] == sector_attribute.id:
                    exist = True
                    attribute["value_string"] = source_data["sector"]

            if not exist:
                attribute["attribute_type"] = sector_attribute.id
                attribute["value_string"] = source_data["sector"]

                object_data["attributes"].append(attribute)

    except Exception as e:
        _l.error("Could not set sector")

    # object_data['attributes'] = []

    _l.info(
        "Settings attributes for instrument done attribute_types %s " % attribute_types
    )

    _tmp_attributes_dict = {}

    for item in object_data["attributes"]:
        _tmp_attributes_dict[item["attribute_type"]] = item

    try:
        if "attributes" in source_data:
            if isinstance(source_data["attributes"], dict):
                for attribute_type in attribute_types:
                    lower_user_code = attribute_type.user_code.lower()

                    for key, value in source_data["attributes"].items():
                        _l_key = key.lower()

                        if _l_key == lower_user_code:
                            attribute = {
                                "attribute_type": attribute_type.id,
                            }

                            if attribute_type.value_type == 10:
                                attribute["value_string"] = value

                            if attribute_type.value_type == 20:
                                attribute["value_float"] = value

                            if attribute_type.value_type == 30:
                                try:
                                    classifier = GenericClassifier.objects.get(
                                        attribute_type=attribute_type, name=value
                                    )

                                    attribute["classifier"] = classifier.id

                                except Exception as e:
                                    attribute["classifier"] = None

                            if attribute_type.value_type == 40:
                                attribute["value_date"] = value

                            _tmp_attributes_dict[
                                attribute["attribute_type"]
                            ] = attribute
    except Exception as e:
        _l.error("Could not set attributes from finmars database. Error %s" % e)
        _l.error(
            "Could not set attributes from finmars database. Traceback %s"
            % traceback.format_exc()
        )

    object_data["attributes"] = []

    _l.info("_tmp_attributes_dict %s" % _tmp_attributes_dict)

    for key, value in _tmp_attributes_dict.items():
        object_data["attributes"].append(value)

    _l.info("Settings attributes for instrument done object_data %s " % object_data)

    object_data["master_user"] = master_user.id
    object_data["manual_pricing_formulas"] = []
    # object_data['accrual_calculation_schedules'] = []
    # object_data['event_schedules'] = []
    object_data["factor_schedules"] = []

    set_events_for_instrument(object_data, source_data, instrument_type)
    _l.info("Settings events for instrument done")

    # _l.info('source_data %s' % source_data)

    if "accrual_calculation_schedules" in source_data:
        if source_data["accrual_calculation_schedules"]:
            if len(source_data["accrual_calculation_schedules"]):
                if len(object_data["event_schedules"]):
                    # C
                    coupon_event = object_data["event_schedules"][0]

                    if (
                        "first_payment_date"
                        in source_data["accrual_calculation_schedules"][0]
                    ):
                        coupon_event["effective_date"] = source_data[
                            "accrual_calculation_schedules"
                        ][0]["first_payment_date"]

    accrual_map = {
        "Actual/Actual (ICMA)": AccrualCalculationModel.ACT_ACT,
        "Actual/Actual (ISDA)": AccrualCalculationModel.ACT_ACT_ISDA,
        "Actual/360": AccrualCalculationModel.ACT_360,
        "Actual/364": AccrualCalculationModel.ACT_365,
        "Actual/365 (Actual/365F)": AccrualCalculationModel.ACT_365,
        "Actual/366": AccrualCalculationModel.ACT_365_366,
        "Actual/365L": AccrualCalculationModel.ACT_365_366,
        "Actual/365A": AccrualCalculationModel.ACT_1_365,
        "30/360 US": AccrualCalculationModel.C_30_360,
        "30E+/360": AccrualCalculationModel.C_30E_P_360,
        "NL/365": AccrualCalculationModel.NL_365,
        "BD/252": AccrualCalculationModel.BUS_DAYS_252,
        "30E/360": AccrualCalculationModel.GERMAN_30_360_EOM,
        "30/360 (30/360 ISDA)": AccrualCalculationModel.GERMAN_30_360_EOM,
        "30/360 German": AccrualCalculationModel.GERMAN_30_360_NO_EOM,
    }

    if "accrual_calculation_schedules" in source_data:
        if source_data["accrual_calculation_schedules"]:
            if len(source_data["accrual_calculation_schedules"]):
                _l.info("Setting up accrual schedules. Init")

                if len(object_data["accrual_calculation_schedules"]):
                    _l.info("Setting up accrual schedules. Overwrite Existing")

                    accrual = object_data["accrual_calculation_schedules"][0]

                    if "day_count_convention" in source_data:
                        if source_data["day_count_convention"] in accrual_map:
                            accrual["accrual_calculation_model"] = accrual_map[
                                source_data["day_count_convention"]
                            ]

                        else:
                            accrual[
                                "accrual_calculation_model"
                            ] = AccrualCalculationModel.DEFAULT

                    if (
                        "accrual_start_date"
                        in source_data["accrual_calculation_schedules"][0]
                    ):
                        accrual["accrual_start_date"] = source_data[
                            "accrual_calculation_schedules"
                        ][0]["accrual_start_date"]

                    if (
                        "first_payment_date"
                        in source_data["accrual_calculation_schedules"][0]
                    ):
                        accrual["first_payment_date"] = source_data[
                            "accrual_calculation_schedules"
                        ][0]["first_payment_date"]

                    try:
                        accrual["accrual_size"] = float(
                            source_data["accrual_calculation_schedules"][0][
                                "accrual_size"
                            ]
                        )
                    except Exception as e:
                        accrual["accrual_size"] = 0

                    try:
                        accrual["periodicity_n"] = int(
                            source_data["accrual_calculation_schedules"][0][
                                "periodicity_n"
                            ]
                        )

                        if accrual["periodicity_n"] == 1:
                            accrual["periodicity"] = Periodicity.ANNUALLY

                        if accrual["periodicity_n"] == 2:
                            accrual["periodicity"] = Periodicity.SEMI_ANNUALLY

                        if accrual["periodicity_n"] == 4:
                            accrual["periodicity"] = Periodicity.QUARTERLY

                        if accrual["periodicity_n"] == 6:
                            accrual["periodicity"] = Periodicity.BIMONTHLY

                        if accrual["periodicity_n"] == 12:
                            accrual["periodicity"] = Periodicity.MONTHLY

                        _l.info("periodicity %s" % accrual["periodicity"])

                        accrual["periodicity_n"] = 0

                    except Exception as e:
                        accrual["periodicity_n"] = 0

                else:
                    _l.info("Setting up accrual schedules. Creating new")

                    accrual = {}

                    accrual[
                        "accrual_calculation_model"
                    ] = AccrualCalculationModel.ACT_365
                    accrual["periodicity"] = Periodicity.ANNUALLY

                    if (
                        "accrual_start_date"
                        in source_data["accrual_calculation_schedules"][0]
                    ):
                        accrual["accrual_start_date"] = source_data[
                            "accrual_calculation_schedules"
                        ][0]["accrual_start_date"]

                    if (
                        "first_payment_date"
                        in source_data["accrual_calculation_schedules"][0]
                    ):
                        accrual["first_payment_date"] = source_data[
                            "accrual_calculation_schedules"
                        ][0]["first_payment_date"]

                    try:
                        accrual["accrual_size"] = float(
                            source_data["accrual_calculation_schedules"][0][
                                "accrual_size"
                            ]
                        )
                    except Exception:
                        accrual["accrual_size"] = 0

                    try:
                        accrual["periodicity_n"] = int(
                            source_data["accrual_calculation_schedules"][0][
                                "periodicity_n"
                            ]
                        )

                        if accrual["periodicity_n"] == 1:
                            accrual["periodicity"] = Periodicity.ANNUALLY

                        if accrual["periodicity_n"] == 2:
                            accrual["periodicity"] = Periodicity.SEMI_ANNUALLY

                        if accrual["periodicity_n"] == 4:
                            accrual["periodicity"] = Periodicity.QUARTERLY

                        if accrual["periodicity_n"] == 6:
                            accrual["periodicity"] = Periodicity.BIMONTHLY

                        if accrual["periodicity_n"] == 12:
                            accrual["periodicity"] = Periodicity.MONTHLY

                        _l.info("periodicity %s" % accrual["periodicity"])

                    except Exception as e:
                        accrual["periodicity_n"] = 0

                    object_data["accrual_calculation_schedules"].append(accrual)
    else:
        set_accruals_for_instrument(object_data, source_data, instrument_type)

    if "name" not in object_data and "user_code" in object_data:
        object_data["name"] = object_data["user_code"]

    if "short_name" not in object_data and "user_code" in object_data:
        object_data["short_name"] = object_data["user_code"]

    return object_data


class SimpleImportProcess(object):
    def __init__(self, task_id, procedure_instance_id=None):
        self.task = CeleryTask.objects.get(pk=task_id)
        self.parent_task = self.task.parent

        _l.info("SimpleImportProcess.Task %s. init" % self.task)

        self.task.status = CeleryTask.STATUS_PENDING
        self.task.save()

        self.procedure_instance = None
        if procedure_instance_id:
            self.procedure_instance = RequestDataFileProcedureInstance.objects.get(
                id=procedure_instance_id
            )

            _l.info(
                "SimpleImportProcess.Task %s. init procedure_instance %s"
                % (self.task, self.procedure_instance)
            )

        self.master_user = self.task.master_user
        self.member = self.task.member

        self.proxy_user = ProxyUser(self.member, self.master_user)
        self.proxy_request = ProxyRequest(self.proxy_user)

        if self.task.options_object.get("scheme_id", None):
            self.scheme = CsvImportScheme.objects.get(
                pk=self.task.options_object["scheme_id"]
            )
        elif self.task.options_object.get("scheme_user_code", None):
            self.scheme = CsvImportScheme.objects.get(
                user_code=self.task.options_object["scheme_user_code"]
            )
        else:
            raise Exception("Import Scheme not found")

        self.execution_context = self.task.options_object["execution_context"]
        self.file_path = self.task.options_object["file_path"]
        # self.preprocess_file = self.task.options_object['preprocess_file']

        self.ecosystem_default = EcosystemDefault.objects.get(
            master_user=self.master_user
        )

        self.result = SimpleImportResult()
        self.result.task = self.task
        self.result.scheme = self.scheme

        self.process_type = ProcessType.CSV

        self.find_process_type()
        self.get_attribute_types()

        self.file_items = []  # items from provider  (json, csv, excel)
        self.raw_items = []  # items from provider  (json, csv, excel)
        self.conversion_items = []  # items with applied converions
        self.preprocessed_items = []  # items with calculated variables applied
        self.items = []  # result items that will be passed to TransactionTypeProcess

        self.context = {
            "master_user": self.master_user,
            "member": self.member,
            "request": self.proxy_request,
        }

        import_system_message_performed_by = self.member.username
        import_system_message_title = "Simple import (start)"

        if (
            self.execution_context
            and self.execution_context["started_by"] == "procedure"
        ):
            import_system_message_performed_by = "System"
            import_system_message_title = "Simple import from broker (start)"

        send_system_message(
            master_user=self.master_user,
            performed_by=import_system_message_performed_by,
            section="import",
            type="success",
            title=import_system_message_title,
            description=self.member.username
            + " started import with scheme "
            + self.scheme.name,
        )

    def generate_file_report(self):
        _l.info(
            "SimpleImportProcess.generate_file_report error_handler %s"
            % self.scheme.error_handler
        )
        _l.info(
            "SimpleImportProcess.generate_file_report missing_data_handler %s"
            % self.scheme.missing_data_handler
        )

        result = []

        result.append("Type, Simple Import")
        result.append("Scheme, " + self.scheme.user_code)
        result.append("Error handle, " + self.scheme.error_handler)

        if self.result.file_name:
            result.append("Filename, " + self.result.file_name)

        result.append(
            "Import Rules - if object is not found, " + self.scheme.missing_data_handler
        )

        success_rows_count = 0
        error_rows_count = 0
        skip_rows_count = 0

        for result_item in self.result.items:
            if result_item.status == "error":
                error_rows_count = error_rows_count + 1

            if result_item.status == "success":
                success_rows_count = success_rows_count + 1

            if "skip" in result_item.status:
                skip_rows_count = skip_rows_count + 1

        result.append("Rows total, %s" % self.result.total_rows)
        result.append("Rows success import, %s" % success_rows_count)
        result.append("Rows fail import, %s" % error_rows_count)
        result.append("Rows skipped import, %s" % skip_rows_count)

        columns = ["Row Number", "Status", "Message"]

        column_row_list = []

        for item in columns:
            column_row_list.append('"' + str(item) + '"')

        column_row = ",".join(column_row_list)

        result.append(column_row)

        for result_item in self.result.items:
            content = []

            content.append(str(result_item.row_number))
            content.append(result_item.status)

            if result_item.error_message:
                content.append(result_item.error_message)
            elif result_item.message:
                content.append(result_item.message)
            else:
                content.append("")

            content_row_list = []

            for item in content:
                content_row_list.append('"' + str(item) + '"')

            content_row = ",".join(content_row_list)

            result.append(content_row)

        result = "\n".join(result)

        current_date_time = now().strftime("%Y-%m-%d-%H-%M")

        file_name = "file_report_%s_task_%s.csv" % (current_date_time, self.task.id)

        file_report = FileReport()

        _l.info("SimpleImportProcess.generate_file_report uploading file")

        file_report.upload_file(
            file_name=file_name, text=result, master_user=self.master_user
        )
        file_report.master_user = self.master_user
        file_report.name = "Simple Import %s (Task %s).csv" % (
            current_date_time,
            self.task.id,
        )
        file_report.file_name = file_name
        file_report.type = "simple_import.import"
        file_report.notes = "System File"
        file_report.content_type = "text/csv"

        file_report.save()

        _l.info("SimpleImportProcess.file_report %s" % file_report)
        _l.info("SimpleImportProcess.file_report %s" % file_report.file_url)

        return file_report

    def generate_json_report(self):
        serializer = SimpleImportResultSerializer(
            instance=self.result, context=self.context
        )

        result = serializer.data

        # _l.debug('self.result %s' % self.result.__dict__)

        # _l.debug('generate_json_report.result %s' % result)

        current_date_time = now().strftime("%Y-%m-%d-%H-%M")
        file_name = "file_report_%s_task_%s.json" % (current_date_time, self.task.id)

        file_report = FileReport()

        _l.info("SimplemportProcess.generate_json_report uploading file")

        file_report.upload_file(
            file_name=file_name,
            text=json.dumps(result, indent=4, default=str),
            master_user=self.master_user,
        )
        file_report.master_user = self.master_user
        file_report.name = "Simple Import %s (Task %s).json" % (
            current_date_time,
            self.task.id,
        )
        file_report.file_name = file_name
        file_report.type = "simple_import.import"
        file_report.notes = "System File"
        file_report.content_type = "application/json"

        file_report.save()

        _l.info("SimpleImportProcess.json_report %s" % file_report)
        _l.info("SimpleImportProcess.json_report %s" % file_report.file_url)

        return file_report

    def get_attribute_types(self):
        attribute_types = []

        try:
            attribute_types = GenericAttributeType.objects.filter(
                master_user=self.master_user, content_type=self.scheme.content_type
            )

        except Exception as e:
            _l.error("Get attribute types excpetion %s" % e)

        self.attribute_types = attribute_types

    def find_process_type(self):
        if self.task.options_object and "items" in self.task.options_object:
            self.process_type = ProcessType.JSON
        elif ".json" in self.file_path:
            self.process_type = ProcessType.JSON
        elif ".xlsx" in self.file_path:
            self.process_type = ProcessType.EXCEL
        elif ".csv" in self.file_path:
            self.process_type = ProcessType.CSV

        _l.info(
            "SimpleImportProcess.Task %s. process_type %s"
            % (self.task, self.process_type)
        )

    def get_verbose_result(self):
        imported_count = 0
        error_count = 0

        for item in self.result.items:
            if item.status == "error":
                error_count = error_count + 1
            else:
                imported_count = imported_count + 1

        result = (
            "Processed %s rows and successfully imported %s items. Error rows %s"
            % (len(self.items), imported_count, error_count)
        )

        return result

    def fill_with_file_items(self):
        _l.info(
            "SimpleImportProcess.Task %s. fill_with_raw_items INIT %s"
            % (self.task, self.process_type)
        )

        try:
            if self.process_type == ProcessType.JSON:
                try:
                    _l.info("Trying to get json items from task object options")
                    items = self.task.options_object["items"]

                    self.result.total_rows = len(items)

                    self.file_items = items

                except Exception as e:
                    _l.info("Trying to get json items from file")

                    with storage.open(self.file_path, "rb") as f:
                        self.file_items = json.loads(f.read())

            if self.process_type == ProcessType.CSV:
                _l.info("ProcessType.CSV self.file_path %s" % self.file_path)

                with storage.open(self.file_path, "rb") as f:
                    with NamedTemporaryFile() as tmpf:
                        for chunk in f.chunks():
                            tmpf.write(chunk)
                        tmpf.flush()

                        # TODO check encoding (maybe should be taken from scheme)
                        with open(
                            tmpf.name, mode="rt", encoding="utf_8_sig", errors="ignore"
                        ) as cf:
                            # TODO check quotechar (maybe should be taken from scheme)
                            reader = csv.reader(
                                cf,
                                delimiter=self.scheme.delimiter,
                                quotechar='"',
                                strict=False,
                                skipinitialspace=True,
                            )

                            column_row = None

                            for row_index, row in enumerate(reader):
                                if row_index == 0:
                                    column_row = row

                                else:
                                    file_item = {}

                                    for column_index, value in enumerate(row):
                                        key = column_row[column_index]
                                        file_item[key] = value

                                    self.file_items.append(file_item)

                            self.result.total_rows = len(self.file_items)

            if self.process_type == ProcessType.EXCEL:
                with storage.open(self.file_path, "rb") as f:
                    with NamedTemporaryFile() as tmpf:
                        for chunk in f.chunks():
                            tmpf.write(chunk)
                        tmpf.flush()

                        os.link(tmpf.name, tmpf.name + ".xlsx")

                        _l.info("self.file_path %s" % self.file_path)
                        _l.info("tmpf.name %s" % tmpf.name)

                        wb = load_workbook(filename=tmpf.name + ".xlsx")

                        if (
                            self.scheme.spreadsheet_active_tab_name
                            and self.scheme.spreadsheet_active_tab_name in wb.sheetnames
                        ):
                            ws = wb[self.scheme.spreadsheet_active_tab_name]
                        else:
                            ws = wb.active

                        reader = []

                        if self.scheme.spreadsheet_start_cell == "A1":
                            for r in ws.rows:
                                reader.append([cell.value for cell in r])

                        else:
                            start_cell_row_number = int(
                                re.search(r"\d+", self.scheme.spreadsheet_start_cell)[0]
                            )
                            start_cell_letter = (
                                self.scheme.spreadsheet_start_cell.split(
                                    str(start_cell_row_number)
                                )[0]
                            )

                            start_cell_column_number = column_index_from_string(
                                start_cell_letter
                            )

                            row_number = 1

                            for r in ws.rows:
                                row_values = []

                                if row_number >= start_cell_row_number:
                                    for cell in r:
                                        if cell.column >= start_cell_column_number:
                                            row_values.append(cell.value)

                                    reader.append(row_values)

                                row_number = row_number + 1

                        column_row = None

                        for row_index, row in enumerate(reader):
                            if row_index == 0:
                                column_row = row

                            else:
                                file_item = {}

                                for column_index, value in enumerate(row):
                                    key = column_row[column_index]
                                    file_item[key] = value

                                self.file_items.append(file_item)

                        self.result.total_rows = len(self.file_items)

            _l.info(
                "SimpleImportProcess.Task %s. fill_with_raw_items %s DONE items %s"
                % (self.task, self.process_type, len(self.raw_items))
            )

        except Exception as e:
            _l.error(
                "SimpleImportProcess.Task %s. fill_with_raw_items %s Exception %s"
                % (self.task, self.process_type, e)
            )
            _l.error(
                "SimpleImportProcess.Task %s. fill_with_raw_items %s Traceback %s"
                % (self.task, self.process_type, traceback.format_exc())
            )

    def whole_file_preprocess(self):
        if self.scheme.data_preprocess_expression:
            names = {}

            names["data"] = self.file_items

            try:
                # _l.info("whole_file_preprocess  names %s" % names)

                self.file_items = formula.safe_eval(
                    self.scheme.data_preprocess_expression,
                    names=names,
                    context=self.context,
                )

                # _l.info("whole_file_preprocess  self.raw_items %s" % self.raw_items)

            except Exception as e:
                _l.error("Could not execute preoprocess expression. Error %s" % e)

        _l.info("whole_file_preprocess.file_items %s" % len(self.file_items))

        return self.file_items

    def fill_with_raw_items(self):
        _l.info(
            "SimpleImportProcess.Task %s. fill_with_raw_items INIT %s"
            % (self.task, self.process_type)
        )

        try:
            for file_item in self.file_items:
                item = {}

                for scheme_input in self.scheme.csv_fields.all():
                    try:
                        item[scheme_input.name] = file_item[scheme_input.column_name]
                    except Exception as e:
                        item[scheme_input.name] = None

                self.raw_items.append(item)
            _l.info(
                "SimpleImportProcess.Task %s. fill_with_raw_items %s DONE items %s"
                % (self.task, self.process_type, len(self.raw_items))
            )

        except Exception as e:
            _l.error(
                "SimpleImportProcess.Task %s. fill_with_raw_items %s Exception %s"
                % (self.task, self.process_type, e)
            )
            _l.error(
                "SimpleImportProcess.Task %s. fill_with_raw_items %s Traceback %s"
                % (self.task, self.process_type, traceback.format_exc())
            )

    def apply_conversion_to_raw_items(self):
        # EXECUTE CONVERSIONS ON SCHEME INPUTS

        row_number = 1
        for raw_item in self.raw_items:
            conversion_item = SimpleImportConversionItem()
            conversion_item.file_inputs = self.file_items[row_number - 1]
            conversion_item.raw_inputs = raw_item
            conversion_item.conversion_inputs = {}
            conversion_item.row_number = row_number

            for scheme_input in self.scheme.csv_fields.all():
                try:
                    names = raw_item

                    conversion_item.conversion_inputs[
                        scheme_input.name
                    ] = formula.safe_eval(
                        scheme_input.name_expr,
                        names=names,
                        context={
                            "master_user": self.master_user,
                            "member": self.member,
                        },
                    )
                except Exception as e:
                    conversion_item.conversion_inputs[scheme_input.name] = None

            self.conversion_items.append(conversion_item)

            row_number = row_number + 1

    # We have formulas that lookup for rows
    # e.g. transaction_import.find_row
    # so it means, in first iterations we will got errors in that inputs
    def recursive_preprocess(self, deep=1, current_level=0):
        if len(self.preprocessed_items) == 0:
            row_number = 1

            for conversion_item in self.conversion_items:
                preprocess_item = SimpleImportProcessPreprocessItem()
                preprocess_item.file_inputs = conversion_item.file_inputs
                preprocess_item.raw_inputs = conversion_item.raw_inputs
                preprocess_item.conversion_inputs = conversion_item.conversion_inputs
                preprocess_item.row_number = row_number
                preprocess_item.inputs = {}

                self.preprocessed_items.append(preprocess_item)

                row_number = row_number + 1

        for preprocess_item in self.preprocessed_items:
            # CREATE SCHEME INPUTS

            for scheme_input in self.scheme.csv_fields.all():
                key_column_name = scheme_input.column_name

                try:
                    preprocess_item.inputs[
                        scheme_input.name
                    ] = preprocess_item.conversion_inputs[scheme_input.name]

                except Exception as e:
                    preprocess_item.inputs[scheme_input.name] = None

                    if current_level == deep:
                        _l.error("key_column_name %s" % key_column_name)
                        _l.error("scheme_input.name %s" % scheme_input.name)
                        _l.error(
                            "preprocess_item.raw_inputs %s"
                            % preprocess_item.conversion_inputs
                        )
                        _l.error(
                            "SimpleImportProcess.Task %s. recursive_preprocess init input %s Exception %s"
                            % (self.task, scheme_input, e)
                        )

            # CREATE CALCULATED INPUTS

            for scheme_calculated_input in self.scheme.calculated_inputs.all():
                try:
                    names = preprocess_item.inputs

                    value = formula.safe_eval(
                        scheme_calculated_input.name_expr,
                        names=names,
                        context={
                            "master_user": self.master_user,
                            "member": self.member,
                            "transaction_import": {"items": self.preprocessed_items},
                        },
                    )

                    preprocess_item.inputs[scheme_calculated_input.name] = value

                except Exception as e:
                    preprocess_item.inputs[scheme_calculated_input.name] = None

                    if current_level == deep:
                        _l.error(
                            "SimpleImportProcess.Task %s. recursive_preprocess calculated_input %s Exception %s"
                            % (self.task, scheme_calculated_input, e)
                        )
                        # _l.error(
                        #     'TransactionImportProcess.Task %s. recursive_preprocess calculated_input %s Traceback %s' % (
                        #         self.task, scheme_calculated_input, traceback.format_exc()))

        if current_level < deep:
            self.recursive_preprocess(deep, current_level + 1)

    def preprocess(self):
        _l.info("SimpleImportProcess.Task %s. preprocess INIT" % self.task)

        self.recursive_preprocess(deep=2)

        for preprocessed_item in self.preprocessed_items:
            item = SimpleImportProcessItem()
            item.row_number = preprocessed_item.row_number
            item.file_inputs = preprocessed_item.file_inputs
            item.raw_inputs = preprocessed_item.raw_inputs
            item.conversion_inputs = preprocessed_item.conversion_inputs
            item.inputs = preprocessed_item.inputs

            self.items.append(item)

        _l.info(
            "SimpleImportProcess.Task %s. preprocess DONE items %s"
            % (self.task, len(self.preprocessed_items))
        )

    def fill_result_item_with_attributes(self, item):
        result = []

        for attribute_type in self.attribute_types:
            for entity_field in self.scheme.entity_fields.all():
                if entity_field.attribute_user_code:
                    if entity_field.attribute_user_code == attribute_type.user_code:
                        attribute = {"attribute_type": attribute_type.id}

                        if attribute_type.value_type == GenericAttributeType.STRING:
                            if item.final_inputs[entity_field.attribute_user_code]:
                                attribute["value_string"] = item.final_inputs[
                                    entity_field.attribute_user_code
                                ]

                        if attribute_type.value_type == GenericAttributeType.NUMBER:
                            if item.final_inputs[entity_field.attribute_user_code]:
                                attribute["value_float"] = item.final_inputs[
                                    entity_field.attribute_user_code
                                ]

                        if attribute_type.value_type == GenericAttributeType.CLASSIFIER:
                            if item.final_inputs[entity_field.attribute_user_code]:
                                try:
                                    attribute[
                                        "classifier"
                                    ] = GenericClassifier.objects.get(
                                        attribute_type=attribute_type,
                                        name=item.final_inputs[
                                            entity_field.attribute_user_code
                                        ],
                                    ).id
                                except Exception as e:
                                    _l.error(
                                        "fill_result_item_with_attributes classifier error - item %s e %s"
                                        % (item, e)
                                    )

                                    if not item.error_message:
                                        item.error_message = ""

                                    item.error_message = (
                                        item.error_message + "%s: %s, "
                                    ) % (entity_field.attribute_user_code, str(e))

                                    attribute["classifier"] = None

                        if attribute_type.value_type == GenericAttributeType.DATE:
                            if item.final_inputs[entity_field.attribute_user_code]:
                                attribute["value_date"] = item.final_inputs[
                                    entity_field.attribute_user_code
                                ]

                        result.append(attribute)

        return result

    def overwrite_item_attributes(self, result_item, item):
        result = []

        for attribute in result_item["attributes"]:
            for entity_field in self.scheme.entity_fields.all():
                if entity_field.attribute_user_code:
                    if (
                        entity_field.attribute_user_code
                        == attribute["attribute_type_object"]["user_code"]
                    ):
                        if (
                            attribute["attribute_type_object"]["value_type"]
                            == GenericAttributeType.STRING
                        ):
                            if item.final_inputs[entity_field.attribute_user_code]:
                                attribute["value_string"] = item.final_inputs[
                                    entity_field.attribute_user_code
                                ]

                        if (
                            attribute["attribute_type_object"]["value_type"]
                            == GenericAttributeType.NUMBER
                        ):
                            if item.final_inputs[entity_field.attribute_user_code]:
                                attribute["value_float"] = item.final_inputs[
                                    entity_field.attribute_user_code
                                ]

                        if (
                            attribute["attribute_type_object"]["value_type"]
                            == GenericAttributeType.CLASSIFIER
                        ):
                            if item.final_inputs[entity_field.attribute_user_code]:
                                try:
                                    attribute[
                                        "classifier"
                                    ] = GenericClassifier.objects.get(
                                        attribute_type_id=attribute[
                                            "attribute_type_object"
                                        ]["id"],
                                        name=item.final_inputs[
                                            entity_field.attribute_user_code
                                        ],
                                    ).id
                                except Exception as e:
                                    _l.error(
                                        "fill_result_item_with_attributes classifier error - item %s e %s"
                                        % (item, e)
                                    )

                                    if not item.error_message:
                                        item.error_message = ""

                                    item.error_message = (
                                        item.error_message + "%s: %s, "
                                    ) % (entity_field.attribute_user_code, str(e))

                                    attribute["classifier"] = None

                        if (
                            attribute["attribute_type_object"]["value_type"]
                            == GenericAttributeType.DATE
                        ):
                            if item.final_inputs[entity_field.attribute_user_code]:
                                attribute["value_date"] = item.final_inputs[
                                    entity_field.attribute_user_code
                                ]

        return result

    def convert_relation_to_ids(self, item, result_item):
        relation_fields_map = {
            "instrument": Instrument,
            "currency": Currency,
            "pricing_currency": Currency,
            "accrued_currency": Currency,
            "type": AccountType,
            "pricing_condition": PricingCondition,
            "instrument_type": InstrumentType,
            "country": Country,
            "pricing_policy": PricingPolicy,
            "payment_size_detail": PaymentSizeDetail,
            "co_directional_exposure_currency": Currency,
            "counter_directional_exposure_currency": Currency,
            "daily_pricing_model": DailyPricingModel,
        }

        if self.scheme.content_type.model == "counterparty":
            relation_fields_map["group"] = CounterpartyGroup

        if self.scheme.content_type.model == "responsible":
            relation_fields_map["group"] = ResponsibleGroup

        if self.scheme.content_type.model == "strategy1":
            relation_fields_map["subgroup"] = Strategy1Subgroup

        if self.scheme.content_type.model == "strategy2":
            relation_fields_map["subgroup"] = Strategy2Subgroup

        if self.scheme.content_type.model == "strategy3":
            relation_fields_map["subgroup"] = Strategy3Subgroup

        for entity_field in self.scheme.entity_fields.all():
            key = entity_field.system_property_key

            if key in relation_fields_map:
                if isinstance(result_item[key], str):
                    try:
                        result_item[key] = (
                            relation_fields_map[key]
                            .objects.get(user_code=result_item[key])
                            .id
                        )
                    except Exception as e:
                        result_item[key] = None

                        if not item.error_message:
                            item.error_message = ""

                        item.error_message = (item.error_message + "%s: %s, ") % (
                            key,
                            str(e),
                        )

        # _l.info('convert_relation_to_ids.result_item %s' % result_item)

        return result_item

    def remove_nullable_attributes(self, result_item):
        for key, value in list(result_item.items()):
            if value == None:
                result_item.pop(key)

        return result_item

    def get_final_inputs(self, item):
        result = {}

        for entity_field in self.scheme.entity_fields.all():
            if entity_field.expression:
                try:
                    value = formula.safe_eval(
                        entity_field.expression, names=item.inputs, context=self.context
                    )

                    if entity_field.system_property_key:
                        result[entity_field.system_property_key] = value

                    elif entity_field.attribute_user_code:
                        result[entity_field.attribute_user_code] = value

                except Exception as e:
                    _l.error("get_final_inputs.e %s" % e)

                    if not item.error_message:
                        item.error_message = ""

                    if entity_field.system_property_key:
                        item.error_message = (item.error_message + "%s: %s, ") % (
                            entity_field.system_property_key,
                            str(e),
                        )

                        result[entity_field.system_property_key] = None

                    elif entity_field.attribute_user_code:
                        item.error_message = (item.error_message + "%s: %s, ") % (
                            entity_field.attribute_user_code,
                            str(e),
                        )

                        result[entity_field.attribute_user_code] = None

            else:
                if entity_field.system_property_key:
                    result[entity_field.system_property_key] = None

                elif entity_field.attribute_user_code:
                    result[entity_field.attribute_user_code] = None

        return result

    def import_item(self, item):
        content_type_key = (
            self.scheme.content_type.app_label + "." + self.scheme.content_type.model
        )

        serializer_class = get_serializer(content_type_key)

        if not item.imported_items:
            item.imported_items = []

        try:
            item.final_inputs = self.get_final_inputs(item)

            result_item = {}

            if self.scheme.content_type.model == "instrument":
                from poms.instruments.handlers import InstrumentTypeProcess

                instrument_type = InstrumentType.objects.get(
                    user_code=item.final_inputs["instrument_type"]
                )

                process = InstrumentTypeProcess(instrument_type=instrument_type)

                default_instrument_object = process.instrument

                default_instrument_object.update(result_item)

                result_item = default_instrument_object

            for key, value in item.final_inputs.items():
                if item.final_inputs[key] is not None:
                    result_item[key] = item.final_inputs[key]

            # TODO do not overwrite existing values from Instrument Type for Instrument
            result_item["attributes"] = self.fill_result_item_with_attributes(item)
            result_item = self.convert_relation_to_ids(item, result_item)
            result_item = self.remove_nullable_attributes(result_item)

            # _l.info('result_item %s' % result_item)

            serializer = serializer_class(data=result_item, context=self.context)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            if self.scheme.item_post_process_script:
                # POST SUCCESS SCRIPT

                try:
                    formula.safe_eval(
                        self.scheme.item_post_process_script,
                        names=item.inputs,
                        context=self.context,
                    )

                except Exception as e:
                    if not item.error_message:
                        item.error_message = ""

                    item.error_message = (
                        item.error_message + "Post script error: %s, "
                    ) % str(e)

            item.status = "success"
            item.message = "Item Imported %s" % serializer.instance

            trn = SimpleImportImportedItem(
                id=serializer.instance.id, user_code=str(serializer.instance)
            )

            item.imported_items.append(trn)

        except Exception as e:
            # _l.error('import_item e %s' % e)
            # _l.error('import_item traceback %s' % traceback.format_exc())

            if self.scheme.mode == "overwrite":
                try:
                    model = self.scheme.content_type.model_class()

                    if self.scheme.content_type.model in ["pricehistory"]:
                        instance = model.objects.get(
                            instrument__user_code=item.final_inputs["instrument"],
                            pricing_policy__user_code=item.final_inputs[
                                "pricing_policy"
                            ],
                            date=item.final_inputs["date"],
                        )
                    elif self.scheme.content_type.model in ["currencyhistory"]:
                        instance = model.objects.get(
                            currency__user_code=item.final_inputs["currency"],
                            pricing_policy__user_code=item.final_inputs[
                                "pricing_policy"
                            ],
                            date=item.final_inputs["date"],
                        )
                    else:
                        instance = model.objects.get(
                            master_user=self.master_user,
                            user_code=item.final_inputs["user_code"],
                        )

                    item.final_inputs = self.get_final_inputs(item)

                    result_item = copy.copy(
                        serializer_class(instance=instance, context=self.context).data
                    )

                    for key, value in item.final_inputs.items():
                        if item.final_inputs[key] is not None:
                            result_item[key] = item.final_inputs[key]

                    if self.scheme.content_type.model not in [
                        "pricehistory",
                        "currencyhistory",
                    ]:
                        self.overwrite_item_attributes(result_item, item)

                    result_item = self.convert_relation_to_ids(item, result_item)

                    serializer = serializer_class(
                        data=result_item,
                        instance=instance,
                        partial=True,
                        context=self.context,
                    )
                    serializer.is_valid(raise_exception=True)
                    serializer.save()

                    if self.scheme.item_post_process_script:
                        # POST SUCCESS SCRIPT
                        try:
                            formula.safe_eval(
                                self.scheme.item_post_process_script,
                                names=item.inputs,
                                context=self.context,
                            )
                        except Exception as e:
                            if not item.error_message:
                                item.error_message = ""

                            item.error_message = (
                                item.error_message + "Post script error: %s, "
                            ) % str(e)

                    item.status = "success"
                    item.message = "Item Imported %s" % serializer.instance

                    trn = SimpleImportImportedItem(
                        id=serializer.instance.id, user_code=str(serializer.instance)
                    )

                    item.imported_items.append(trn)

                except Exception as e:
                    item.status = "error"
                    item.error_message = (
                        item.error_message + "==== Overwrite Exception " + str(e)
                    )

                    _l.error("import_item.overwrite  e %s" % e)
                    _l.error(
                        "import_item.overwrite  traceback %s" % traceback.format_exc()
                    )

            else:
                item.status = "error"
                item.error_message = (
                    item.error_message + "====  Create Exception " + str(e)
                )

    def process_items(self):
        _l.info("SimpleImportProcess.Task %s. process_items INIT" % self.task)

        index = 0

        for item in self.items:
            try:
                _l.info(
                    "SimpleImportProcess.Task %s. ========= process row %s/%s ========"
                    % (self.task, str(item.row_number), str(self.result.total_rows))
                )

                if self.scheme.filter_expr:
                    # expr = Expression.parseString("a == 1 and b == 2")
                    # expr = Expression.parseString(self.scheme.filter_expr)

                    result = bool(
                        formula.safe_eval(
                            self.scheme.filter_expr,
                            names=item.inputs,
                            context=self.context,
                        )
                    )

                    if result:
                        # filter passed
                        pass
                    else:
                        item.status = "skip"
                        item.message = "Skipped due filter"

                        _l.info(
                            "SimpleImportProcess.Task %s. Row skipped due filter %s"
                            % (self.task, str(item.row_number))
                        )
                        continue

                self.import_item(item)

                self.result.processed_rows = self.result.processed_rows + 1

                self.task.update_progress(
                    {
                        "current": self.result.processed_rows,
                        "total": len(self.items),
                        "percent": round(
                            self.result.processed_rows / (len(self.items) / 100)
                        ),
                        "description": "Row %s processed" % self.result.processed_rows,
                    }
                )

            except Exception as e:
                item.status = "error"
                item.message = "Error %s" % e

                _l.error(
                    "SimpleImportProcess.Task %s.  ========= process row %s ======== Exception %s"
                    % (self.task, str(item.row_number), e)
                )
                _l.error(
                    "SimpleImportProcess.Task %s.  ========= process row %s ======== Traceback %s"
                    % (self.task, str(item.row_number), traceback.format_exc())
                )

        self.result.items = self.items

        _l.info("SimpleImportProcess.Task %s. process_items DONE" % self.task)

    def process(self):
        try:
            self.process_items()

        except Exception as e:
            _l.error(
                "SimpleImportProcess.Task %s. process Exception %s" % (self.task, e)
            )
            _l.error(
                "SimpleImportProcess.Task %s. process Traceback %s"
                % (self.task, traceback.format_exc())
            )

            self.result.error_message = "General Import Error. Exception %s" % e

            if (
                self.execution_context
                and self.execution_context["started_by"] == "procedure"
            ):
                send_system_message(
                    master_user=self.master_user,
                    performed_by="System",
                    description="Can't process file. Exception %s" % e,
                )

        finally:
            if self.task.options_object and "items" in self.task.options_object:
                pass
            else:
                pass

            self.task.result_object = SimpleImportResultSerializer(
                instance=self.result, context=self.context
            ).data

            self.result.reports = []

            self.result.reports.append(self.generate_file_report())
            self.result.reports.append(self.generate_json_report())

            error_rows_count = 0
            for result_item in self.result.items:
                if result_item.status == "error":
                    error_rows_count = error_rows_count + 1

            if error_rows_count != 0:
                send_system_message(
                    master_user=self.master_user,
                    action_status="required",
                    type="warning",
                    title="Simple Import Partially Failed. Task id: %s" % self.task.id,
                    description="Error rows %s/%s"
                    % (error_rows_count, len(self.result.items)),
                )

            system_message_title = "New Items (import from file)"
            system_message_description = (
                "New items created (Import scheme - "
                + str(self.scheme.name)
                + ") - "
                + str(len(self.items))
            )

            import_system_message_title = "Simple import (finished)"

            system_message_performed_by = self.member.username

            if self.process_type == ProcessType.JSON:
                if (
                    self.execution_context
                    and self.execution_context["started_by"] == "procedure"
                ):
                    system_message_title = "New itmes (import from broker)"
                    system_message_performed_by = "System"

                    import_system_message_title = "Simple import from broker (finished)"

            send_system_message(
                master_user=self.master_user,
                performed_by=system_message_performed_by,
                section="import",
                type="success",
                title="Import Finished. Prices Recalculation Required",
                description="Please, run schedule or execute procedures to calculate portfolio prices and nav history",
            )

        send_system_message(
            master_user=self.master_user,
            performed_by=system_message_performed_by,
            section="import",
            type="success",
            title=import_system_message_title,
            attachments=[self.result.reports[0].id, self.result.reports[1].id],
        )

        send_system_message(
            master_user=self.master_user,
            performed_by=system_message_performed_by,
            section="import",
            type="success",
            title=system_message_title,
            description=system_message_description,
        )

        if self.procedure_instance and self.procedure_instance.schedule_instance:
            self.procedure_instance.schedule_instance.run_next_procedure()

        self.task.add_attachment(self.result.reports[0].id)
        self.task.add_attachment(self.result.reports[1].id)

        self.task.verbose_result = self.get_verbose_result()

        self.task.status = CeleryTask.STATUS_DONE
        self.task.mark_task_as_finished()
        self.task.save()

        return self.result
