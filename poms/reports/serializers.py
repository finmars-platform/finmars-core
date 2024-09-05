from __future__ import unicode_literals

import contextlib
import json
import logging
import time
import traceback
import uuid
from datetime import date, timedelta

from django.db.models import ForeignKey
from django.utils.translation import gettext_lazy
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from poms.reports.utils import generate_unique_key
from poms_app import settings

from poms.accounts.fields import AccountField
from poms.accounts.serializers import AccountViewSerializer
from poms.common.fields import ExpressionField
from poms.common.models import EXPRESSION_FIELD_LENGTH
from poms.common.serializers import (
    ModelWithUserCodeSerializer,
    ModelMetaSerializer,
    ModelWithTimeStampSerializer,
)
from poms.common.utils import date_now, date_yesterday
from poms.currencies.fields import CurrencyField, SystemCurrencyDefault
from poms.currencies.serializers import CurrencyViewSerializer
from poms.expressions_engine import formula
from poms.instruments.fields import (
    RegisterField,
    BundleField,
    PricingPolicyField,
    SystemPricingPolicyDefault,
)
from poms.instruments.models import CostMethod
from poms.instruments.serializers import (
    PricingPolicyViewSerializer,
    CostMethodSerializer,
)
from poms.portfolios.fields import PortfolioField
from poms.portfolios.serializers import PortfolioViewSerializer
from poms.reports.backend_reports_utils import BackendReportHelperService
from poms.reports.base_serializers import (
    ReportInstrumentSerializer,
    ReportInstrumentTypeSerializer,
    ReportCurrencySerializer,
    ReportPortfolioSerializer,
    ReportAccountSerializer,
    ReportAccountTypeSerializer,
    ReportStrategy1Serializer,
    ReportStrategy2Serializer,
    ReportStrategy3Serializer,
    ReportResponsibleSerializer,
    ReportCounterpartySerializer,
    ReportComplexTransactionSerializer,
    ReportCountrySerializer,
)
from poms.reports.common import Report, PerformanceReport, TransactionReport
from poms.reports.fields import (
    BalanceReportCustomFieldField,
    PLReportCustomFieldField,
    TransactionReportCustomFieldField,
    ReportCurrencyField,
    ReportPricingPolicyField,
)
from poms.reports.models import (
    BalanceReportCustomField,
    PLReportCustomField,
    TransactionReportCustomField,
    PLReportInstance,
    BalanceReportInstance,
    PerformanceReportInstance,
    PerformanceReportInstanceItem,
    TransactionReportInstance,
)
from poms.reports.serializers_helpers import (
    serialize_price_checker_item,
    serialize_price_checker_item_instrument,
    serialize_transaction_report_item,
    serialize_pl_report_item,
    serialize_report_item_instrument,
    serialize_balance_report_item,
)
from poms.strategies.fields import Strategy1Field, Strategy2Field, Strategy3Field
from poms.strategies.serializers import (
    Strategy1ViewSerializer,
    Strategy2ViewSerializer,
    Strategy3ViewSerializer,
)
from poms.transactions.models import TransactionClass
from poms.transactions.serializers import (
    TransactionClassSerializer,
    ComplexTransactionStatusSerializer,
)
from poms.users.fields import MasterUserField, HiddenMemberField
from poms_app import settings

_l = logging.getLogger("poms.reports")

_cf_list = [
    "id",
    "master_user",
    "name",
    "user_code",
    "expr",
    "value_type",
    "notes",
    "configuration_code",
]


class BalanceReportCustomFieldSerializer(ModelWithUserCodeSerializer):
    master_user = MasterUserField()
    expr = ExpressionField(
        max_length=EXPRESSION_FIELD_LENGTH,
        required=False,
        allow_blank=True,
        default='""',
    )

    class Meta:
        model = BalanceReportCustomField
        fields = _cf_list


class PLReportCustomFieldSerializer(ModelWithUserCodeSerializer):
    master_user = MasterUserField()
    expr = ExpressionField(
        max_length=EXPRESSION_FIELD_LENGTH,
        required=False,
        allow_blank=True,
        default='""',
    )

    class Meta:
        model = PLReportCustomField
        fields = _cf_list


class TransactionReportCustomFieldSerializer(ModelWithUserCodeSerializer):
    master_user = MasterUserField()
    expr = ExpressionField(
        max_length=EXPRESSION_FIELD_LENGTH,
        required=False,
        allow_blank=True,
        default='""',
    )

    class Meta:
        model = TransactionReportCustomField
        fields = _cf_list


class ReportSerializerWithLogs(serializers.Serializer):
    pass
    # def to_representation(self, instance):
    #     """
    #     Object instance -> Dict of primitive datatypes.
    #     """
    #     ret = OrderedDict()
    #     fields = self._readable_fields
    #
    #     st = time.perf_counter()
    #
    #     for field in fields:
    #         try:
    #             attribute = field.get_attribute(instance)
    #         except SkipField:
    #             continue
    #
    #         field_st = time.perf_counter()
    #
    #         # We skip `to_representation` for `None` values so that fields do
    #         # not have to explicitly deal with that case.
    #         #
    #         # For related fields with `use_pk_only_optimization` we need to
    #         # resolve the pk value.
    #         check_for_none = attribute.pk if isinstance(attribute, PKOnlyObject) else attribute
    #         if check_for_none is None:
    #             ret[field.field_name] = None
    #         else:
    #             ret[field.field_name] = field.to_representation(attribute)
    #
    #         if 'item_' in field.field_name:
    #             if hasattr(instance, 'is_report'):
    #                 result_time = "{:3.3f}".format(time.perf_counter() - field_st)
    #
    #                 _l.debug('field %s to representation done %s' % (field.field_name, result_time))
    #
    #     if hasattr(instance, 'is_report'):
    #         _l.debug('report to representation done %s' % "{:3.3f}".format(time.perf_counter() - st))
    #
    #     return ret


