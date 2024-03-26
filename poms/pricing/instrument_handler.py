import logging
import time

from django.db import transaction
from django.db.models import Q

from poms_app import settings

from poms.common.utils import date_now, isclose
from poms.expressions_engine import formula
from poms.instruments.models import Instrument, PriceHistory, PricingCondition
from poms.integrations.models import BloombergDataProviderCredential, ProviderClass
from poms.obj_attrs.models import GenericAttribute, GenericAttributeType
from poms.portfolios.models import PortfolioRegister, PortfolioRegisterRecord
from poms.pricing.models import (
    InstrumentPricingSchemeType,
    PriceHistoryError,
    PricingProcedureAlphavInstrumentResult,
    PricingProcedureBloombergForwardInstrumentResult,
    PricingProcedureBloombergInstrumentResult,
    PricingProcedureCbondsInstrumentResult,
    PricingProcedureWtradeInstrumentResult,
)
from poms.pricing.transport.transport import PricingTransport
from poms.pricing.utils import (
    get_closest_tenors,
    get_empty_values_for_dates,
    get_is_yesterday,
    get_list_of_dates_between_two_dates,
    get_parameter_from_scheme_parameters,
    get_unique_pricing_schemes,
    group_instrument_items_by_provider,
    optimize_items,
    roll_price_history_for_n_day_forward,
)
from poms.procedures.models import (
    BaseProcedureInstance,
    PricingProcedure,
    PricingProcedureInstance,
)
from poms.reports.common import Report
from poms.reports.sql_builders.balance import BalanceReportBuilderSql
from poms.system_messages.handlers import send_system_message
from poms.transactions.models import Transaction
from poms.users.models import Member

_l = logging.getLogger("poms.pricing")


class InstrumentItem(object):
    def __init__(self, instrument, policy, pricing_scheme):
        self.instrument = instrument
        self.policy = policy
        self.pricing_scheme = pricing_scheme

        self.scheme_fields = []
        self.scheme_fields_map = {}
        self.parameters = []

        self.fill_parameters()
        self.fill_scheme_fields()

    def fill_parameters(self):
        if self.pricing_scheme.type.input_type == InstrumentPricingSchemeType.NONE:
            pass  # do nothing

        if (
            self.pricing_scheme.type.input_type
            == InstrumentPricingSchemeType.SINGLE_PARAMETER
        ):
            if self.policy.default_value:
                self.parameters.append(self.policy.default_value)
            else:
                result = None

                if self.policy.attribute_key == "reference_for_pricing":
                    result = self.instrument.reference_for_pricing
                else:
                    try:
                        if "attributes" in self.policy.attribute_key:
                            user_code = self.policy.attribute_key.split("attributes.")[
                                1
                            ]
                        else:
                            user_code = self.policy.attribute_key

                        attribute = GenericAttribute.objects.get(
                            object_id=self.instrument.id,
                            attribute_type__user_code=user_code,
                        )

                        if (
                            attribute.attribute_type.value_type
                            == GenericAttributeType.STRING
                        ):
                            result = attribute.value_string

                        if (
                            attribute.attribute_type.value_type
                            == GenericAttributeType.NUMBER
                        ):
                            result = attribute.value_float

                        if (
                            attribute.attribute_type.value_type
                            == GenericAttributeType.DATE
                        ):
                            result = attribute.value_date

                        if (
                            attribute.attribute_type.value_type
                            == GenericAttributeType.CLASSIFIER
                        ):
                            if attribute.classifier:
                                result = attribute.classifier.name

                    except (Exception, GenericAttribute.DoesNotExist) as e:
                        _l.info(
                            "instrument_handler fill_parameters instrument %s "
                            % self.instrument
                        )
                        _l.info("instrument_handler fill_parameters error %s " % e)
                        pass

                if result:
                    self.parameters.append(result)

        if (
            self.pricing_scheme.type.input_type
            == InstrumentPricingSchemeType.MULTIPLE_PARAMETERS
        ):
            pass  # TODO implement multiparameter case

    def fill_scheme_fields(self):
        parameters = self.pricing_scheme.get_parameters()

        if self.pricing_scheme.type.id == 5:
            self.scheme_fields_map = {}

            if parameters.bid_historical:
                self.scheme_fields.append([parameters.bid_historical])
                self.scheme_fields_map["bid_historical"] = parameters.bid_historical

            if parameters.ask_historical:
                self.scheme_fields.append([parameters.ask_historical])
                self.scheme_fields_map["ask_historical"] = parameters.ask_historical

            if parameters.accrual_historical:
                self.scheme_fields.append([parameters.accrual_historical])
                self.scheme_fields_map[
                    "accrual_historical"
                ] = parameters.accrual_historical

            if parameters.last_historical:
                self.scheme_fields.append([parameters.last_historical])
                self.scheme_fields_map["last_historical"] = parameters.last_historical

            if parameters.bid_yesterday:
                self.scheme_fields.append([parameters.bid_yesterday])
                self.scheme_fields_map["bid_yesterday"] = parameters.bid_yesterday

            if parameters.ask_yesterday:
                self.scheme_fields.append([parameters.ask_yesterday])
                self.scheme_fields_map["ask_yesterday"] = parameters.ask_yesterday

            if parameters.last_yesterday:
                self.scheme_fields.append([parameters.last_yesterday])
                self.scheme_fields_map["last_yesterday"] = parameters.last_yesterday

            if parameters.accrual_yesterday:
                self.scheme_fields.append([parameters.accrual_yesterday])
                self.scheme_fields_map[
                    "accrual_yesterday"
                ] = parameters.accrual_yesterday


