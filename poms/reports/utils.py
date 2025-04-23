import hashlib
import json
import logging
from datetime import date, timedelta

from poms.accounts.models import Account
from poms.common.utils import (
    get_last_business_day,
    get_last_business_day_in_previous_quarter,
    get_last_business_day_of_previous_month,
    get_last_business_day_of_previous_year,
)
from poms.iam.utils import get_allowed_queryset
from poms.portfolios.models import Portfolio

_l = logging.getLogger("poms.reports")


def generate_report_unique_hash(app, action, data, master_user, member):
    _data = data.copy()

    report_options = {"master_user": master_user.id, "member": member.id}

    if "begin_date" in _data:
        report_options["begin_date"] = _data["begin_date"]

    if "date_field" in _data:
        report_options["date_field"] = _data["date_field"]

    if "end_date" in _data:
        report_options["end_date"] = _data["end_date"]

    if "report_date" in _data:
        report_options["report_date"] = _data["report_date"]

    if "pl_first_date" in _data:
        report_options["pl_first_date"] = _data["pl_first_date"]

    if "report_currency" in _data:
        report_options["report_currency"] = _data["report_currency"]

    if "pricing_policy" in _data:
        report_options["pricing_policy"] = _data["pricing_policy"]

    if "report_type" in _data:
        report_options["report_type"] = _data["report_type"]

    if "account_mode" in _data:
        report_options["account_mode"] = _data["account_mode"]

    if "portfolio_mode" in _data:
        report_options["portfolio_mode"] = _data["portfolio_mode"]

    if "strategy1_mode" in _data:
        report_options["strategy1_mode"] = _data["strategy1_mode"]

    if "strategy2_mode" in _data:
        report_options["strategy2_mode"] = _data["strategy2_mode"]

    if "strategy3_mode" in _data:
        report_options["strategy3_mode"] = _data["strategy3_mode"]

    if "allocation_mode" in _data:
        report_options["allocation_mode"] = _data["allocation_mode"]

    if "custom_fields_to_calculate" in _data:
        report_options["custom_fields_to_calculate"] = _data[
            "custom_fields_to_calculate"
        ]

    if "complex_transaction_statuses_filter" in _data:
        report_options["complex_transaction_statuses_filter"] = _data[
            "complex_transaction_statuses_filter"
        ]

    if "cost_method" in _data:
        report_options["cost_method"] = _data["cost_method"]

    if "show_balance_exposure_details" in _data:
        report_options["show_balance_exposure_details"] = _data[
            "show_balance_exposure_details"
        ]

    if "show_transaction_details" in _data:
        report_options["show_transaction_details"] = _data["show_transaction_details"]

    if "approach_multiplier" in _data:
        report_options["approach_multiplier"] = _data["approach_multiplier"]

    if "portfolios" in _data:
        report_options["portfolios"] = _data["portfolios"]

    if "accounts" in _data:
        report_options["accounts"] = _data["accounts"]

    if "strategies1" in _data:
        report_options["strategies1"] = _data["strategies1"]

    if "strategies2" in _data:
        report_options["strategies2"] = _data["strategies2"]

    if "strategies3" in _data:
        report_options["strategies3"] = _data["strategies3"]

    # Performance report field

    if "calculation_type" in _data:
        report_options["calculation_type"] = _data["calculation_type"]

    if "segmentation_type" in _data:
        report_options["segmentation_type"] = _data["segmentation_type"]

    if "calculation_type" in _data:
        report_options["calculation_type"] = _data["calculation_type"]

    if "registers" in _data:
        report_options["registers"] = _data["registers"]

    if "bundle" in _data:
        report_options["bundle"] = _data["bundle"]

    if "depth_level" in _data:
        report_options["depth_level"] = _data["depth_level"]

    if "period_type" in _data:
        report_options["period_type"] = _data["period_type"]

    if "filters" in _data:
        report_options["filters"] = str(_data["filters"])

    if "expression_iterations_count" in _data:
        report_options["expression_iterations_count"] = _data[
            "expression_iterations_count"
        ]

    hash_value = hashlib.md5(
        json.dumps(report_options, sort_keys=True, default=str).encode()
    ).hexdigest()

    return f"{app}_{action}_{master_user.id}-{member.id}-{hash_value}"