class ReportSerializer(ReportSerializerWithLogs):
    task_id = serializers.CharField(
        allow_null=True, allow_blank=True, required=False
    )  # something depreacted
    report_instance_id = serializers.CharField(
        read_only=True
    )  # needs for backend reports
    task_status = serializers.ReadOnlyField()

    master_user = MasterUserField()
    member = HiddenMemberField()

    save_report = serializers.BooleanField(default=False)

    pl_first_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text=gettext_lazy("First date for pl report"),
    )
    report_type = serializers.ChoiceField(read_only=True, choices=Report.TYPE_CHOICES)
    report_date = serializers.DateField(
        required=False,
        allow_null=True,
        default=date_now,
        help_text=gettext_lazy("Report date or second date for pl report"),
    )
    report_currency = ReportCurrencyField(
        required=False, allow_null=True, default=SystemCurrencyDefault()
    )
    pricing_policy = ReportPricingPolicyField()
    cost_method = serializers.PrimaryKeyRelatedField(
        queryset=CostMethod.objects, allow_null=True, allow_empty=True
    )

    calculation_group = serializers.ChoiceField(
        default=Report.CALCULATION_GROUP_NO_GROUPING,
        initial=Report.CALCULATION_GROUP_PORTFOLIO,
        choices=Report.CALCULATION_GROUP_CHOICES,
        required=False,
        help_text="Calculation grouping",
    )

    portfolio_mode = serializers.ChoiceField(
        default=Report.MODE_INDEPENDENT,
        initial=Report.MODE_INDEPENDENT,
        choices=Report.MODE_CHOICES,
        required=False,
        help_text="Portfolio consolidation",
    )
    account_mode = serializers.ChoiceField(
        default=Report.MODE_INDEPENDENT,
        initial=Report.MODE_INDEPENDENT,
        choices=Report.MODE_CHOICES,
        required=False,
        help_text="Account consolidation",
    )
    strategy1_mode = serializers.ChoiceField(
        default=Report.MODE_INDEPENDENT,
        initial=Report.MODE_INDEPENDENT,
        choices=Report.MODE_CHOICES,
        required=False,
        help_text="Strategy1 consolidation",
    )
    strategy2_mode = serializers.ChoiceField(
        default=Report.MODE_INDEPENDENT,
        initial=Report.MODE_INDEPENDENT,
        choices=Report.MODE_CHOICES,
        required=False,
        help_text="Strategy2 consolidation",
    )
    strategy3_mode = serializers.ChoiceField(
        default=Report.MODE_INDEPENDENT,
        initial=Report.MODE_INDEPENDENT,
        choices=Report.MODE_CHOICES,
        required=False,
        help_text="Strategy3 consolidation",
    )

    allocation_mode = serializers.ChoiceField(
        default=Report.MODE_INDEPENDENT,
        initial=Report.MODE_INDEPENDENT,
        choices=Report.MODE_CHOICES,
        required=False,
        help_text="Allocation consolidation",
    )

    only_numbers = serializers.BooleanField(default=False, initial=False)
    show_transaction_details = serializers.BooleanField(default=False, initial=False)
    show_balance_exposure_details = serializers.BooleanField(
        default=False, initial=False
    )
    approach_multiplier = serializers.FloatField(
        default=0.5, initial=0.5, min_value=0.0, max_value=1.0, required=False
    )
    allocation_detailing = serializers.BooleanField(default=True, initial=True)
    pl_include_zero = serializers.BooleanField(default=False, initial=False)
    custom_fields_to_calculate = serializers.CharField(
        allow_null=True, allow_blank=True, required=False
    )
    expression_iterations_count = serializers.IntegerField(
        default=1, initial=1, min_value=1, required=False
    )

    custom_fields = BalanceReportCustomFieldField(
        many=True, allow_empty=True, allow_null=True, required=False
    )

    execution_time = serializers.FloatField(
        allow_null=True, required=False, read_only=True
    )
    relation_prefetch_time = serializers.FloatField(
        allow_null=True, required=False, read_only=True
    )
    serialization_time = serializers.FloatField(
        allow_null=True, required=False, read_only=True
    )
    auth_time = serializers.FloatField(allow_null=True, required=False, read_only=True)

    portfolios = PortfolioField(
        many=True, required=False, allow_null=True, allow_empty=True
    )
    accounts = AccountField(
        many=True, required=False, allow_null=True, allow_empty=True
    )
    accounts_position = AccountField(
        many=True, required=False, allow_null=True, allow_empty=True
    )
    accounts_cash = AccountField(
        many=True, required=False, allow_null=True, allow_empty=True
    )
    strategies1 = Strategy1Field(
        many=True, required=False, allow_null=True, allow_empty=True
    )
    strategies2 = Strategy2Field(
        many=True, required=False, allow_null=True, allow_empty=True
    )
    strategies3 = Strategy3Field(
        many=True, required=False, allow_null=True, allow_empty=True
    )
    transaction_classes = serializers.PrimaryKeyRelatedField(
        queryset=TransactionClass.objects.all(),
        many=True,
        required=False,
        allow_null=True,
        allow_empty=True,
    )
    date_field = serializers.ChoiceField(
        required=False,
        allow_null=True,
        choices=(
            ("transaction_date", gettext_lazy("Transaction date")),
            ("accounting_date", gettext_lazy("Accounting date")),
            ("date", gettext_lazy("Date")),
            ("cash_date", gettext_lazy("Cash date")),
            ("user_date_1", gettext_lazy("User Date 1")),
            ("user_date_2", gettext_lazy("User Date 2")),
            ("user_date_3", gettext_lazy("User Date 3")),
            ("user_date_4", gettext_lazy("User Date 4")),
            ("user_date_5", gettext_lazy("User Date 5")),
            ("user_date_6", gettext_lazy("User Date 6")),
            ("user_date_7", gettext_lazy("User Date 7")),
            ("user_date_8", gettext_lazy("User Date 8")),
            ("user_date_9", gettext_lazy("User Date 9")),
            ("user_date_10", gettext_lazy("User Date 10")),
        ),
    )

    pricing_policy_object = PricingPolicyViewSerializer(
        source="pricing_policy", read_only=True
    )
    report_currency_object = CurrencyViewSerializer(
        source="report_currency", read_only=True
    )
    cost_method_object = CostMethodSerializer(source="cost_method", read_only=True)
    portfolios_object = PortfolioViewSerializer(
        source="portfolios", read_only=True, many=True
    )
    accounts_object = AccountViewSerializer(
        source="accounts", read_only=True, many=True
    )
    accounts_position_object = AccountViewSerializer(
        source="accounts_position", read_only=True, many=True
    )
    accounts_cash_object = AccountViewSerializer(
        source="accounts_cash", read_only=True, many=True
    )
    strategies1_object = Strategy1ViewSerializer(
        source="strategies1", read_only=True, many=True
    )
    strategies2_object = Strategy2ViewSerializer(
        source="strategies2", read_only=True, many=True
    )
    strategies3_object = Strategy3ViewSerializer(
        source="strategies3", read_only=True, many=True
    )
    custom_fields_object = BalanceReportCustomFieldSerializer(
        source="custom_fields", read_only=True, many=True
    )
    transaction_classes_object = TransactionClassSerializer(
        source="transaction_classes", read_only=True, many=True
    )

    # transactions = ReportTransactionSerializer(many=True, read_only=True)
    # items = ReportItemSerializer(many=True, read_only=True)

    item_instruments = ReportInstrumentSerializer(many=True, read_only=True)
    item_instrument_types = ReportInstrumentTypeSerializer(many=True, read_only=True)
    item_countries = ReportCountrySerializer(many=True, read_only=True)
    item_currencies = ReportCurrencySerializer(many=True, read_only=True)
    item_portfolios = ReportPortfolioSerializer(many=True, read_only=True)
    item_accounts = ReportAccountSerializer(many=True, read_only=True)
    item_account_types = ReportAccountTypeSerializer(many=True, read_only=True)
    item_strategies1 = ReportStrategy1Serializer(many=True, read_only=True)
    item_strategies2 = ReportStrategy2Serializer(many=True, read_only=True)
    item_strategies3 = ReportStrategy3Serializer(many=True, read_only=True)
    # Deprecated
    # item_currency_fx_rates = ReportCurrencyHistorySerializer(many=True, read_only=True)
    # item_instrument_pricings = ReportPriceHistorySerializer(many=True, read_only=True)
    # item_instrument_accruals = ReportAccrualCalculationScheduleSerializer(many=True, read_only=True)

    frontend_request_options = serializers.JSONField(
        allow_null=True, required=False
    )  # for backend report calculation mode

    # Pagination settings
    count = serializers.IntegerField(default=1, initial=1, min_value=1, required=False)
    page = serializers.IntegerField(default=1, initial=1, min_value=1, required=False)
    page_size = serializers.IntegerField(
        default=40, initial=40, min_value=1, required=False
    )

    created_at = serializers.DateTimeField(read_only=True)

    def __init__(self, *args, **kwargs):
        super(ReportSerializer, self).__init__(*args, **kwargs)

    def validate(self, attrs):
        _l.debug("Report Serializer validate start")

        if not attrs.get("report_date", None):
            if settings.DEBUG:
                attrs["report_date"] = date(2017, 2, 12)
            else:
                attrs["report_date"] = date_now() - timedelta(days=1)

        pl_first_date = attrs.get("pl_first_date", None)
        if pl_first_date and pl_first_date >= attrs["report_date"]:
            raise ValidationError(
                gettext_lazy('"pl_first_date" must be lesser than "report_date"')
            )

        # if settings.DEBUG:
        #     if not attrs.get('pl_first_date', None):
        #         attrs['pl_first_date'] = date(2017, 2, 10)

        if not attrs.get("report_currency", None):
            attrs["report_currency"] = attrs["master_user"].system_currency

        if not attrs.get("cost_method", None):
            attrs["cost_method"] = CostMethod.objects.get(pk=CostMethod.AVCO)

        return attrs

    def create(self, validated_data):
        return Report(**validated_data)

    def _extract_names(self, item, data):
        names = item.copy()
        names.update(
            {
                "report_currency": data["report_currency"],
                "report_date": data["report_date"],
                "pl_first_date": data["pl_first_date"],
                "cost_method": data["cost_method"],
                "pricing_policy": data["pricing_policy"],
                "portfolio_mode": data["portfolio_mode"],
                "account_mode": data["account_mode"],
            }
        )
        return names

    def _get_item_dict(self, data, key):
        return {o["id"]: o for o in data[key]}

    def _set_object(self, names, pk_attr, objs):
        if pk_attr in names:
            pk = names[pk_attr]
            if pk is not None:
                with contextlib.suppress(KeyError):
                    names[f"{pk_attr}_object"] = objs[pk]

    def evaluate_expression(self, expr, names, context):
        try:
            return formula.safe_eval(expr, names=names, context=context)
        except formula.InvalidExpression as e:
            _l.debug(f"evaluate_expression {e} traceback {traceback.format_exc()}")
            return gettext_lazy("Invalid expression")

    def process_custom_field(self, cf, value):
        expr = cf["expr"]
        if expr:
            if cf["value_type"] == 10:
                return self.evaluate_expression(
                    "str(item)", names={"item": value}, context=self.context
                )
            elif cf["value_type"] == 20:
                return self.evaluate_expression(
                    "float(item)", names={"item": value}, context=self.context
                )
            elif cf["value_type"] == 40:
                return self.evaluate_expression(
                    "parse_date(item, '%d/%m/%Y')",
                    names={"item": value},
                    context=self.context,
                )
        return None

    def to_representation(self, instance):
        to_representation_st = time.perf_counter()

        instance.is_report = True

        data = super(ReportSerializer, self).to_representation(instance)

        _l.debug(
            "ReportSerializer to_representation_st done: %s"
            % "{:3.3f}".format(time.perf_counter() - to_representation_st)
        )

        # _l.debug('data["custom_fields_to_calculate"] %s' % data["custom_fields_to_calculate"])

        st = time.perf_counter()

        dict_st = time.perf_counter()

        item_dicts = {
            "portfolio": self._get_item_dict(data, "item_portfolios"),
            "account": self._get_item_dict(data, "item_accounts"),
            "strategy1": self._get_item_dict(data, "item_strategies1"),
            "strategy2": self._get_item_dict(data, "item_strategies2"),
            "strategy3": self._get_item_dict(data, "item_strategies3"),
            "instrument": self._get_item_dict(data, "item_instruments"),
            "currency": self._get_item_dict(data, "item_currencies"),
            "pricing_currency": self._get_item_dict(data, "item_currencies"),
            "exposure_currency": self._get_item_dict(data, "item_currencies"),
            "allocation": self._get_item_dict(data, "item_instruments"),
            "mismatch_portfolio": self._get_item_dict(data, "item_portfolios"),
            "mismatch_account": self._get_item_dict(data, "item_accounts"),
        }

        _l.debug(
            "ReportSerializer custom columns dict  done: %s"
            % "{:3.3f}".format(time.perf_counter() - dict_st)
        )

        custom_fields = data["custom_fields_object"]

        calc_st = time.perf_counter()

        if len(data["custom_fields_to_calculate"]) and custom_fields:
            items = data["items"]

            for item in items:
                item_st = time.perf_counter()

                names = self._extract_names(item, data)
                for name, item_dict in item_dicts.items():
                    self._set_object(names, name, item_dict)

                names = formula.value_prepare(names)

                cfv = []

                custom_fields_names = {}

                # _l.debug('names %s' % names)

                for _ in range(data["expression_iterations_count"]):
                    for cf in custom_fields:
                        if cf["name"] in data["custom_fields_to_calculate"]:
                            expr = cf["expr"]
                            value = (
                                self.evaluate_expression(
                                    expr, names, context=self.context
                                )
                                if expr
                                else None
                            )
                            if cf[
                                "user_code"
                            ] not in custom_fields_names or custom_fields_names[
                                cf["user_code"]
                            ] in [
                                None,
                                gettext_lazy("Invalid expression"),
                            ]:
                                custom_fields_names[cf["user_code"]] = value

                names["custom_fields"] = custom_fields_names

                for key, value in custom_fields_names.items():
                    for cf in custom_fields:
                        if cf["user_code"] == key:
                            value = self.process_custom_field(cf, value)
                            cfv.append(
                                {
                                    "custom_field": cf["id"],
                                    "user_code": cf["user_code"],
                                    "value": value,
                                }
                            )

                item["custom_fields"] = cfv

        _l.debug(
            "ReportSerializer custom columns calc_st done: %s"
            % "{:3.3f}".format(time.perf_counter() - calc_st)
        )

        _l.debug(
            "ReportSerializer custom columns done: %s"
            % "{:3.3f}".format(time.perf_counter() - st)
        )

        data["serialization_time"] = float(
            "{:3.3f}".format(time.perf_counter() - to_representation_st)
        )

        return data


