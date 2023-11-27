from django.contrib import admin

from poms.common.admin import AbstractModelAdmin
from poms.obj_attrs.admin import GenericAttributeInline
from poms.portfolios.models import (
    Portfolio,
    PortfolioBundle,
    PortfolioRegister,
    PortfolioRegisterRecord, PortfolioHistory,
)


class PortfolioAdmin(AbstractModelAdmin):
    model = Portfolio
    master_user_path = "master_user"
    list_display = [
        "id",
        "master_user",
        "user_code",
        "name",
        "is_deleted",
    ]
    list_select_related = ["master_user"]
    list_filter = [
        "is_deleted",
    ]
    search_fields = ["id", "user_code", "name"]
    raw_id_fields = [
        "master_user",
        "accounts",
        "responsibles",
        "counterparties",
        "transaction_types",
    ]
    inlines = [
        GenericAttributeInline,
    ]


admin.site.register(Portfolio, PortfolioAdmin)


class PortfolioRegisterAdmin(AbstractModelAdmin):
    model = PortfolioRegister
    master_user_path = "master_user"
    list_display = [
        "id",
        "master_user",
        "portfolio",
        "linked_instrument",
        "valuation_pricing_policy",
        "valuation_currency",
    ]
    raw_id_fields = [
        "master_user",
        "portfolio",
        "linked_instrument",
        "valuation_pricing_policy",
        "valuation_currency",
    ]


admin.site.register(PortfolioRegister, PortfolioRegisterAdmin)


class PortfolioRegisterRecordAdmin(AbstractModelAdmin):
    model = PortfolioRegisterRecord
    master_user_path = "master_user"
    list_display = [
        "id",
        "master_user",
        "transaction_date",
        "portfolio",
        "instrument",
        "transaction_class",
        "portfolio_register",
        "share_price_calculation_type",
    ]
    raw_id_fields = [
        "master_user",
        "portfolio",
        "instrument",
        "portfolio_register",
    ]


admin.site.register(PortfolioRegisterRecord, PortfolioRegisterRecordAdmin)


class PortfolioBundleAdmin(AbstractModelAdmin):
    model = PortfolioBundle
    master_user_path = "master_user"
    list_display = ["id", "master_user", "name"]
    raw_id_fields = ["master_user"]

    filter_horizontal = ("registers",)


admin.site.register(PortfolioBundle, PortfolioBundleAdmin)


class PortfolioHistoryAdmin(AbstractModelAdmin):
    model = PortfolioHistory
    master_user_path = "master_user"
    list_display = ["id", "master_user", "user_code", "portfolio", "date"]
    raw_id_fields = ["master_user"]


admin.site.register(PortfolioHistory, PortfolioHistoryAdmin)