class PricingInstrumentHandler(object):
    def __init__(
        self,
        procedure=None,
        parent_procedure=None,
        master_user=None,
        member=None,
        schedule_instance=None,
    ):
        self.master_user = master_user
        self.procedure = procedure
        self.parent_procedure = parent_procedure

        self.member = member or Member.objects.get(username="finmars_bot")

        self.schedule_instance = schedule_instance

        self.instruments = []

        self.instrument_pricing_schemes = []

        self.instrument_items = []

        self.instrument_items_grouped = {}

        # self.broker_bloomberg = BrokerBloomberg()
        self.transport = PricingTransport()

    def process(self):
        _l.debug("Pricing Instrument Handler: Process")

        self.instruments = self.get_instruments()

        self.instrument_pricing_schemes = get_unique_pricing_schemes(self.instruments)

        _l.debug(
            f"instrument_pricing_schemes len {len(self.instrument_pricing_schemes)}"
        )

        self.instrument_items = self.get_instrument_items()

        _l.debug(f"instrument_items len {len(self.instrument_items)}")

        self.instrument_items_grouped = group_instrument_items_by_provider(
            items=self.instrument_items, groups=self.instrument_pricing_schemes
        )

        _l.debug("instrument_items_grouped len %s" % len(self.instrument_items_grouped))

        self.print_grouped_instruments()

        for provider_id, items in self.instrument_items_grouped.items():
            if len(items):
                if provider_id == 3:
                    self.process_to_single_parameter_formula(items)

                elif provider_id == 4:
                    self.process_to_multiple_parameter_formula(items)

                elif provider_id == 5:
                    self.process_to_bloomberg_provider(items)

                elif provider_id == 6:
                    self.process_to_wtrade_provider(items)

                elif provider_id == 7:
                    self.process_to_alphav_provider(items)

                elif provider_id == 8:
                    self.process_to_bloomberg_forwards_provider(items)

                elif provider_id == 9:
                    self.process_to_cbonds_provider(items)

                elif provider_id == "has_linked_with_portfolio":
                    self.process_to_linked_with_portfolio_provider(items)

    def get_instruments(self):
        result = []

        instruments = Instrument.objects.filter(
            master_user=self.procedure.master_user, is_deleted=False
        ).exclude(user_code="-")

        instruments_opened = set()
        instruments_always = set()

        if self.procedure.type == PricingProcedure.CREATED_BY_USER:
            # User configured pricing condition filters
            active_pricing_conditions = []

            if self.procedure.instrument_pricing_condition_filters:
                active_pricing_conditions = list(
                    map(
                        int,
                        self.procedure.instrument_pricing_condition_filters.split(","),
                    )
                )

            # Add RUN_VALUATION_ALWAYS currencies only if pricing condition is enabled
            if PricingCondition.RUN_VALUATION_ALWAYS in active_pricing_conditions:
                for i in instruments:
                    if i.pricing_condition_id in [
                        PricingCondition.RUN_VALUATION_ALWAYS
                    ]:
                        instruments_always.add(i.id)

            _l.debug(
                "PricingInstrumentHandler.get_instruments: instruments always len %s"
                % len(instruments_always)
            )

            # Add RUN_VALUATION_IF_NON_ZERO currencies only if pricing condition is enabled
            if PricingCondition.RUN_VALUATION_IF_NON_ZERO in active_pricing_conditions:
                # Here we have two steps
                # Step "a" we took base transaction until procedure.price_date_from
                # And take only that instruments with position size that is not size

                # Step "b" we took base transactions from procedure.price_date_from (exclude)
                # and procedure.price_date_to. Instruments from that query we add up to instruments from step "a"

                # Step "a" starts here

                processing_st_a = time.perf_counter()

                base_transactions_a = Transaction.objects.filter(
                    master_user=self.procedure.master_user
                )

                base_transactions_a = base_transactions_a.filter(
                    Q(accounting_date__lte=self.procedure.price_date_from)
                    | Q(cash_date__lte=self.procedure.price_date_from)
                )

                if self.procedure.portfolio_filters:
                    portfolio_user_codes = self.procedure.portfolio_filters.split(",")

                    base_transactions_a = base_transactions_a.filter(
                        portfolio__user_code__in=portfolio_user_codes
                    )

                _l.debug(
                    "< get_instruments base transactions (step a) len %s",
                    len(base_transactions_a),
                )
                _l.debug(
                    "< get_instruments base transactions (step a) done in %s",
                    (time.perf_counter() - processing_st_a),
                )

                instruments_dict = {}

                if len(list(base_transactions_a)):
                    instruments_positions = {}

                    for trn in base_transactions_a:
                        if trn.instrument_id:
                            if trn.instrument_id in instruments_positions:
                                instruments_positions[trn.instrument_id] = (
                                    instruments_positions[trn.instrument_id]
                                    + trn.position_size_with_sign
                                )
                            else:
                                instruments_positions[
                                    trn.instrument_id
                                ] = trn.position_size_with_sign

                            instruments_dict[trn.instrument_id] = trn.instrument

                    for id, pos in instruments_positions.items():
                        if not isclose(pos, 0.0) and instruments_dict[
                            id
                        ].pricing_condition_id in [
                            PricingCondition.RUN_VALUATION_IF_NON_ZERO
                        ]:
                            instruments_opened.add(id)

                _l.debug(
                    "< get_instruments instruments_opened (step a) len %s"
                    % len(instruments_opened)
                )

                # Step "a" ends here

                # Step "b" starts here

                processing_st_b = time.perf_counter()

                base_transactions_b = Transaction.objects.filter(
                    master_user=self.procedure.master_user
                )

                base_transactions_b = base_transactions_b.filter(
                    Q(accounting_date__gt=self.procedure.price_date_from)
                    | Q(cash_date__gt=self.procedure.price_date_from)
                )
                base_transactions_b = base_transactions_b.filter(
                    Q(accounting_date__lte=self.procedure.price_date_to)
                    | Q(cash_date__lte=self.procedure.price_date_to)
                )

                if self.procedure.portfolio_filters:
                    portfolio_user_codes = self.procedure.portfolio_filters.split(",")

                    base_transactions_b = base_transactions_b.filter(
                        portfolio__user_code__in=portfolio_user_codes
                    )

                _l.debug(
                    "< get_instruments base transactions (step b) len %s",
                    len(base_transactions_b),
                )
                _l.debug(
                    "< get_instruments base transactions (step b) done in %s",
                    (time.perf_counter() - processing_st_b),
                )

                for trn in base_transactions_b:
                    if trn.instrument_id and trn.instrument.pricing_condition_id in [
                                                PricingCondition.RUN_VALUATION_IF_NON_ZERO
                                            ]:
                        instruments_opened.add(trn.instrument_id)

                _l.debug(
                    "< get_instruments instruments_opened (step b) len %s"
                    % len(instruments_opened)
                )

                # Step "b" ends here

            _l.debug(
                "PricingInstrumentHandler.get_instruments: instruments opened len %s"
                % len(instruments_opened)
            )

            instruments = instruments.filter(
                pk__in=(instruments_always | instruments_opened)
            )

            _l.debug(
                "PricingInstrumentHandler.get_instruments: instruments filtered len %s"
                % len(instruments)
            )

            if self.procedure.instrument_type_filters:
                user_codes = self.procedure.instrument_type_filters.split(",")

                _l.debug("Filter by Instrument Types %s " % user_codes)

                _l.debug("instruments before filter %s " % len(instruments))
                instruments = instruments.filter(
                    instrument_type__user_code__in=user_codes
                )
                _l.debug("instruments after filter %s " % len(instruments))

            result = instruments

        if self.procedure.type == PricingProcedure.CREATED_BY_INSTRUMENT:
            if self.procedure.instrument_filters:
                user_codes = self.procedure.instrument_filters.split(",")

                _l.debug("Filter by Instruments %s " % user_codes)

                _l.debug("instruments before filter %s " % len(instruments))
                instruments = instruments.filter(user_code__in=user_codes)
                _l.debug("instruments after filter %s " % len(instruments))

                result = instruments

        return result

    def get_instrument_items(self):
        result = []

        for instrument in self.instruments:
            for policy in instrument.pricing_policies.all():
                if policy.pricing_scheme:
                    allowed_policy = True  # Policy that will pass all filters

                    if self.procedure.instrument_pricing_scheme_filters:
                        if (
                            policy.pricing_scheme.user_code
                            not in self.procedure.instrument_pricing_scheme_filters
                        ):
                            allowed_policy = False

                    if self.procedure.pricing_policy_filters:
                        if (
                            policy.pricing_policy.user_code
                            not in self.procedure.pricing_policy_filters
                        ):
                            allowed_policy = False

                    if allowed_policy:
                        item = InstrumentItem(instrument, policy, policy.pricing_scheme)

                        result.append(item)

        return result

    # DEPRECATED
    def calculate_simple_balance_report(
        self, master_user, report_date, report_currency, portfolio_register
    ):
        instance = Report(master_user=master_user)

        instance.master_user = master_user
        instance.report_date = report_date
        instance.pricing_policy = portfolio_register.valuation_pricing_policy
        instance.report_currency = report_currency
        instance.portfolios = [portfolio_register.portfolio]

        builder = BalanceReportBuilderSql(instance=instance)
        instance = builder.build_balance()

        return instance

    # DEPRECATED
    def process_to_linked_with_portfolio_provider(self, items):
        _l.debug(
            "Pricing Instrument Handler - Single parameters Formula: len %s"
            % len(items)
        )

        dates = get_list_of_dates_between_two_dates(
            date_from=self.procedure.price_date_from,
            date_to=self.procedure.price_date_to,
        )

        successful_prices_count = 0
        error_prices_count = 0

        procedure_instance = PricingProcedureInstance(
            procedure=self.procedure,
            parent_procedure_instance=self.parent_procedure,
            master_user=self.master_user,
            status=PricingProcedureInstance.STATUS_PENDING,
            action="linked_with_portfolio_instrument_prices",
            provider="finmars",
            action_verbose="Get Instrument Prices from Linked With Portfolio",
            provider_verbose="Finmars",
        )

        if self.member:
            procedure_instance.started_by = BaseProcedureInstance.STARTED_BY_MEMBER
            procedure_instance.member = self.member

        if self.schedule_instance:
            procedure_instance.started_by = BaseProcedureInstance.STARTED_BY_SCHEDULE
            procedure_instance.schedule_instance = self.schedule_instance

        procedure_instance.save()

        for item in items:
            last_price = None

            _l.info("item %s" % item)
            _l.info("item %s" % item.__dict__)
            _l.info("item %s" % item.instrument)

            for date in dates:
                principal_price = None
                accrued_price = None

                try:
                    portfolio_register = PortfolioRegister.objects.get(
                        master_user=self.master_user, instrument=item.instrument
                    )

                    portfolio_register_record = PortfolioRegisterRecord.objects.get(
                        master_user=self.master_user,
                        instrument=item.instrument,
                        transaction_date=date,
                    )

                    balance_report = self.calculate_simple_balance_report(
                        self.master_user,
                        date,
                        portfolio_register.valuation_currency,
                        portfolio_register,
                    )

                    nav = 0

                    for balance_report_item in balance_report.items:
                        if balance_report_item["market_value"]:
                            nav = nav + balance_report_item["market_value"]

                    principal_price = (
                        nav / portfolio_register_record.n_shares_end_of_the_day
                    )

                    try:
                        price = PriceHistory.objects.get(
                            instrument=item.instrument,
                            pricing_policy=item.policy.pricing_policy,
                            date=date,
                        )

                        if (
                            not self.procedure.price_overwrite_principal_prices
                            and not self.procedure.price_overwrite_accrued_prices
                        ):
                            can_write = False
                            _l.debug("Skip %s" % price)
                        else:
                            _l.debug("Overwrite existing %s" % price)

                    except PriceHistory.DoesNotExist:
                        price = PriceHistory(
                            instrument=item.instrument,
                            pricing_policy=item.policy.pricing_policy,
                            date=date,
                        )

                        _l.debug("Create new %s" % price)

                    price.procedure_modified_datetime = date_now()

                    price.principal_price = 0
                    price.accrued_price = 0

                    if principal_price is not None:
                        if price.id:
                            if self.procedure.price_overwrite_principal_prices:
                                price.principal_price = principal_price
                        else:
                            price.principal_price = principal_price

                    if accrued_price is not None:
                        if price.id:
                            if self.procedure.price_overwrite_accrued_prices:
                                price.accrued_price = accrued_price
                        else:
                            price.accrued_price = accrued_price

                    # _l.debug(
                    #     "Price: %s. Can write: %s. Has Error: %s." % (price, can_write, None)
                    # )

                    price.nav = nav

                    price.save()

                    last_price = price

                except (
                    Exception,
                    PortfolioRegister.DoesNotExist,
                    PortfolioRegisterRecord.DoesNotExist,
                ):
                    _l.debug(
                        "Portfolio register or PortfolioRegisterRecord is not found"
                    )

            if last_price:
                successes, errors = roll_price_history_for_n_day_forward(
                    item,
                    self.procedure,
                    last_price,
                    self.master_user,
                    procedure_instance,
                    item.policy,
                )

                successful_prices_count = successful_prices_count + successes
                error_prices_count = error_prices_count + errors

        procedure_instance.successful_prices_count = successful_prices_count
        procedure_instance.error_prices_count = error_prices_count

        procedure_instance.status = PricingProcedureInstance.STATUS_DONE

        procedure_instance.save()

        if procedure_instance.schedule_instance:
            procedure_instance.schedule_instance.run_next_procedure()

    def process_to_single_parameter_formula(self, items):
        _l.debug(
            "Pricing Instrument Handler - Single parameters Formula: len %s"
            % len(items)
        )

        procedure_instance = PricingProcedureInstance.objects.create(
            procedure=self.procedure,
            parent_procedure_instance=self.parent_procedure,
            master_user=self.master_user,
            member=self.member,
            status=PricingProcedureInstance.STATUS_PENDING,
            action="single_parameter_formula_get_instrument_prices",
            provider="finmars",
            action_verbose="Get Instrument Prices from Single Parameter Formula",
            provider_verbose="Finmars",
        )

        if self.member:
            procedure_instance.started_by = BaseProcedureInstance.STARTED_BY_MEMBER
            procedure_instance.member = self.member

        if self.schedule_instance:
            procedure_instance.started_by = BaseProcedureInstance.STARTED_BY_SCHEDULE
            procedure_instance.schedule_instance = self.schedule_instance

        try:
            dates = get_list_of_dates_between_two_dates(
                date_from=self.procedure.price_date_from,
                date_to=self.procedure.price_date_to,
            )

            successful_prices_count = 0
            error_prices_count = 0

            procedure_instance.save()

            for item in items:
                last_price = None

                for date in dates:
                    scheme_parameters = item.pricing_scheme.get_parameters()

                    if scheme_parameters:
                        safe_instrument = {
                            "id": item.instrument.id,
                        }

                        safe_pp = {
                            "id": item.policy.id,
                        }

                        parameter = get_parameter_from_scheme_parameters(
                            item, item.policy, scheme_parameters
                        )

                        values = {
                            "context_date": date,
                            "context_instrument": safe_instrument,
                            "context_pricing_policy": safe_pp,
                            "parameter": parameter,
                        }

                        expr = scheme_parameters.expr
                        accrual_expr = scheme_parameters.accrual_expr
                        pricing_error_text_expr = (
                            scheme_parameters.pricing_error_text_expr
                        )
                        accrual_error_text_expr = (
                            scheme_parameters.accrual_error_text_expr
                        )

                        _l.debug("values %s" % values)
                        _l.debug("expr %s" % expr)

                        has_error = False
                        error = PriceHistoryError(
                            master_user=self.master_user,
                            procedure_instance=procedure_instance,
                            instrument=item.instrument,
                            pricing_scheme=item.pricing_scheme,
                            pricing_policy=item.policy.pricing_policy,
                            date=date,
                            created=procedure_instance.created,
                        )

                        principal_price = None
                        accrued_price = None

                        try:
                            principal_price = formula.safe_eval(expr, names=values)
                        except formula.InvalidExpression:
                            has_error = True

                            try:
                                _l.debug(
                                    "pricing_error_text_expr %s"
                                    % pricing_error_text_expr
                                )

                                error.error_text = formula.safe_eval(
                                    pricing_error_text_expr, names=values
                                )

                            except formula.InvalidExpression:
                                error.error_text = "Invalid Error Text Expression"

                        if (
                            scheme_parameters.accrual_calculation_method == 2
                        ):  # ACCRUAL_PER_SCHEDULE
                            try:
                                accrued_price = item.instrument.get_accrued_price(date)
                            except Exception:
                                has_error = True

                                try:
                                    _l.debug(
                                        "accrual_error_text_expr %s"
                                        % accrual_error_text_expr
                                    )

                                    error.error_text = formula.safe_eval(
                                        accrual_error_text_expr, names=values
                                    )

                                except formula.InvalidExpression:
                                    error.error_text = "Invalid Error Text Expression"

                        if (
                            scheme_parameters.accrual_calculation_method == 3
                        ):  # ACCRUAL_PER_FORMULA
                            try:
                                accrued_price = formula.safe_eval(
                                    accrual_expr, names=values
                                )
                            except formula.InvalidExpression:
                                has_error = True

                                try:
                                    _l.debug(
                                        "accrual_error_text_expr %s"
                                        % accrual_error_text_expr
                                    )

                                    error.error_text = formula.safe_eval(
                                        accrual_error_text_expr, names=values
                                    )

                                except formula.InvalidExpression:
                                    error.error_text = "Invalid Error Text Expression"

                        can_write = True

                        try:
                            price = PriceHistory.objects.get(
                                instrument=item.instrument,
                                pricing_policy=item.policy.pricing_policy,
                                date=date,
                            )

                            if (
                                not self.procedure.price_overwrite_principal_prices
                                and not self.procedure.price_overwrite_accrued_prices
                            ):
                                can_write = False
                                _l.debug("Skip %s" % price)
                            else:
                                _l.debug("Overwrite existing %s" % price)

                        except PriceHistory.DoesNotExist:
                            price = PriceHistory(
                                instrument=item.instrument,
                                pricing_policy=item.policy.pricing_policy,
                                date=date,
                            )

                            _l.debug("Create new %s" % price)

                        price.procedure_modified_datetime = date_now()

                        price.principal_price = 0
                        price.accrued_price = 0

                        if principal_price is not None:
                            if price.id:
                                if self.procedure.price_overwrite_principal_prices:
                                    price.principal_price = principal_price
                            else:
                                price.principal_price = principal_price

                            error.principal_price = principal_price

                        if accrued_price is not None:
                            if price.id:
                                if self.procedure.price_overwrite_accrued_prices:
                                    price.accrued_price = accrued_price
                            else:
                                price.accrued_price = accrued_price

                            error.accrued_price = accrued_price

                        _l.debug(
                            "Price: %s. Can write: %s. Has Error: %s."
                            % (price, can_write, has_error)
                        )

                        if price.accrued_price == 0 and price.principal_price == 0:
                            has_error = True

                            error.error_text = error.error_text + " Price is 0 or null"

                        if can_write:
                            # if has_error:
                            #     # if has_error or (price.accrued_price == 0 and price.principal_price == 0):
                            #
                            #     error_prices_count = error_prices_count + 1
                            #     error.status = PriceHistoryError.STATUS_ERROR
                            #     error.save()
                            #
                            # else:

                            successful_prices_count = successful_prices_count + 1

                            price.save()

                            if price.id:
                                error.status = PriceHistoryError.STATUS_OVERWRITTEN
                            else:
                                error.status = PriceHistoryError.STATUS_SKIP
                            error.save()

                        else:
                            error_prices_count = error_prices_count + 1

                            error.error_text = (
                                "Prices already exists. Principal Price: "
                                + str(principal_price)
                                + "; Accrued: "
                                + str(accrued_price)
                                + "."
                            )

                            error.status = PriceHistoryError.STATUS_SKIP
                            error.save()

                        last_price = price

                successes, errors = roll_price_history_for_n_day_forward(
                    item,
                    self.procedure,
                    last_price,
                    self.master_user,
                    procedure_instance,
                    item.policy,
                )

                successful_prices_count = successful_prices_count + successes
                error_prices_count = error_prices_count + errors

            procedure_instance.successful_prices_count = successful_prices_count
            procedure_instance.error_prices_count = error_prices_count

            procedure_instance.status = PricingProcedureInstance.STATUS_DONE

            procedure_instance.save()

            if procedure_instance.schedule_instance:
                procedure_instance.schedule_instance.run_next_procedure()

        except Exception as e:
            procedure_instance.error_message = "Error %s" % e
            procedure_instance.status = PricingProcedureInstance.STATUS_ERROR
            procedure_instance.save()

    def process_to_multiple_parameter_formula(self, items):
        _l.debug(
            "Pricing Instrument Handler - Multiple parameters Formula: len %s"
            % len(items)
        )

        procedure_instance = PricingProcedureInstance(
            procedure=self.procedure,
            parent_procedure_instance=self.parent_procedure,
            master_user=self.master_user,
            member=self.member,
            status=PricingProcedureInstance.STATUS_PENDING,
            action="multiple_parameter_formula_get_instrument_prices",
            provider="finmars",
            action_verbose="Get Instrument Prices Multiple Parameter Formula",
            provider_verbose="Finmars",
        )

        dates = get_list_of_dates_between_two_dates(
            date_from=self.procedure.price_date_from,
            date_to=self.procedure.price_date_to,
        )

        successful_prices_count = 0
        error_prices_count = 0

        if self.member:
            procedure_instance.started_by = BaseProcedureInstance.STARTED_BY_MEMBER
            procedure_instance.member = self.member

        if self.schedule_instance:
            procedure_instance.started_by = BaseProcedureInstance.STARTED_BY_SCHEDULE
            procedure_instance.schedule_instance = self.schedule_instance

        procedure_instance.save()

        try:
            for item in items:
                last_price = None

                for date in dates:
                    scheme_parameters = item.pricing_scheme.get_parameters()

                    if scheme_parameters:
                        safe_instrument = {
                            "id": item.instrument.id,
                        }

                        safe_pp = {
                            "id": item.policy.id,
                        }

                        parameter = None

                        try:
                            if item.policy.default_value:
                                if scheme_parameters.value_type == 10:
                                    parameter = str(item.policy.default_value)

                                elif scheme_parameters.value_type == 20:
                                    parameter = float(item.policy.default_value)

                                elif scheme_parameters.value_type == 40:
                                    parameter = formula._parse_date(
                                        str(item.policy.default_value)
                                    )

                                else:
                                    parameter = item.policy.default_value

                            elif item.policy.attribute_key:
                                if "attributes" in item.policy.attribute_key:
                                    user_code = item.policy.attribute_key.split(
                                        "attributes."
                                    )[1]

                                    attribute = GenericAttribute.objects.get(
                                        object_id=item.instrument.id,
                                        attribute_type__user_code=user_code,
                                    )

                                    if scheme_parameters.value_type == 10:
                                        parameter = attribute.value_string

                                    elif scheme_parameters.value_type == 20:
                                        parameter = attribute.value_float

                                    elif scheme_parameters.value_type == 40:
                                        parameter = attribute.value_date

                                else:
                                    parameter = getattr(
                                        item.instrument, item.policy.attribute_key, None
                                    )

                        except Exception as e:
                            _l.debug("Cant find parameter value. Error: %s" % e)

                            parameter = None

                        values = {
                            "context_date": date,
                            "context_instrument": safe_instrument,
                            "context_pricing_policy": safe_pp,
                            "parameter": parameter,
                        }

                        if item.policy.data:
                            if "parameters" in item.policy.data:
                                for parameter in item.policy.data["parameters"]:
                                    if (
                                        "default_value" in parameter
                                        and parameter["default_value"]
                                    ):
                                        if float(parameter["value_type"]) == 10:
                                            val = str(parameter["default_value"])

                                        elif float(parameter["value_type"]) == 20:
                                            val = float(parameter["default_value"])

                                        elif float(parameter["value_type"]) == 40:
                                            val = formula._parse_date(
                                                str(parameter["default_value"])
                                            )

                                        else:
                                            val = parameter["default_value"]

                                    if (
                                        "attribute_key" in parameter
                                        and parameter["attribute_key"]
                                    ):
                                        if "attributes" in parameter["attribute_key"]:
                                            user_code = parameter[
                                                "attribute_key"
                                            ].split("attributes.")[1]

                                            attribute = GenericAttribute.objects.get(
                                                object_id=item.instrument.id,
                                                attribute_type__user_code=user_code,
                                            )

                                            if float(parameter["value_type"]) == 10:
                                                val = attribute.value_string

                                            elif float(parameter["value_type"]) == 20:
                                                val = attribute.value_float

                                            elif float(parameter["value_type"]) == 40:
                                                val = attribute.value_date

                                        else:
                                            val = getattr(
                                                item.instrument,
                                                parameter["attribute_key"],
                                            )

                                    values["parameter" + str(parameter["index"])] = val

                        expr = scheme_parameters.expr
                        accrual_expr = scheme_parameters.accrual_expr
                        pricing_error_text_expr = (
                            scheme_parameters.pricing_error_text_expr
                        )
                        accrual_error_text_expr = (
                            scheme_parameters.accrual_error_text_expr
                        )

                        _l.debug("values %s" % values)
                        _l.debug("expr %s" % expr)

                        has_error = False
                        error = PriceHistoryError(
                            master_user=self.master_user,
                            procedure_instance=procedure_instance,
                            instrument=item.instrument,
                            pricing_scheme=item.pricing_scheme,
                            pricing_policy=item.policy.pricing_policy,
                            date=date,
                            created=procedure_instance.created,
                        )

                        principal_price = None
                        accrued_price = None

                        try:
                            principal_price = formula.safe_eval(expr, names=values)
                        except formula.InvalidExpression:
                            has_error = True

                            try:
                                error.error_text = formula.safe_eval(
                                    pricing_error_text_expr, names=values
                                )
                            except formula.InvalidExpression:
                                error.error_text = "Invalid Error Text Expression"

                        _l.debug("principal_price %s" % principal_price)

                        if (
                            scheme_parameters.accrual_calculation_method == 2
                        ):  # ACCRUAL_PER_SCHEDULE
                            try:
                                accrued_price = item.instrument.get_accrued_price(date)
                            except Exception:
                                has_error = True

                                try:
                                    _l.debug(
                                        "accrual_error_text_expr %s"
                                        % accrual_error_text_expr
                                    )

                                    error.error_text = formula.safe_eval(
                                        accrual_error_text_expr, names=values
                                    )

                                except formula.InvalidExpression:
                                    error.error_text = "Invalid Error Text Expression"

                        if (
                            scheme_parameters.accrual_calculation_method == 3
                        ):  # ACCRUAL_PER_FORMULA
                            try:
                                accrued_price = formula.safe_eval(
                                    accrual_expr, names=values
                                )
                            except formula.InvalidExpression:
                                has_error = True

                                try:
                                    _l.debug(
                                        "accrual_error_text_expr %s"
                                        % accrual_error_text_expr
                                    )

                                    error.error_text = formula.safe_eval(
                                        accrual_error_text_expr, names=values
                                    )

                                except formula.InvalidExpression:
                                    error.error_text = "Invalid Error Text Expression"

                        can_write = True

                        try:
                            price = PriceHistory.objects.get(
                                instrument=item.instrument,
                                pricing_policy=item.policy.pricing_policy,
                                date=date,
                            )

                            if (
                                not self.procedure.price_overwrite_principal_prices
                                and not self.procedure.price_overwrite_accrued_prices
                            ):
                                can_write = False
                                _l.debug("Skip %s" % price)
                            else:
                                _l.debug("Overwrite existing %s" % price)

                        except PriceHistory.DoesNotExist:
                            price = PriceHistory(
                                instrument=item.instrument,
                                pricing_policy=item.policy.pricing_policy,
                                date=date,
                            )

                            _l.debug("Create new %s" % price)

                        price.procedure_modified_datetime = date_now()

                        price.principal_price = 0
                        price.accrued_price = 0

                        if principal_price is not None:
                            if price.id:
                                if self.procedure.price_overwrite_principal_prices:
                                    price.principal_price = principal_price
                            else:
                                price.principal_price = principal_price

                            error.principal_price = principal_price

                        if accrued_price is not None:
                            if price.id:
                                if self.procedure.price_overwrite_accrued_prices:
                                    price.accrued_price = accrued_price
                            else:
                                price.accrued_price = accrued_price

                            error.accrued_price = accrued_price

                        _l.debug(
                            "Price: %s. Can write: %s. Has Error: %s."
                            % (price, can_write, has_error)
                        )

                        if price.accrued_price == 0 and price.principal_price == 0:
                            has_error = True
                            error.error_text = error.error_text + " Price is 0 or null"

                        if can_write:
                            # if has_error or (price.accrued_price == 0 and price.principal_price == 0):
                            # if has_error:
                            #
                            #     error_prices_count = error_prices_count + 1
                            #     error.status = PriceHistoryError.STATUS_ERROR
                            #     error.save()
                            # else:

                            successful_prices_count = successful_prices_count + 1

                            price.save()

                            if price.id:
                                error.status = PriceHistoryError.STATUS_OVERWRITTEN
                            else:
                                error.status = PriceHistoryError.STATUS_SKIP
                            error.save()

                        else:
                            error_prices_count = error_prices_count + 1

                            error.error_text = (
                                "Prices already exists. Principal Price: "
                                + str(principal_price)
                                + "; Accrued: "
                                + str(accrued_price)
                                + "."
                            )

                            error.status = PriceHistoryError.STATUS_SKIP
                            error.save()

                        last_price = price

                successes, errors = roll_price_history_for_n_day_forward(
                    item,
                    self.procedure,
                    last_price,
                    self.master_user,
                    procedure_instance,
                    item.policy,
                )

                successful_prices_count = successful_prices_count + successes
                error_prices_count = error_prices_count + errors

            procedure_instance.successful_prices_count = successful_prices_count
            procedure_instance.error_prices_count = error_prices_count

            procedure_instance.status = PricingProcedureInstance.STATUS_DONE

            procedure_instance.save()

            if procedure_instance.schedule_instance:
                procedure_instance.schedule_instance.run_next_procedure()

        except Exception as e:
            procedure_instance.error_message = "Error %s" % e
            procedure_instance.status = PricingProcedureInstance.STATUS_ERROR
            procedure_instance.save()

    def is_valid_parameter_for_bloomberg(self, parameters):
        reference = parameters[0]

        pieces = reference.split(" ")

        if len(pieces) > 1:
            return True

        return False

    def process_to_bloomberg_provider(self, items):
        _l.debug("Pricing Instrument Handler - Bloomberg Provider: len %s" % len(items))

        procedure_instance = PricingProcedureInstance(
            procedure=self.procedure,
            parent_procedure_instance=self.parent_procedure,
            master_user=self.master_user,
            status=PricingProcedureInstance.STATUS_PENDING,
            action="bloomberg_get_instrument_prices",
            provider="bloomberg",
            action_verbose="Get Instrument Prices from Bloomberg",
            provider_verbose="Bloomberg",
        )

        if self.member:
            procedure_instance.started_by = BaseProcedureInstance.STARTED_BY_MEMBER
            procedure_instance.member = self.member

        if self.schedule_instance:
            procedure_instance.started_by = BaseProcedureInstance.STARTED_BY_SCHEDULE
            procedure_instance.schedule_instance = self.schedule_instance

        procedure_instance.save()

        body = {}
        body["action"] = procedure_instance.action
        body["procedure"] = procedure_instance.id
        body["provider"] = procedure_instance.provider

        config = None

        try:
            config = BloombergDataProviderCredential.objects.get(
                master_user=self.master_user
            )

        except Exception as e:
            config = self.master_user.import_configs.get(
                provider=ProviderClass.BLOOMBERG
            )

        body["user"] = {
            "token": self.master_user.token,
            "base_api_url": self.master_user.space_code,
            "credentials": {
                "p12cert": str(config.p12cert),
                "password": config.password,
            },
        }

        body["error_code"] = None
        body["error_message"] = None

        body["data"] = {}

        body["data"]["date_from"] = str(self.procedure.price_date_from)
        body["data"]["date_to"] = str(self.procedure.price_date_to)
        body["data"]["items"] = []

        items_with_missing_parameters = []

        dates = get_list_of_dates_between_two_dates(
            date_from=self.procedure.price_date_from,
            date_to=self.procedure.price_date_to,
        )

        is_yesterday = get_is_yesterday(
            self.procedure.price_date_from, self.procedure.price_date_to
        )

        _l.debug("is_yesterday %s" % is_yesterday)
        _l.debug("procedure id %s" % body["procedure"])

        full_items = []

        empty_values = get_empty_values_for_dates(dates)

        # _l.debug('empty_values %s' % empty_values)

        for item in items:
            if len(item.parameters):
                item_parameters = item.parameters.copy()
                item_parameters.pop()

                if is_yesterday:
                    for date in dates:
                        with transaction.atomic():
                            try:
                                record = PricingProcedureBloombergInstrumentResult(
                                    master_user=self.master_user,
                                    procedure=procedure_instance,
                                    instrument=item.instrument,
                                    instrument_parameters=str(item_parameters),
                                    pricing_policy=item.policy.pricing_policy,
                                    pricing_scheme=item.pricing_scheme,
                                    reference=item.parameters[0],
                                    date=date,
                                )

                                if "ask_yesterday" in item.scheme_fields_map:
                                    record.ask_parameters = item.scheme_fields_map[
                                        "ask_yesterday"
                                    ]

                                if "bid_yesterday" in item.scheme_fields_map:
                                    record.bid_parameters = item.scheme_fields_map[
                                        "bid_yesterday"
                                    ]

                                if "last_yesterday" in item.scheme_fields_map:
                                    record.last_parameters = item.scheme_fields_map[
                                        "last_yesterday"
                                    ]

                                if "accrual_yesterday" in item.scheme_fields_map:
                                    record.accrual_parameters = item.scheme_fields_map[
                                        "accrual_yesterday"
                                    ]

                                history_record = PriceHistoryError.objects.create(
                                    master_user=self.master_user,
                                    procedure_instance_id=procedure_instance.id,
                                    instrument=record.instrument,
                                    pricing_scheme=record.pricing_scheme,
                                    pricing_policy=record.pricing_policy,
                                    date=record.date,
                                    status=PriceHistoryError.STATUS_REQUESTED,
                                    created=procedure_instance.created,
                                )

                                record.save()

                            except Exception as e:
                                _l.debug("Cant create Result Record %s" % e)
                                pass

                    item_obj = {
                        "reference": item.parameters[0],
                        "parameters": item_parameters,
                        "fields": [],
                    }

                    if "ask_yesterday" in item.scheme_fields_map:
                        item_obj["fields"].append(
                            {
                                "code": item.scheme_fields_map["ask_yesterday"],
                                "parameters": [],
                                "values": empty_values,
                            }
                        )

                    if "bid_yesterday" in item.scheme_fields_map:
                        item_obj["fields"].append(
                            {
                                "code": item.scheme_fields_map["bid_yesterday"],
                                "parameters": [],
                                "values": empty_values,
                            }
                        )

                    if "last_yesterday" in item.scheme_fields_map:
                        item_obj["fields"].append(
                            {
                                "code": item.scheme_fields_map["last_yesterday"],
                                "parameters": [],
                                "values": empty_values,
                            }
                        )

                    if "accrual_yesterday" in item.scheme_fields_map:
                        item_obj["fields"].append(
                            {
                                "code": item.scheme_fields_map["accrual_yesterday"],
                                "parameters": [],
                                "values": empty_values,
                            }
                        )

                    full_items.append(item_obj)

                else:
                    for date in dates:
                        with transaction.atomic():
                            try:
                                record = PricingProcedureBloombergInstrumentResult(
                                    master_user=self.master_user,
                                    procedure=procedure_instance,
                                    instrument=item.instrument,
                                    instrument_parameters=str(item_parameters),
                                    pricing_policy=item.policy.pricing_policy,
                                    pricing_scheme=item.pricing_scheme,
                                    reference=item.parameters[0],
                                    date=date,
                                )

                                if "ask_historical" in item.scheme_fields_map:
                                    record.ask_parameters = item.scheme_fields_map[
                                        "ask_historical"
                                    ]

                                if "bid_historical" in item.scheme_fields_map:
                                    record.bid_parameters = item.scheme_fields_map[
                                        "bid_historical"
                                    ]

                                if "last_historical" in item.scheme_fields_map:
                                    record.last_parameters = item.scheme_fields_map[
                                        "last_historical"
                                    ]

                                if "accrual_historical" in item.scheme_fields_map:
                                    record.accrual_parameters = item.scheme_fields_map[
                                        "accrual_historical"
                                    ]

                                history_record = PriceHistoryError.objects.create(
                                    master_user=self.master_user,
                                    procedure_instance_id=procedure_instance.id,
                                    instrument=record.instrument,
                                    pricing_scheme=record.pricing_scheme,
                                    pricing_policy=record.pricing_policy,
                                    date=record.date,
                                    created=procedure_instance.created,
                                )

                                record.save()

                            except Exception as e:
                                _l.debug("Cant create Result Record %s" % e)

                    item_obj = {
                        "reference": item.parameters[0],
                        "parameters": item_parameters,
                        "fields": [],
                    }

                    if "ask_historical" in item.scheme_fields_map:
                        item_obj["fields"].append(
                            {
                                "code": item.scheme_fields_map["ask_historical"],
                                "parameters": [],
                                "values": empty_values,
                            }
                        )

                    if "bid_historical" in item.scheme_fields_map:
                        item_obj["fields"].append(
                            {
                                "code": item.scheme_fields_map["bid_historical"],
                                "parameters": [],
                                "values": empty_values,
                            }
                        )

                    if "last_historical" in item.scheme_fields_map:
                        item_obj["fields"].append(
                            {
                                "code": item.scheme_fields_map["last_historical"],
                                "parameters": [],
                                "values": empty_values,
                            }
                        )

                    if "accrual_historical" in item.scheme_fields_map:
                        item_obj["fields"].append(
                            {
                                "code": item.scheme_fields_map["accrual_historical"],
                                "parameters": [],
                                "values": empty_values,
                            }
                        )

                    full_items.append(item_obj)

            else:
                items_with_missing_parameters.append(item)

        _l.debug("full_items len: %s" % len(full_items))

        optimized_items = optimize_items(full_items)

        _l.debug("optimized_items len: %s" % len(optimized_items))

        body["data"]["items"] = optimized_items

        _l.debug(
            "items_with_missing_parameters %s" % len(items_with_missing_parameters)
        )
        # _l.debug('data %s' % data)

        _l.debug("self.procedure %s" % self.procedure.id)
        _l.debug("send request %s" % body)

        procedure_instance.request_data = body
        procedure_instance.save()

        try:
            self.transport.send_request(body)

        except Exception as e:
            procedure_instance.status = PricingProcedureInstance.STATUS_ERROR
            procedure_instance.error_code = 500
            procedure_instance.error_message = (
                "Mediator is unavailable. Please try later."
            )

            procedure_instance.save()

            send_system_message(
                master_user=self.master_user,
                performed_by="System",
                type="error",
                description="Pricing Procedure %s. Error, Mediator is unavailable."
                % procedure_instance.procedure.name,
            )

    def process_to_bloomberg_forwards_provider(self, items):
        _l.debug(
            "Pricing Instrument Handler - Bloomberg Forwards Provider: len %s"
            % len(items)
        )

        procedure_instance = PricingProcedureInstance(
            procedure=self.procedure,
            parent_procedure_instance=self.parent_procedure,
            master_user=self.master_user,
            status=PricingProcedureInstance.STATUS_PENDING,
            action="bloomberg_forwards_get_instrument_prices",
            provider="bloomberg_forwards",
            action_verbose="Get Instrument Prices from Bloomberg Forwards",
            provider_verbose="Bloomberg Forwards",
        )
        if self.member:
            procedure_instance.started_by = BaseProcedureInstance.STARTED_BY_MEMBER
            procedure_instance.member = self.member

        if self.schedule_instance:
            procedure_instance.started_by = BaseProcedureInstance.STARTED_BY_SCHEDULE
            procedure_instance.schedule_instance = self.schedule_instance

        procedure_instance.save()

        body = {}
        body["action"] = procedure_instance.action
        body["procedure"] = procedure_instance.id
        body["provider"] = procedure_instance.provider

        config = None

        try:
            config = BloombergDataProviderCredential.objects.get(
                master_user=self.master_user
            )

        except Exception as e:
            config = self.master_user.import_configs.get(
                provider=ProviderClass.BLOOMBERG
            )

        body["user"] = {
            "token": self.master_user.token,
            "base_api_url": self.master_user.space_code,
            "credentials": {
                "p12cert": str(config.p12cert),
                "password": config.password,
            },
        }

        body["error_code"] = None
        body["error_message"] = None

        body["data"] = {}

        body["data"]["date_from"] = str(self.procedure.price_date_from)
        body["data"]["date_to"] = str(self.procedure.price_date_to)
        body["data"]["items"] = []

        items_with_missing_parameters = []

        dates = get_list_of_dates_between_two_dates(
            date_from=self.procedure.price_date_from,
            date_to=self.procedure.price_date_to,
        )

        _l.debug("procedure id %s" % body["procedure"])

        full_items = []

        empty_values = get_empty_values_for_dates(dates)

        for item in items:
            pricing_scheme_parameters = item.policy.pricing_scheme.get_parameters()

            for date in dates:
                with transaction.atomic():
                    try:
                        matched_tenors = []

                        maturity_date = None

                        if pricing_scheme_parameters.attribute_key:
                            maturity_date = getattr(
                                item.instrument, pricing_scheme_parameters.attribute_key
                            )

                        else:
                            maturity_date = pricing_scheme_parameters.default_value

                        if pricing_scheme_parameters.data and maturity_date:
                            if "tenors" in pricing_scheme_parameters.data and len(
                                pricing_scheme_parameters.data["tenors"]
                            ):
                                matched_tenors = get_closest_tenors(
                                    maturity_date,
                                    date,
                                    pricing_scheme_parameters.data["tenors"],
                                )

                        for matched_tenor in matched_tenors:
                            record = PricingProcedureBloombergForwardInstrumentResult(
                                master_user=self.master_user,
                                procedure=procedure_instance,
                                instrument=item.instrument,
                                instrument_parameters=None,
                                pricing_policy=item.policy.pricing_policy,
                                pricing_scheme=item.pricing_scheme,
                                reference=matched_tenor["price_ticker"],
                                tenor_type=matched_tenor["tenor_type"],
                                tenor_clause=matched_tenor["tenor_clause"],
                                date=date,
                            )

                            record.price_code_parameters = (
                                pricing_scheme_parameters.price_code
                            )

                            history_record = PriceHistoryError.objects.create(
                                master_user=self.master_user,
                                procedure_instance_id=procedure_instance.id,
                                instrument=record.instrument,
                                pricing_scheme=record.pricing_scheme,
                                pricing_policy=record.pricing_policy,
                                date=record.date,
                                status=PriceHistoryError.STATUS_REQUESTED,
                                created=procedure_instance.created,
                            )

                            record.save()

                            item_obj = {
                                "reference": matched_tenor["price_ticker"],
                                "parameters": [],
                                "fields": [],
                            }

                            if pricing_scheme_parameters.price_code:
                                item_obj["fields"].append(
                                    {
                                        "code": pricing_scheme_parameters.price_code,
                                        "parameters": [],
                                        "values": empty_values,
                                    }
                                )

                            full_items.append(item_obj)

                    except Exception as e:
                        _l.debug("Cant create Result Record %s" % e)

        _l.debug("full_items len: %s" % len(full_items))

        optimized_items = optimize_items(full_items)

        _l.debug("optimized_items len: %s" % len(optimized_items))

        body["data"]["items"] = optimized_items

        _l.debug(
            "items_with_missing_parameters %s" % len(items_with_missing_parameters)
        )
        # _l.debug('data %s' % data)

        _l.debug("self.procedure %s" % self.procedure.id)
        _l.debug("send request %s" % body)

        procedure_instance.request_data = body
        procedure_instance.save()

        try:
            self.transport.send_request(body)

        except Exception as e:
            procedure_instance.status = PricingProcedureInstance.STATUS_ERROR
            procedure_instance.error_code = 500
            procedure_instance.error_message = (
                "Mediator is unavailable. Please try later."
            )

            procedure_instance.save()

            send_system_message(
                master_user=self.master_user,
                performed_by="System",
                type="error",
                description="Pricing Procedure %s. Error, Mediator is unavailable."
                % procedure_instance.procedure.name,
            )

    def process_to_wtrade_provider(self, items):
        _l.debug("Pricing Instrument Handler - Wtrade Provider: len %s" % len(items))

        procedure_instance = PricingProcedureInstance(
            procedure=self.procedure,
            parent_procedure_instance=self.parent_procedure,
            master_user=self.master_user,
            status=PricingProcedureInstance.STATUS_PENDING,
            action="wtrade_get_instrument_prices",
            provider="wtrade",
            action_verbose="Get Instrument Prices from World Trade Data",
            provider_verbose="World Trade Data",
        )

        if self.member:
            procedure_instance.started_by = BaseProcedureInstance.STARTED_BY_MEMBER
            procedure_instance.member = self.member

        if self.schedule_instance:
            procedure_instance.started_by = BaseProcedureInstance.STARTED_BY_SCHEDULE
            procedure_instance.schedule_instance = self.schedule_instance

        procedure_instance.save()

        body = {}
        body["action"] = procedure_instance.action
        body["procedure"] = procedure_instance.id
        body["provider"] = procedure_instance.provider

        body["user"] = {
            "token": self.master_user.id,
            "base_api_url": self.master_user.space_code
        }

        body["error_code"] = None
        body["error_message"] = None

        body["data"] = {}

        body["data"]["date_from"] = str(self.procedure.price_date_from)
        body["data"]["date_to"] = str(self.procedure.price_date_to)
        body["data"]["items"] = []

        items_with_missing_parameters = []

        dates = get_list_of_dates_between_two_dates(
            date_from=self.procedure.price_date_from,
            date_to=self.procedure.price_date_to,
        )

        empty_values = get_empty_values_for_dates(dates)

        _l.debug("procedure id %s" % body["procedure"])

        full_items = []

        for item in items:
            if len(item.parameters):
                item_parameters = item.parameters.copy()
                item_parameters.pop()

                for date in dates:
                    with transaction.atomic():
                        try:
                            record = PricingProcedureWtradeInstrumentResult(
                                master_user=self.master_user,
                                procedure=procedure_instance,
                                instrument=item.instrument,
                                instrument_parameters=str(item_parameters),
                                pricing_policy=item.policy.pricing_policy,
                                pricing_scheme=item.pricing_scheme,
                                reference=item.parameters[0],
                                date=date,
                            )

                            record.save()

                        except Exception as e:
                            _l.debug("Cant create Result Record %s" % e)
                            pass

                item_obj = {
                    "reference": item.parameters[0],
                    "parameters": item_parameters,
                    "fields": [],
                }

                item_obj["fields"].append(
                    {"code": "close", "parameters": [], "values": empty_values}
                )

                item_obj["fields"].append(
                    {"code": "open", "parameters": [], "values": empty_values}
                )

                item_obj["fields"].append(
                    {"code": "high", "parameters": [], "values": empty_values}
                )

                item_obj["fields"].append(
                    {"code": "low", "parameters": [], "values": empty_values}
                )

                item_obj["fields"].append(
                    {"code": "volume", "parameters": [], "values": empty_values}
                )

                full_items.append(item_obj)

            else:
                items_with_missing_parameters.append(item)

        _l.debug("full_items len: %s" % len(full_items))

        optimized_items = optimize_items(full_items)

        _l.debug("optimized_items len: %s" % len(optimized_items))

        body["data"]["items"] = optimized_items

        _l.debug(
            "items_with_missing_parameters %s" % len(items_with_missing_parameters)
        )
        # _l.debug('data %s' % data)

        _l.debug("self.procedure %s" % self.procedure.id)
        _l.debug("send request %s" % body)

        procedure_instance.request_data = body
        procedure_instance.save()

        try:
            self.transport.send_request(body)

        except Exception as e:
            procedure_instance.status = PricingProcedureInstance.STATUS_ERROR
            procedure_instance.error_code = 500
            procedure_instance.error_message = (
                "Mediator is unavailable. Please try later."
            )

            procedure_instance.save()

            send_system_message(
                master_user=self.master_user,
                performed_by="System",
                type="error",
                description="Pricing Procedure %s. Error, Mediator is unavailable."
                % procedure_instance.procedure.name,
            )

    def process_to_alphav_provider(self, items):
        _l.debug("Pricing Instrument Handler - Alphav Provider: len %s" % len(items))

        procedure_instance = PricingProcedureInstance(
            procedure=self.procedure,
            parent_procedure_instance=self.parent_procedure,
            master_user=self.master_user,
            status=PricingProcedureInstance.STATUS_PENDING,
            action="alphav_get_instrument_prices",
            provider="alphav",
            action_verbose="Get Instrument Prices from Alpha Vantage",
            provider_verbose="Alpha Vantage",
        )

        if self.member:
            procedure_instance.started_by = BaseProcedureInstance.STARTED_BY_MEMBER
            procedure_instance.member = self.member

        if self.schedule_instance:
            procedure_instance.started_by = BaseProcedureInstance.STARTED_BY_SCHEDULE
            procedure_instance.schedule_instance = self.schedule_instance

        procedure_instance.save()

        body = {}
        body["action"] = procedure_instance.action
        body["procedure"] = procedure_instance.id
        body["provider"] = procedure_instance.provider

        body["user"] = {
            "token": self.master_user.id,
            "base_api_url": self.master_user.space_code
        }

        body["error_code"] = None
        body["error_message"] = None

        body["data"] = {}

        body["data"]["date_from"] = str(self.procedure.price_date_from)
        body["data"]["date_to"] = str(self.procedure.price_date_to)
        body["data"]["items"] = []

        items_with_missing_parameters = []

        dates = get_list_of_dates_between_two_dates(
            date_from=self.procedure.price_date_from,
            date_to=self.procedure.price_date_to,
        )

        _l.debug("procedure id %s" % body["procedure"])

        empty_values = get_empty_values_for_dates(dates)

        full_items = []

        for item in items:
            if len(item.parameters):
                item_parameters = item.parameters.copy()
                item_parameters.pop()

                for date in dates:
                    with transaction.atomic():
                        try:
                            record = PricingProcedureAlphavInstrumentResult(
                                master_user=self.master_user,
                                procedure=procedure_instance,
                                instrument=item.instrument,
                                instrument_parameters=str(item_parameters),
                                pricing_policy=item.policy.pricing_policy,
                                pricing_scheme=item.pricing_scheme,
                                reference=item.parameters[0],
                                date=date,
                            )

                            record.save()

                        except Exception as e:
                            _l.debug("Cant create Result Record %s" % e)
                            pass

                item_obj = {
                    "reference": item.parameters[0],
                    "parameters": item_parameters,
                    "fields": [],
                }

                item_obj["fields"].append(
                    {"code": "close", "parameters": [], "values": empty_values}
                )

                full_items.append(item_obj)

            else:
                items_with_missing_parameters.append(item)

        _l.debug("full_items len: %s" % len(full_items))

        optimized_items = optimize_items(full_items)

        _l.debug("optimized_items len: %s" % len(optimized_items))

        body["data"]["items"] = optimized_items

        _l.debug(
            "items_with_missing_parameters %s" % len(items_with_missing_parameters)
        )
        # _l.debug('data %s' % data)

        _l.debug("self.procedure %s" % self.procedure.id)
        _l.debug("send request %s" % body)

        procedure_instance.request_data = body
        procedure_instance.save()

        try:
            self.transport.send_request(body)

        except Exception as e:
            _l.debug("Handle here")

            procedure_instance.status = PricingProcedureInstance.STATUS_ERROR
            procedure_instance.error_code = 500
            procedure_instance.error_message = (
                "Mediator is unavailable. Please try later."
            )

            procedure_instance.save()

            send_system_message(
                master_user=self.master_user,
                performed_by="System",
                type="error",
                description="Pricing Procedure %s. Error, Mediator is unavailable."
                % procedure_instance.procedure.name,
            )

    def process_to_cbonds_provider(self, items):
        _l.debug("Pricing Instrument Handler - Cbonds Provider: len %s" % len(items))

        procedure_instance = PricingProcedureInstance(
            procedure=self.procedure,
            parent_procedure_instance=self.parent_procedure,
            master_user=self.master_user,
            member=self.member,
            status=PricingProcedureInstance.STATUS_PENDING,
            action="cbonds_get_instrument_prices",
            provider="cbonds",
            action_verbose="Get Instrument Prices from Cbonds",
            provider_verbose="Cbonds",
        )

        if self.member:
            procedure_instance.started_by = BaseProcedureInstance.STARTED_BY_MEMBER
            procedure_instance.member = self.member

        if self.schedule_instance:
            procedure_instance.started_by = BaseProcedureInstance.STARTED_BY_SCHEDULE
            procedure_instance.schedule_instance = self.schedule_instance

        procedure_instance.save()

        try:
            body = {}
            body["action"] = procedure_instance.action
            body["procedure"] = procedure_instance.id
            body["provider"] = procedure_instance.provider

            body["user"] = {
                "token": self.master_user.id,
                "base_api_url": self.master_user.space_code
            }

            body["error_code"] = None
            body["error_message"] = None

            body["data"] = {}

            body["data"]["date_from"] = str(self.procedure.price_date_from)
            body["data"]["date_to"] = str(self.procedure.price_date_to)
            body["data"]["items"] = []

            items_with_missing_parameters = []

            dates = get_list_of_dates_between_two_dates(
                date_from=self.procedure.price_date_from,
                date_to=self.procedure.price_date_to,
            )

            empty_values = get_empty_values_for_dates(dates)

            _l.debug("procedure id %s" % body["procedure"])

            full_items = []

            _l.debug("items len: %s" % len(items))

            for item in items:
                if len(item.parameters):
                    item_parameters = item.parameters.copy()
                    item_parameters.pop()

                    for date in dates:
                        with transaction.atomic():
                            try:
                                record = PricingProcedureCbondsInstrumentResult(
                                    master_user=self.master_user,
                                    procedure=procedure_instance,
                                    instrument=item.instrument,
                                    instrument_parameters=str(item_parameters),
                                    pricing_policy=item.policy.pricing_policy,
                                    pricing_scheme=item.pricing_scheme,
                                    reference=item.parameters[0],
                                    date=date,
                                )

                                record.save()

                            except Exception as e:
                                _l.debug("Cant create Result Record %s" % e)
                                pass

                    item_obj = {
                        "reference": item.parameters[0],
                        "parameters": item_parameters,
                        "fields": [],
                    }

                    item_obj["fields"].append(
                        {"code": "close", "parameters": [], "values": empty_values}
                    )

                    item_obj["fields"].append(
                        {"code": "open", "parameters": [], "values": empty_values}
                    )

                    item_obj["fields"].append(
                        {"code": "high", "parameters": [], "values": empty_values}
                    )

                    item_obj["fields"].append(
                        {"code": "low", "parameters": [], "values": empty_values}
                    )

                    item_obj["fields"].append(
                        {"code": "volume", "parameters": [], "values": empty_values}
                    )

                    full_items.append(item_obj)

                else:
                    items_with_missing_parameters.append(item)

            _l.debug("full_items len: %s" % len(full_items))

            optimized_items = optimize_items(full_items)

            _l.debug("optimized_items len: %s" % len(optimized_items))

            body["data"]["items"] = optimized_items

            _l.debug(
                "items_with_missing_parameters %s" % len(items_with_missing_parameters)
            )
            # _l.debug('data %s' % data)

            # _l.debug('self.procedure %s' % self.procedure.id)
            # _l.debug('send request %s' % body)

            procedure_instance.request_data = body
            procedure_instance.save()

            try:
                self.transport.send_request(body)

            except Exception as e:
                procedure_instance.status = PricingProcedureInstance.STATUS_ERROR
                procedure_instance.error_code = 500
                procedure_instance.error_message = (
                    "Mediator is unavailable. Please try later."
                )

                procedure_instance.save()

                send_system_message(
                    master_user=self.master_user,
                    performed_by="System",
                    type="error",
                    description="Pricing Procedure %s. Error, Mediator is unavailable."
                    % procedure_instance.procedure.name,
                )
        except Exception as e:
            procedure_instance.status = PricingProcedureInstance.STATUS_ERROR
            procedure_instance.error_message = "Error %s" % e

            procedure_instance.save()

    def print_grouped_instruments(self):
        names = {
            1: "Skip",
            2: "Manual Pricing",  # DEPRECATED
            3: "Single Parameter Formula",
            4: "Multiple Parameter Formula",
            5: "Bloomberg",
            6: "Wtrade",
            7: "Alphav",
            8: "Bloomberg Forwards",
            9: "Cbonds",
            "has_linked_with_portfolio": "Has Linked with Portfolio",
        }

        for provider_id, items in self.instrument_items_grouped.items():
            _l.debug(
                "Pricing Instrument Handler - Provider %s: len: %s"
                % (names[provider_id], len(items))
            )