class BalanceReportLightSerializer(ReportSerializerWithLogs):

    report_instance_id = serializers.CharField(read_only=True)
    task_status = serializers.ReadOnlyField()

    master_user = MasterUserField()
    member = HiddenMemberField()

    save_report = serializers.BooleanField(default=False)

    report_type = serializers.ChoiceField(read_only=True, choices=Report.TYPE_CHOICES)
    report_date = serializers.DateField(
        required=False,
        allow_null=True,
        default=date_now,
        help_text=gettext_lazy("Report date or second date for pl report"),
    )
    report_currency = ReportCurrencyField(
        required=False, allow_null=True, default=SystemCurrencyDefault()
    )
    pricing_policy = ReportPricingPolicyField()
    cost_method = serializers.PrimaryKeyRelatedField(
        queryset=CostMethod.objects, allow_null=True, allow_empty=True
    )

    calculation_group = serializers.ChoiceField(
        default=Report.CALCULATION_GROUP_NO_GROUPING,
        initial=Report.CALCULATION_GROUP_PORTFOLIO,
        choices=Report.CALCULATION_GROUP_CHOICES,
        required=False,
        help_text="Calculation grouping",
    )

    portfolio_mode = serializers.ChoiceField(
        default=Report.MODE_INDEPENDENT,
        initial=Report.MODE_INDEPENDENT,
        choices=Report.MODE_CHOICES,
        required=False,
        help_text="Portfolio consolidation",
    )
    account_mode = serializers.ChoiceField(
        default=Report.MODE_INDEPENDENT,
        initial=Report.MODE_INDEPENDENT,
        choices=Report.MODE_CHOICES,
        required=False,
        help_text="Account consolidation",
    )
    strategy1_mode = serializers.ChoiceField(
        default=Report.MODE_INDEPENDENT,
        initial=Report.MODE_INDEPENDENT,
        choices=Report.MODE_CHOICES,
        required=False,
        help_text="Strategy1 consolidation",
    )
    strategy2_mode = serializers.ChoiceField(
        default=Report.MODE_INDEPENDENT,
        initial=Report.MODE_INDEPENDENT,
        choices=Report.MODE_CHOICES,
        required=False,
        help_text="Strategy2 consolidation",
    )
    strategy3_mode = serializers.ChoiceField(
        default=Report.MODE_INDEPENDENT,
        initial=Report.MODE_INDEPENDENT,
        choices=Report.MODE_CHOICES,
        required=False,
        help_text="Strategy3 consolidation",
    )

    allocation_mode = serializers.ChoiceField(
        default=Report.MODE_INDEPENDENT,
        initial=Report.MODE_INDEPENDENT,
        choices=Report.MODE_CHOICES,
        required=False,
        help_text="Allocation consolidation",
    )

    only_numbers = serializers.BooleanField(default=False, initial=False)

    execution_time = serializers.FloatField(
        allow_null=True, required=False, read_only=True
    )
    relation_prefetch_time = serializers.FloatField(
        allow_null=True, required=False, read_only=True
    )
    serialization_time = serializers.FloatField(
        allow_null=True, required=False, read_only=True
    )
    auth_time = serializers.FloatField(allow_null=True, required=False, read_only=True)

    # frontend_request_options = serializers.JSONField(
    #     allow_null=True, required=False
    # )  # for backend report calculation mode

    items = serializers.SerializerMethodField()

    def create(self, validated_data):
        return Report(**validated_data)

    def get_items(self, obj):
        return [serialize_balance_report_item(item) for item in obj.items]

    def to_representation(self, instance):
        # No need for now, but do not delete

        to_representation_st = time.perf_counter()

        data = super(BalanceReportLightSerializer, self).to_representation(instance)

        data["serialization_time"] = float(
            "{:3.3f}".format(time.perf_counter() - to_representation_st)
        )

        return data


class BalanceReportSerializer(ReportSerializer):
    calculate_pl = serializers.BooleanField(default=True, initial=True)

    items = serializers.SerializerMethodField()

    item_instruments = serializers.SerializerMethodField()

    def get_items(self, obj):
        return [serialize_balance_report_item(item) for item in obj.items]

    def get_item_instruments(self, obj):
        return [serialize_report_item_instrument(item) for item in obj.item_instruments]

    def to_representation(self, instance):
        # No need for now, but do not delete

        to_representation_st = time.perf_counter()

        data = super(BalanceReportSerializer, self).to_representation(instance)

        data["serialization_time"] = float(
            "{:3.3f}".format(time.perf_counter() - to_representation_st)
        )

        return data


class SummarySerializer(serializers.Serializer):
    date_from = serializers.DateField(
        required=False,
        allow_null=True,
        default=date_yesterday,
        help_text=gettext_lazy("Date from"),
    )

    date_to = serializers.DateField(
        required=False,
        allow_null=True,
        default=date_now,
        help_text=gettext_lazy("Date from"),
    )

    currency = CurrencyField(
        required=False, allow_null=True, default=SystemCurrencyDefault()
    )
    pricing_policy = PricingPolicyField(
        required=False, allow_null=True, default=SystemPricingPolicyDefault()
    )
    portfolios = PortfolioField(
        many=True, required=False, allow_null=True, allow_empty=True
    )
    calculate_new = serializers.BooleanField(default=False, initial=False)
    allocation_mode = serializers.IntegerField(default=0, initial=0)