def get_first_transaction():
    from poms.transactions.models import Transaction

    try:
        transaction = Transaction.objects.all().first()

        return transaction.transaction_date

    except Exception:
        _l.error("Could not find first transaction date")
        return None


def get_pl_first_date(instance):
    if not instance.pl_first_date and instance.period_type:
        _l.debug("No pl_first_date, calculating by period_type...")

        if instance.period_type == "inception":
            # TODO wtf is first transaction when multi portfolios?
            # TODO ask oleg what to do with inception
            # szhitenev 2023-12-04

            first_portfolio = instance.portfolios.first()

            instance.pl_first_date = get_last_business_day(
                first_portfolio.first_transaction_date - timedelta(days=1),
            )
        elif instance.period_type == "ytd":
            instance.pl_first_date = get_last_business_day_of_previous_year(
                instance.report_date
            )

        elif instance.period_type == "qtd":
            instance.pl_first_date = get_last_business_day_in_previous_quarter(
                instance.report_date
            )

        elif instance.period_type == "mtd":
            instance.pl_first_date = get_last_business_day_of_previous_month(
                instance.report_date
            )

        elif instance.period_type == "daily":
            instance.pl_first_date = get_last_business_day(
                instance.report_date - timedelta(days=1)
            )

    instance.first_transaction_date = get_first_transaction()

    pl_first_date = instance.pl_first_date

    if not pl_first_date or pl_first_date == date.min:
        instance.pl_first_date = instance.first_transaction_date

    return instance.pl_first_date


def transform_to_allowed_portfolios(instance):
    if not len(instance.portfolios):
        return get_allowed_queryset(
            instance.member, Portfolio.objects.filter(is_deleted=False)
        )
    return instance.portfolios


def transform_to_allowed_accounts(instance):
    if not len(instance.accounts):
        return get_allowed_queryset(
            instance.member, Account.objects.filter(is_deleted=False)
        )
    return instance.accounts


def generate_unique_key(instance, report_type):
    portfolio_user_codes = sorted(
        [portfolio.user_code for portfolio in instance.portfolios]
    )
    account_user_codes = sorted([account.user_code for account in instance.accounts])
    strategy1_user_codes = sorted(
        [strategy.user_code for strategy in instance.strategies1]
    )
    strategy2_user_codes = sorted(
        [strategy.user_code for strategy in instance.strategies2]
    )
    strategy3_user_codes = sorted(
        [strategy.user_code for strategy in instance.strategies3]
    )

    report_data = {
        "report_type": report_type,
        "report_date": str(instance.report_date),
        "pl_first_date": str(instance.pl_first_date),
        "report_currency": instance.report_currency.user_code,
        "cost_method": instance.cost_method.user_code,
        "pricing_policy": instance.pricing_policy.user_code,
        "portfolio_mode": instance.portfolio_mode,
        "account_mode": instance.account_mode,
        "strategy1_mode": instance.strategy1_mode,
        "strategy2_mode": instance.strategy2_mode,
        "strategy3_mode": instance.strategy3_mode,
        "allocation_mode": instance.allocation_mode,
        "calculate_pl": instance.calculate_pl,
        "portfolios": portfolio_user_codes,
        "accounts": account_user_codes,
        "strategies1": strategy1_user_codes,
        "strategies2": strategy2_user_codes,
        "strategies3": strategy3_user_codes,
        "custom_fields_to_calculate": instance.custom_fields_to_calculate,
    }

    settings = json.dumps(report_data, sort_keys=True, default=str)
    unique_key = hashlib.md5(settings.encode()).hexdigest()

    return settings, unique_key