class PLReportSerializer(ReportSerializer):
    custom_fields = PLReportCustomFieldField(
        many=True, allow_empty=True, allow_null=True, required=False
    )

    items = serializers.SerializerMethodField()

    item_instruments = serializers.SerializerMethodField()

    period_type = serializers.ChoiceField(
        allow_null=True,
        choices=Report.PERIOD_TYPE_CHOICES,
        allow_blank=True,
        required=False,
    )

    def get_items(self, obj):
        return [serialize_pl_report_item(item) for item in obj.items]

    def get_item_instruments(self, obj):
        _l.debug("get item instruments here")

        return [serialize_report_item_instrument(item) for item in obj.item_instruments]

    def to_representation(self, instance):
        return super(PLReportSerializer, self).to_representation(instance)


class TransactionReportSerializer(ReportSerializerWithLogs):
    report_instance_id = serializers.CharField(
        allow_null=True, allow_blank=True, required=False
    )
    task_id = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    task_status = serializers.ReadOnlyField()

    master_user = MasterUserField()
    member = HiddenMemberField()

    date_field = serializers.ChoiceField(
        required=False,
        allow_null=True,
        choices=(
            ("transaction_date", gettext_lazy("Transaction date")),
            ("accounting_date", gettext_lazy("Accounting date")),
            ("cash_date", gettext_lazy("Cash date")),
            ("date", gettext_lazy("Date")),
            ("user_date_1", gettext_lazy("User Date 1")),
            ("user_date_2", gettext_lazy("User Date 2")),
            ("user_date_3", gettext_lazy("User Date 3")),
            ("user_date_4", gettext_lazy("User Date 4")),
            ("user_date_5", gettext_lazy("User Date 5")),
            # ('user_date_6', gettext_lazy('User Date 6')),
            # ('user_date_7', gettext_lazy('User Date 7')),
            # ('user_date_8', gettext_lazy('User Date 8')),
            # ('user_date_9', gettext_lazy('User Date 9')),
            # ('user_date_10', gettext_lazy('User Date 10')),
        ),
    )

    depth_level = serializers.ChoiceField(
        required=False,
        allow_null=True,
        choices=(
            ("complex_transaction", gettext_lazy("Complex Transaction")),
            ("base_transaction", gettext_lazy("Base Transaction")),
            ("entry", gettext_lazy("Entry")),
        ),
    )
    expression_iterations_count = serializers.IntegerField(
        default=1, initial=1, min_value=1, required=False
    )
    begin_date = serializers.DateField(
        required=False,
        allow_null=True,
        initial=date_now() - timedelta(days=365),
        default=date_now() - timedelta(days=365),
    )
    end_date = serializers.DateField(
        required=False, allow_null=True, initial=date_now, default=date_now
    )
    portfolios = PortfolioField(
        many=True, required=False, allow_null=True, allow_empty=True
    )
    bundle = BundleField(required=False, allow_null=True, allow_empty=True)
    accounts = AccountField(
        many=True, required=False, allow_null=True, allow_empty=True
    )
    accounts_position = AccountField(
        many=True, required=False, allow_null=True, allow_empty=True
    )
    accounts_cash = AccountField(
        many=True, required=False, allow_null=True, allow_empty=True
    )
    strategies1 = Strategy1Field(
        many=True, required=False, allow_null=True, allow_empty=True
    )
    strategies2 = Strategy2Field(
        many=True, required=False, allow_null=True, allow_empty=True
    )
    strategies3 = Strategy3Field(
        many=True, required=False, allow_null=True, allow_empty=True
    )
    custom_fields = TransactionReportCustomFieldField(
        many=True, allow_empty=True, allow_null=True, required=False
    )
    custom_fields_to_calculate = serializers.CharField(
        default="", allow_null=True, allow_blank=True, required=False
    )
    custom_fields_object = TransactionReportCustomFieldSerializer(
        source="custom_fields", read_only=True, many=True
    )

    complex_transaction_statuses_filter = serializers.CharField(
        default="", allow_null=True, allow_blank=True, required=False
    )

    portfolios_object = PortfolioViewSerializer(
        source="portfolios", read_only=True, many=True
    )
    accounts_object = AccountViewSerializer(
        source="accounts", read_only=True, many=True
    )
    accounts_position_object = AccountViewSerializer(
        source="accounts_position", read_only=True, many=True
    )
    accounts_cash_object = AccountViewSerializer(
        source="accounts_cash", read_only=True, many=True
    )
    strategies1_object = Strategy1ViewSerializer(
        source="strategies1", read_only=True, many=True
    )
    strategies2_object = Strategy2ViewSerializer(
        source="strategies2", read_only=True, many=True
    )
    strategies3_object = Strategy3ViewSerializer(
        source="strategies3", read_only=True, many=True
    )

    execution_time = serializers.FloatField(
        allow_null=True, required=False, read_only=True
    )
    relation_prefetch_time = serializers.FloatField(
        allow_null=True, required=False, read_only=True
    )
    serialization_time = serializers.FloatField(
        allow_null=True, required=False, read_only=True
    )
    auth_time = serializers.FloatField(allow_null=True, required=False, read_only=True)

    items = serializers.SerializerMethodField()
    item_transaction_classes = TransactionClassSerializer(many=True, read_only=True)
    item_complex_transactions = ReportComplexTransactionSerializer(
        many=True, read_only=True
    )
    item_complex_transaction_status = ComplexTransactionStatusSerializer(
        many=True, read_only=True
    )
    item_instruments = ReportInstrumentSerializer(many=True, read_only=True)
    item_instrument_types = ReportInstrumentTypeSerializer(many=True, read_only=True)
    item_countries = ReportCountrySerializer(many=True, read_only=True)
    item_currencies = ReportCurrencySerializer(many=True, read_only=True)
    item_portfolios = ReportPortfolioSerializer(many=True, read_only=True)
    item_accounts = ReportAccountSerializer(many=True, read_only=True)
    item_account_types = ReportAccountTypeSerializer(many=True, read_only=True)
    item_strategies1 = ReportStrategy1Serializer(many=True, read_only=True)
    item_strategies2 = ReportStrategy2Serializer(many=True, read_only=True)
    item_strategies3 = ReportStrategy3Serializer(many=True, read_only=True)
    item_responsibles = ReportResponsibleSerializer(many=True, read_only=True)
    item_counterparties = ReportCounterpartySerializer(many=True, read_only=True)

    filters = serializers.JSONField(
        allow_null=True, required=False
    )  # for backend filters in transactions report
    frontend_request_options = serializers.JSONField(
        allow_null=True, required=False
    )  # for backend report calculation mode

    # Pagination settings
    count = serializers.IntegerField(default=1, initial=1, min_value=1, required=False)
    page = serializers.IntegerField(default=1, initial=1, min_value=1, required=False)
    page_size = serializers.IntegerField(
        default=40, initial=40, min_value=1, required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def create(self, validated_data):
        return TransactionReport(**validated_data)

    def get_items(self, obj):
        return [serialize_transaction_report_item(item) for item in obj.items]

    def to_representation(self, instance):
        to_representation_st = time.perf_counter()

        instance.is_report = True

        data = super(TransactionReportSerializer, self).to_representation(instance)

        _l.debug(
            "TransactionReportSerializer to_representation_st done: %s"
            % "{:3.3f}".format(time.perf_counter() - to_representation_st)
        )

        st = time.perf_counter()

        items = data["items"]
        custom_fields = data["custom_fields_object"]

        # _l.debug('custom_fields_to_calculate %s' % data["custom_fields_to_calculate"])
        # _l.debug('custom_fields %s' % data["custom_fields_object"])

        if len(data["custom_fields_to_calculate"]) and (custom_fields and items):
            item_transaction_classes = {
                o["id"]: o for o in data["item_transaction_classes"]
            }
            item_complex_transactions = {
                o["id"]: o for o in data["item_complex_transactions"]
            }
            item_instruments = {o["id"]: o for o in data["item_instruments"]}
            item_currencies = {o["id"]: o for o in data["item_currencies"]}
            item_portfolios = {o["id"]: o for o in data["item_portfolios"]}
            item_accounts = {o["id"]: o for o in data["item_accounts"]}
            item_strategies1 = {o["id"]: o for o in data["item_strategies1"]}
            item_strategies2 = {o["id"]: o for o in data["item_strategies2"]}
            item_strategies3 = {o["id"]: o for o in data["item_strategies3"]}
            item_responsibles = {o["id"]: o for o in data["item_responsibles"]}
            item_counterparties = {o["id"]: o for o in data["item_counterparties"]}

            def _set_object(names, pk_attr, objs):
                pk = names[pk_attr]
                if pk is not None:
                    with contextlib.suppress(KeyError):
                        names[f"{pk_attr}_object"] = objs[pk]
                        # names[pk_attr] = objs[pk]

            for item in items:
                names = {}

                for key, value in item.items():
                    names[key] = value

                _set_object(names, "complex_transaction", item_complex_transactions)
                _set_object(names, "transaction_class", item_transaction_classes)
                _set_object(names, "instrument", item_instruments)
                _set_object(names, "transaction_currency", item_currencies)
                _set_object(names, "settlement_currency", item_currencies)
                _set_object(names, "portfolio", item_portfolios)
                _set_object(names, "account_cash", item_accounts)
                _set_object(names, "account_position", item_accounts)
                _set_object(names, "account_interim", item_accounts)
                _set_object(names, "strategy1_position", item_strategies1)
                _set_object(names, "strategy1_cash", item_strategies1)
                _set_object(names, "strategy2_position", item_strategies2)
                _set_object(names, "strategy2_cash", item_strategies2)
                _set_object(names, "strategy3_position", item_strategies3)
                _set_object(names, "strategy3_cash", item_strategies3)
                _set_object(names, "responsible", item_responsibles)
                _set_object(names, "counterparty", item_counterparties)
                _set_object(names, "linked_instrument", item_instruments)
                _set_object(names, "allocation_balance", item_instruments)
                _set_object(names, "allocation_pl", item_instruments)

                names = formula.value_prepare(names)

                cfv = []

                custom_fields_names = {}

                # for i in range(5):
                for i in range(data["expression_iterations_count"]):
                    for cf in custom_fields:
                        if cf["name"] in data["custom_fields_to_calculate"]:
                            expr = cf["expr"]

                            if expr:
                                try:
                                    value = formula.safe_eval(
                                        expr, names=names, context=self.context
                                    )
                                except formula.InvalidExpression:
                                    value = gettext_lazy("Invalid expression")
                            else:
                                value = None

                            if cf["user_code"] not in custom_fields_names:
                                custom_fields_names[cf["user_code"]] = value
                            else:
                                if custom_fields_names[
                                    cf["user_code"]
                                ] is None or custom_fields_names[
                                    cf["user_code"]
                                ] == gettext_lazy(
                                    "Invalid expression"
                                ):
                                    custom_fields_names[cf["user_code"]] = value

                    names["custom_fields"] = custom_fields_names

                for key, value in custom_fields_names.items():
                    for cf in custom_fields:
                        if cf["user_code"] == key:
                            expr = cf["expr"]

                            if cf["value_type"] == 10:
                                if expr:
                                    try:
                                        value = formula.safe_eval(
                                            "str(item)",
                                            names={"item": value},
                                            context=self.context,
                                        )
                                    except formula.InvalidExpression:
                                        value = gettext_lazy("Invalid expression")
                                else:
                                    value = None

                            elif cf["value_type"] == 20:
                                if expr:
                                    try:
                                        value = formula.safe_eval(
                                            "float(item)",
                                            names={"item": value},
                                            context=self.context,
                                        )
                                    except formula.InvalidExpression:
                                        value = gettext_lazy("Invalid expression")
                                else:
                                    value = None
                            elif cf["value_type"] == 40:
                                if expr:
                                    try:
                                        value = formula.safe_eval(
                                            "parse_date(item, '%d/%m/%Y')",
                                            names={"item": value},
                                            context=self.context,
                                        )
                                    except formula.InvalidExpression:
                                        value = gettext_lazy("Invalid expression")
                                else:
                                    value = None

                            cfv.append(
                                {
                                    "custom_field": cf["id"],
                                    "user_code": cf["user_code"],
                                    "value": value,
                                }
                            )

                item["custom_fields"] = cfv

        data["serialization_time"] = float(
            "{:3.3f}".format(time.perf_counter() - to_representation_st)
        )

        return data


class PerformanceReportItemSerializer(serializers.Serializer):
    id = serializers.ReadOnlyField()

    date_from = serializers.CharField(read_only=True)
    date_to = serializers.CharField(read_only=True)

    begin_nav = serializers.FloatField(read_only=True)
    end_nav = serializers.FloatField(read_only=True)

    cash_flow = serializers.FloatField(read_only=True)
    cash_inflow = serializers.FloatField(read_only=True)
    cash_outflow = serializers.FloatField(read_only=True)
    nav = serializers.FloatField(read_only=True)
    instrument_return = serializers.FloatField(read_only=True)
    cumulative_return = serializers.FloatField(read_only=True)

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("read_only", True)

        super(PerformanceReportItemSerializer, self).__init__(*args, **kwargs)


class PerformanceReportSerializer(serializers.Serializer):
    master_user = MasterUserField()
    member = HiddenMemberField()

    save_report = serializers.BooleanField(default=False)

    begin_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    calculation_type = serializers.ChoiceField(
        allow_null=True,
        initial=PerformanceReport.CALCULATION_TYPE_MODIFIED_DIETZ,
        default=PerformanceReport.CALCULATION_TYPE_MODIFIED_DIETZ,
        choices=PerformanceReport.CALCULATION_TYPE_CHOICES,
        allow_blank=True,
        required=False,
    )
    period_type = serializers.ChoiceField(
        allow_null=True,
        initial=PerformanceReport.PERIOD_TYPE_YTD,
        default=PerformanceReport.PERIOD_TYPE_YTD,
        choices=PerformanceReport.PERIOD_TYPE_CHOICES,
        allow_blank=True,
        required=False,
    )

    segmentation_type = serializers.ChoiceField(
        allow_null=True,
        initial=PerformanceReport.SEGMENTATION_TYPE_MONTHS,
        default=PerformanceReport.SEGMENTATION_TYPE_MONTHS,
        choices=PerformanceReport.SEGMENTATION_TYPE_CHOICES,
        allow_blank=True,
        required=False,
    )
    adjustment_type = serializers.ChoiceField(
        allow_null=True,
        initial=PerformanceReport.ADJUSTMENT_TYPE_ORIGINAL,
        default=PerformanceReport.ADJUSTMENT_TYPE_ORIGINAL,
        choices=PerformanceReport.ADJUSTMENT_TYPE_CHOICES,
        allow_blank=True,
        required=False,
    )
    registers = RegisterField(
        many=True, required=False, allow_null=True, allow_empty=True
    )
    bundle = BundleField(required=False, allow_null=True, allow_empty=True)
    report_currency = CurrencyField(
        required=False, allow_null=True, default=SystemCurrencyDefault()
    )
    report_currency_object = CurrencyViewSerializer(
        source="report_currency", read_only=True
    )
    error_message = serializers.CharField(read_only=True)

    items = PerformanceReportItemSerializer(many=True, read_only=True)
    raw_items = serializers.JSONField(allow_null=True, required=False, read_only=True)
    execution_log = serializers.JSONField(
        allow_null=True, required=False, read_only=True
    )
    begin_nav = serializers.ReadOnlyField()
    end_nav = serializers.ReadOnlyField()
    grand_return = serializers.ReadOnlyField()
    grand_cash_flow_weighted = serializers.ReadOnlyField()
    grand_cash_flow = serializers.ReadOnlyField()
    grand_cash_inflow = serializers.ReadOnlyField()
    grand_cash_outflow = serializers.ReadOnlyField()
    grand_nav = serializers.ReadOnlyField()

    grand_absolute_pl = serializers.ReadOnlyField()

    def __init__(self, *args, **kwargs):
        super(PerformanceReportSerializer, self).__init__(*args, **kwargs)

    def create(self, validated_data):
        return PerformanceReport(**validated_data)

    def to_representation(self, instance):
        to_representation_st = time.perf_counter()

        data = super(PerformanceReportSerializer, self).to_representation(instance)

        report_uuid = str(uuid.uuid4())

        if instance.save_report:
            register_ids_list = []
            register_names_list = []
            register_ids = ""
            register_names = ""

            for r in instance.registers:
                register_ids_list.append(str(r.id))
                register_names_list.append(str(r.name))

            register_ids = ", ".join(register_ids_list)
            register_names = ", ".join(register_names_list)

            report_instance_name = ""
            if self.instance.report_instance_name:
                report_instance_name = self.instance.report_instance_name
            else:
                report_instance_name = report_uuid

            report_instance = None

            try:
                report_instance = PerformanceReportInstance.objects.get(
                    master_user=instance.master_user,
                    member=instance.member,
                    owner=instance.member,
                    user_code=report_instance_name,
                )

            except Exception as e:
                report_instance = PerformanceReportInstance.objects.create(
                    master_user=instance.master_user,
                    member=instance.member,
                    owner=instance.member,
                    user_code=report_instance_name,
                    name=report_instance_name,
                    short_name=report_instance_name,
                    report_currency=instance.report_currency,
                    begin_date=instance.begin_date,
                    end_date=instance.end_date,
                )

            report_instance.report_currency = instance.report_currency
            report_instance.begin_date = instance.begin_date
            report_instance.end_date = instance.end_date
            report_instance.calculation_type = instance.calculation_type
            report_instance.segmentation_type = instance.segmentation_type
            report_instance.registers = register_ids
            report_instance.registers_names = register_names
            report_instance.begin_nav = instance.begin_nav
            report_instance.end_nav = instance.end_nav
            report_instance.grand_return = instance.grand_return
            report_instance.grand_cash_flow = instance.grand_cash_flow
            report_instance.grand_cash_inflow = instance.grand_cash_inflow
            report_instance.grand_cash_outflow = instance.grand_cash_outflow
            report_instance.grand_nav = instance.grand_nav
            report_instance.grand_absolute_pl = instance.grand_absolute_pl

            report_instance.report_uuid = report_uuid
            report_instance.save()

            PerformanceReportInstanceItem.objects.filter(
                report_instance=report_instance
            ).delete()

            for item in data["items"]:
                instance_item = PerformanceReportInstanceItem(
                    report_instance=report_instance,
                    master_user=instance.master_user,
                    member=instance.member,
                    owner=instance.member,
                    begin_date=instance.begin_date,
                    end_date=instance.end_date,
                    calculation_type=instance.calculation_type,
                    segmentation_type=instance.segmentation_type,
                    registers=register_ids,
                    registers_names=register_names,
                    report_currency=instance.report_currency,
                )

                for field in PerformanceReportInstanceItem._meta.fields:
                    if field.name not in ["id"] and field.name in item:
                        if isinstance(field, ForeignKey):
                            try:
                                setattr(
                                    instance_item, f"{field.name}_id", item[field.name]
                                )
                            except Exception as e:
                                print(f"exception field {field.name} : {e}")
                                setattr(instance_item, field.name, None)

                        else:
                            try:
                                setattr(instance_item, field.name, item[field.name])
                            except Exception as e:
                                print(f"exception field {field.name} : {e}")
                                setattr(instance_item, field.name, None)

                instance_item.save()

        data["report_uuid"] = report_uuid

        data["serialization_time"] = float(
            "{:3.3f}".format(time.perf_counter() - to_representation_st)
        )

        return data


class PriceHistoryCheckSerializer(ReportSerializerWithLogs):

    master_user = MasterUserField()
    member = HiddenMemberField()

    pl_first_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text=gettext_lazy("First date for pl report"),
    )
    report_type = serializers.ChoiceField(read_only=True, choices=Report.TYPE_CHOICES)
    report_date = serializers.DateField(
        required=False,
        allow_null=True,
        default=date_now,
        help_text=gettext_lazy("Report date or second date for pl report"),
    )
    report_currency = ReportCurrencyField(
        required=False, allow_null=True, default=SystemCurrencyDefault()
    )
    pricing_policy = ReportPricingPolicyField()

    execution_time = serializers.FloatField(
        allow_null=True, required=False, read_only=True
    )
    relation_prefetch_time = serializers.FloatField(
        allow_null=True, required=False, read_only=True
    )
    serialization_time = serializers.FloatField(
        allow_null=True, required=False, read_only=True
    )
    auth_time = serializers.FloatField(allow_null=True, required=False, read_only=True)

    pricing_policy_object = PricingPolicyViewSerializer(
        source="pricing_policy", read_only=True
    )
    report_currency_object = CurrencyViewSerializer(
        source="report_currency", read_only=True
    )

    items = serializers.SerializerMethodField()

    # item_currencies = ReportCurrencySerializer(many=True, read_only=True)
    # item_instruments = serializers.SerializerMethodField()

    def get_items(self, obj):
        return [serialize_price_checker_item(item) for item in obj.items]

    def get_item_instruments(self, obj):
        return [
            serialize_price_checker_item_instrument(item)
            for item in obj.item_instruments
        ]

    def create(self, validated_data):
        return Report(**validated_data)


class BackendBalanceReportGroupsSerializer(BalanceReportSerializer):
    def to_representation(self, instance):
        if not instance.frontend_request_options:
            raise serializers.ValidationError("frontend_request_options is required")

        to_representation_st = time.perf_counter()

        helper_service = BackendReportHelperService()

        _l.debug("BackendBalanceReportGroupsSerializer.to_representation")

        unique_key = generate_unique_key(instance, "balance")

        try:

            report_instance = BalanceReportInstance.objects.get(unique_key=unique_key)

            data = report_instance.data

            full_items = report_instance.data["items"]

        except BalanceReportInstance.DoesNotExist:

            data = super(BackendBalanceReportGroupsSerializer, self).to_representation(
                instance
            )

            report_uuid = str(uuid.uuid4())

            report_instance_name = ""
            if self.instance.report_instance_name:
                report_instance_name = self.instance.report_instance_name
            else:
                report_instance_name = report_uuid

            report_instance = BalanceReportInstance.objects.create(
                unique_key=unique_key,
                master_user=instance.master_user,
                member=instance.member,
                owner=instance.member,
                user_code=report_instance_name,
                name=report_instance_name,
                short_name=report_instance_name,
                report_date=instance.report_date,
                report_currency=instance.report_currency,
                pricing_policy=instance.pricing_policy,
                cost_method=instance.cost_method,
            )

            report_instance.report_date = instance.report_date
            report_instance.report_currency = instance.report_currency
            report_instance.pricing_policy = instance.pricing_policy
            report_instance.cost_method = instance.cost_method

            report_instance.report_uuid = report_uuid

            data["report_uuid"] = report_uuid

            full_items = helper_service.convert_report_items_to_full_items(data)

            data["items"] = full_items

            report_instance.data = json.loads(json.dumps(data, default=str))

            report_instance.save()

        full_items = helper_service.calculate_value_percent(
            full_items, instance.calculation_group, "market_value"
        )
        full_items = helper_service.calculate_value_percent(
            full_items, instance.calculation_group, "exposure"
        )

        # filter by previous groups
        full_items = helper_service.filter(
            full_items, instance.frontend_request_options
        )

        full_items = helper_service.filter_by_groups_filters(
            full_items, instance.frontend_request_options
        )

        full_items = helper_service.sort_items(
            full_items, instance.frontend_request_options
        )

        groups_types = instance.frontend_request_options["groups_types"]
        columns = instance.frontend_request_options["columns"]

        group_type = groups_types[len(groups_types) - 1]

        unique_groups = helper_service.get_unique_groups(
            full_items, group_type, columns
        )
        unique_groups = helper_service.sort_groups(
            unique_groups, instance.frontend_request_options
        )

        # _l.debug('unique_groups %s' % unique_groups)

        data["count"] = len(unique_groups)

        groups = helper_service.paginate_items(
            unique_groups,
            {
                "page_size": instance.page_size,
                "page": instance.page,
            },
        )

        data["report_instance_id"] = report_instance.id
        data["items"] = groups
        data.pop("item_currencies", [])
        data.pop("item_portfolios", [])
        data.pop("item_instruments", [])
        data.pop("item_instrument_types", [])
        data.pop("item_accounts", [])
        data.pop("item_countries", [])
        data.pop("item_account_types", [])
        data.pop("item_strategies1", [])
        data.pop("item_strategies2", [])
        data.pop("item_strategies3", [])

        data["created_at"] = report_instance.created_at

        _l.debug("BackendBalanceReportGroupsSerializer.to_representation")

        data["serialization_time"] = float(
            "{:3.3f}".format(time.perf_counter() - to_representation_st)
        )

        # _l.debug('data items %s ' % data['items'])

        return data


class BackendBalanceReportItemsSerializer(BalanceReportSerializer):
    def to_representation(self, instance):
        if not instance.frontend_request_options:
            raise serializers.ValidationError("frontend_request_options is required")

        to_representation_st = time.perf_counter()

        helper_service = BackendReportHelperService()

        _l.debug("BackendBalanceReportItemsSerializer.to_representation")

        # TODO Hard logic requires refactor
        # Idea is that if user is not passed report_instance_id then we calculated it normal flow
        # if user passed report_instance_id then we skip:
        #    - build_report step
        #    - all to_representation steps
        # Idea is that we put calculated report and to_representation result to BalanceReportInstance.data
        # And if user just applies filters or regroups there is no need for calculating whole report again

        unique_key = generate_unique_key(instance, "balance")

        try:

            report_instance = BalanceReportInstance.objects.get(unique_key=unique_key)

            data = report_instance.data

            full_items = report_instance.data["items"]

        except BalanceReportInstance.DoesNotExist:
            data = super(BackendBalanceReportItemsSerializer, self).to_representation(
                instance
            )

            report_uuid = str(uuid.uuid4())

            report_instance_name = ""
            if self.instance.report_instance_name:
                report_instance_name = self.instance.report_instance_name
            else:
                report_instance_name = report_uuid

            report_instance = BalanceReportInstance.objects.create(
                unique_key=unique_key,
                master_user=instance.master_user,
                member=instance.member,
                owner=instance.member,
                user_code=report_instance_name,
                name=report_instance_name,
                short_name=report_instance_name,
                report_date=instance.report_date,
                report_currency=instance.report_currency,
                pricing_policy=instance.pricing_policy,
                cost_method=instance.cost_method,
            )

            report_instance.report_date = instance.report_date
            report_instance.report_currency = instance.report_currency
            report_instance.pricing_policy = instance.pricing_policy
            report_instance.cost_method = instance.cost_method

            report_instance.report_uuid = report_uuid

            data["report_uuid"] = report_uuid

            full_items = helper_service.convert_report_items_to_full_items(data)

            data["items"] = full_items

            report_instance.data = json.loads(
                json.dumps(data, default=str)
            )  # TODO consider something more logical, we got here date conversion error

            report_instance.save()



        full_items = helper_service.calculate_value_percent(
            full_items, instance.calculation_group, "market_value"
        )
        full_items = helper_service.calculate_value_percent(
            full_items, instance.calculation_group, "exposure"
        )

        # _l.debug('full_items %s' % full_items[0])
        full_items = helper_service.filter(
            full_items, instance.frontend_request_options
        )

        full_items = helper_service.filter_by_groups_filters(
            full_items, instance.frontend_request_options
        )

        full_items = helper_service.sort_items(
            full_items, instance.frontend_request_options
        )
        # full_items = helper_service.reduce_columns(full_items, instance.frontend_request_options)

        result_items = []

        # _l.debug("full_items items len %s" % len(full_items))
        # _l.debug("original items len %s" % len(data['items']))

        # for item in data['items']:
        #     for full_item in full_items:
        #         if item['id'] == full_item['id']:
        #             result_items.append(item)
        #
        # data['items'] = result_items

        # data['items'] = full_items

        data["count"] = len(full_items)

        data["report_instance_id"] = report_instance.id
        data["items"] = helper_service.paginate_items(
            full_items,
            {
                "page_size": instance.page_size,
                "page": instance.page,
            },
        )

        for item in data["items"]:
            item["date"] = data["report_date"]

        data.pop("item_currencies", [])
        data.pop("item_portfolios", [])
        data.pop("item_instruments", [])
        data.pop("item_instrument_types", [])
        data.pop("item_accounts", [])
        data.pop("item_countries", [])
        data.pop("item_account_types", [])
        data.pop("item_strategies1", [])
        data.pop("item_strategies2", [])
        data.pop("item_strategies3", [])

        data["created_at"] = report_instance.created_at

        # _l.debug("after filter items len %s" % len(data['items']))

        # original_items = helper_service.filterByGlobalTableSearch(original_items, globalTableSearch)

        data["serialization_time"] = float(
            "{:3.3f}".format(time.perf_counter() - to_representation_st)
        )

        return data


class BackendPLReportGroupsSerializer(PLReportSerializer):
    def to_representation(self, instance):
        if not instance.frontend_request_options:
            raise serializers.ValidationError("frontend_request_options is required")

        to_representation_st = time.perf_counter()

        helper_service = BackendReportHelperService()

        unique_key = generate_unique_key(instance, "pnl")

        try:

            report_instance = PLReportInstance.objects.get(unique_key=unique_key)

            data = report_instance.data

            full_items = report_instance.data["items"]

        except PLReportInstance.DoesNotExist:
            data = super(BackendPLReportGroupsSerializer, self).to_representation(
                instance
            )

            report_uuid = str(uuid.uuid4())

            report_instance_name = ""
            if self.instance.report_instance_name:
                report_instance_name = self.instance.report_instance_name
            else:
                report_instance_name = report_uuid

            report_instance = PLReportInstance.objects.create(
                unique_key=unique_key,
                master_user=instance.master_user,
                member=instance.member,
                owner=instance.member,
                user_code=report_instance_name,
                name=report_instance_name,
                short_name=report_instance_name,
                report_date=instance.report_date,
                pl_first_date=instance.pl_first_date,
                report_currency=instance.report_currency,
                pricing_policy=instance.pricing_policy,
                cost_method=instance.cost_method,
            )

            report_instance.report_uuid = report_uuid
            report_instance.report_date = instance.report_date
            report_instance.pl_first_date = instance.pl_first_date
            report_instance.report_currency = instance.report_currency
            report_instance.pricing_policy = instance.pricing_policy
            report_instance.cost_method = instance.cost_method

            report_instance.report_uuid = report_uuid

            data["report_uuid"] = report_uuid

            full_items = helper_service.convert_report_items_to_full_items(data)

            data["items"] = full_items

            report_instance.data = json.loads(
                json.dumps(data, default=str)
            )  # TODO consider something more logical, we got here date conversion error

            report_instance.save()

        data["report_instance_id"] = report_instance.id

        _l.debug("BackendBalanceReportGroupsSerializer.to_representation")

        # filter by previous groups
        full_items = helper_service.filter(
            full_items, instance.frontend_request_options
        )
        full_items = helper_service.calculate_value_percent(
            full_items, instance.calculation_group, "market_value"
        )
        full_items = helper_service.calculate_value_percent(
            full_items, instance.calculation_group, "exposure"
        )

        full_items = helper_service.filter_by_groups_filters(
            full_items, instance.frontend_request_options
        )

        # _l.debug('instance.frontend_request_options %s' % instance.frontend_request_options)
        # _l.debug('original_items0 %s' % full_items[0])

        groups_types = instance.frontend_request_options["groups_types"]
        columns = instance.frontend_request_options["columns"]

        group_type = groups_types[len(groups_types) - 1]

        unique_groups = helper_service.get_unique_groups(
            full_items, group_type, columns
        )
        unique_groups = helper_service.sort_groups(
            unique_groups, instance.frontend_request_options
        )

        # _l.debug('unique_groups %s' % unique_groups)

        data["count"] = len(unique_groups)

        data["items"] = helper_service.paginate_items(
            unique_groups,
            {
                "page_size": instance.page_size,
                "page": instance.page,
            },
        )

        data["created_at"] = report_instance.created_at

        _l.debug("BackendBalanceReportGroupsSerializer.to_representation")

        data["serialization_time"] = float(
            "{:3.3f}".format(time.perf_counter() - to_representation_st)
        )

        # _l.debug('data items %s ' % data['items'])

        return data


class BackendPLReportItemsSerializer(PLReportSerializer):
    def to_representation(self, instance):
        if not instance.frontend_request_options:
            raise serializers.ValidationError("frontend_request_options is required")

        to_representation_st = time.perf_counter()

        helper_service = BackendReportHelperService()

        unique_key = generate_unique_key(instance, "pnl")

        try:

            report_instance = PLReportInstance.objects.get(unique_key=unique_key)

            data = report_instance.data

            full_items = report_instance.data["items"]

        except PLReportInstance.DoesNotExist:
            data = super(BackendPLReportItemsSerializer, self).to_representation(
                instance
            )

            report_uuid = str(uuid.uuid4())

            report_instance_name = ""
            if self.instance.report_instance_name:
                report_instance_name = self.instance.report_instance_name
            else:
                report_instance_name = report_uuid

            report_instance = PLReportInstance.objects.create(
                unique_key=unique_key,
                master_user=instance.master_user,
                member=instance.member,
                owner=instance.member,
                user_code=report_instance_name,
                name=report_instance_name,
                short_name=report_instance_name,
                report_date=instance.report_date,
                pl_first_date=instance.pl_first_date,
                report_currency=instance.report_currency,
                pricing_policy=instance.pricing_policy,
                cost_method=instance.cost_method,
            )

            report_instance.report_uuid = report_uuid
            report_instance.report_date = instance.report_date
            report_instance.pl_first_date = instance.pl_first_date
            report_instance.report_currency = instance.report_currency
            report_instance.pricing_policy = instance.pricing_policy
            report_instance.cost_method = instance.cost_method

            report_instance.report_uuid = report_uuid

            data["report_uuid"] = report_uuid

            full_items = helper_service.convert_report_items_to_full_items(data)

            data["items"] = full_items

            report_instance.data = json.loads(
                json.dumps(data, default=str)
            )  # TODO consider something more logical, we got here date conversion error

            report_instance.save()

        data["report_instance_id"] = report_instance.id

        _l.debug("BackendBalanceReportItemsSerializer.to_representation")

        _l.debug(f"PL BEFORE ALL FILTERS full_items len {len(full_items)}")
        full_items = helper_service.filter(
            full_items, instance.frontend_request_options
        )
        full_items = helper_service.calculate_value_percent(
            full_items, instance.calculation_group, "market_value"
        )
        full_items = helper_service.calculate_value_percent(
            full_items, instance.calculation_group, "exposure"
        )

        _l.debug(f"PL BEFORE ALL GLOBAL FILTER full_items len {len(full_items)}")
        full_items = helper_service.filter_by_groups_filters(
            full_items, instance.frontend_request_options
        )
        full_items = helper_service.sort_items(
            full_items, instance.frontend_request_options
        )
        _l.debug(f"PL BEFORE AFTER ALL FILTERS full_items len {len(full_items)}")

        data["count"] = len(full_items)

        data["items"] = helper_service.paginate_items(
            full_items,
            {
                "page_size": instance.page_size,
                "page": instance.page,
            },
        )
        data.pop("item_currencies", [])
        data.pop("item_portfolios", [])
        data.pop("item_instruments", [])
        data.pop("item_instrument_types", [])
        data.pop("item_accounts", [])
        data.pop("item_countries", [])
        data.pop("item_account_types", [])
        data.pop("item_strategies1", [])
        data.pop("item_strategies2", [])
        data.pop("item_strategies3", [])

        data["created_at"] = report_instance.created_at

        data["serialization_time"] = float(
            "{:3.3f}".format(time.perf_counter() - to_representation_st)
        )

        return data


class BackendTransactionReportGroupsSerializer(TransactionReportSerializer):
    def to_representation(self, instance):
        if not instance.frontend_request_options:
            raise serializers.ValidationError("frontend_request_options is required")

        to_representation_st = time.perf_counter()

        helper_service = BackendReportHelperService()

        if not instance.report_instance_id:
            data = super(
                BackendTransactionReportGroupsSerializer, self
            ).to_representation(instance)

            report_uuid = str(uuid.uuid4())

            if self.instance.report_instance_name:
                report_instance_name = self.instance.report_instance_name
            else:
                report_instance_name = report_uuid

            report_instance = TransactionReportInstance.objects.create(
                master_user=instance.master_user,
                member=instance.member,
                owner=instance.member,
                user_code=report_instance_name,
                name=report_instance_name,
                short_name=report_instance_name,
                begin_date=instance.begin_date,
                end_date=instance.end_date,
            )

            report_instance.report_uuid = report_uuid
            report_instance.begin_date = instance.begin_date
            report_instance.end_date = instance.end_date

            report_instance.report_uuid = report_uuid

            data["report_uuid"] = report_uuid

            full_items = helper_service.convert_report_items_to_full_items(data)

            data["items"] = full_items

            report_instance.data = json.loads(json.dumps(data, default=str))

            report_instance.save()

        else:
            report_instance = TransactionReportInstance.objects.get(
                id=instance.report_instance_id
            )

            data = report_instance.data

            full_items = report_instance.data["items"]

        data["report_instance_id"] = report_instance.id

        _l.debug("BackendTransactionReportGroupsSerializer.to_representation")

        # filter by previous groups
        full_items = helper_service.filter(
            full_items, instance.frontend_request_options
        )
        full_items = helper_service.filter_by_groups_filters(
            full_items, instance.frontend_request_options
        )

        groups_types = instance.frontend_request_options["groups_types"]
        columns = instance.frontend_request_options["columns"]

        group_type = groups_types[len(groups_types) - 1]

        unique_groups = helper_service.get_unique_groups(
            full_items, group_type, columns
        )
        unique_groups = helper_service.sort_groups(
            unique_groups, instance.frontend_request_options
        )

        # _l.debug('unique_groups %s' % unique_groups)

        data["count"] = len(unique_groups)

        _l.debug(
            f'BackendTransactionReportGroupsSerializer.to_representation.page {data["page"]}'
        )

        groups = helper_service.paginate_items(
            unique_groups,
            {
                "page_size": instance.page_size,
                "page": instance.page,
            },
        )

        data["items"] = groups

        data.pop("item_currencies", [])
        data.pop("item_portfolios", [])
        data.pop("item_instruments", [])
        data.pop("item_instrument_types", [])
        data.pop("item_accounts", [])
        data.pop("item_countries", [])
        data.pop("item_account_types", [])
        data.pop("item_strategies1", [])
        data.pop("item_strategies2", [])
        data.pop("item_strategies3", [])

        _l.debug("BackendTransactionReportGroupsSerializer.to_representation")

        data["serialization_time"] = float(
            "{:3.3f}".format(time.perf_counter() - to_representation_st)
        )

        # _l.debug('data items %s ' % data['items'])

        return data


class BackendTransactionReportItemsSerializer(TransactionReportSerializer):
    def to_representation(self, instance):
        _l.debug("BackendTransactionReportItemsSerializer.to_representation")

        if not instance.frontend_request_options:
            raise serializers.ValidationError("frontend_request_options is required")

        to_representation_st = time.perf_counter()

        helper_service = BackendReportHelperService()

        if not instance.report_instance_id:
            data = super().to_representation(instance)
            report_uuid = str(uuid.uuid4())

            if self.instance.report_instance_name:
                report_instance_name = self.instance.report_instance_name
            else:
                report_instance_name = report_uuid

            report_instance = TransactionReportInstance.objects.create(
                master_user=instance.master_user,
                member=instance.member,
                owner=instance.member,
                user_code=report_instance_name,
                name=report_instance_name,
                short_name=report_instance_name,
                begin_date=instance.begin_date,
                end_date=instance.end_date,
                report_uuid=report_uuid,
            )

            data["report_uuid"] = report_uuid
            full_items = helper_service.convert_report_items_to_full_items(data)
            data["items"] = full_items

            # TODO consider something more logical, we got here date conversion error
            report_instance.data = json.loads(json.dumps(data, default=str))

            report_instance.save()

        else:
            report_instance = TransactionReportInstance.objects.get(
                id=instance.report_instance_id
            )
            data = report_instance.data
            full_items = report_instance.data["items"]

        data["report_instance_id"] = report_instance.id

        full_items = helper_service.filter(
            full_items, instance.frontend_request_options
        )
        full_items = helper_service.filter_by_groups_filters(
            full_items, instance.frontend_request_options
        )
        full_items = helper_service.sort_items(
            full_items, instance.frontend_request_options
        )

        _l.debug(f"full items?? {len(full_items)}")

        data["count"] = len(full_items)

        data["items"] = helper_service.paginate_items(
            full_items,
            {
                "page_size": instance.page_size,
                "page": instance.page,
            },
        )

        data.pop("item_currencies", [])
        data.pop("item_portfolios", [])
        data.pop("item_instruments", [])
        data.pop("item_instrument_types", [])
        data.pop("item_accounts", [])
        data.pop("item_account_types", [])
        data.pop("item_strategies1", [])
        data.pop("item_strategies2", [])
        data.pop("item_strategies3", [])
        data.pop("item_counterparties", [])
        data.pop("item_countries", [])
        data.pop("item_responsibles", [])
        data.pop("item_transaction_classes", [])
        data.pop("item_complex_transactions", [])

        data["serialization_time"] = float(
            "{:3.3f}".format(time.perf_counter() - to_representation_st)
        )

        return data


class BalanceReportInstanceSerializer(
    ModelWithUserCodeSerializer,
    ModelWithTimeStampSerializer,
    ModelMetaSerializer,
):
    master_user = MasterUserField()

    class Meta:
        model = BalanceReportInstance
        fields = [
            "id",
            "master_user",
            "user_code",
            "name",
            "short_name",
            "public_name",
            "notes",
            "unique_key",

            "report_date",
            "report_currency",
            "pricing_policy",
            "cost_method"
        ]

    def __init__(self, *args, **kwargs):
        super(BalanceReportInstanceSerializer, self).__init__(*args, **kwargs)




class PLReportInstanceSerializer(
    ModelWithUserCodeSerializer,
    ModelWithTimeStampSerializer,
    ModelMetaSerializer,
):
    master_user = MasterUserField()

    class Meta:
        model = PLReportInstance
        fields = [
            "id",
            "master_user",
            "user_code",
            "name",
            "short_name",
            "public_name",
            "notes",
            "unique_key"
            
            "report_date",
            "pl_first_date",
            "report_currency",
            "pricing_policy",
            "cost_method"
        ]

    def __init__(self, *args, **kwargs):
        super(PLReportInstanceSerializer, self).__init__(*args, **kwargs)


