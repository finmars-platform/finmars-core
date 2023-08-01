from django.contrib import admin
from django.utils.translation import gettext_lazy

from poms.common.admin import AbstractModelAdmin
from poms.currencies.models import Currency, CurrencyHistory
from poms.obj_attrs.admin import GenericAttributeInline


class CurrencyAdmin(AbstractModelAdmin):
    model = Currency
    master_user_path = "master_user"
    list_display = [
        "id",
        "master_user",
        "user_code",
        "name",
        "is_deleted",
    ]
    list_select_related = ["master_user"]
    list_filter = ["is_deleted"]
    search_fields = [
        "id",
        "user_code",
        "name",
    ]
    raw_id_fields = ["master_user"]
    inlines = [GenericAttributeInline]

    def is_system(self, obj):
        return obj.is_system

    is_system.short_name = gettext_lazy("is system")
    is_system.boolean = True


class CurrencyHistoryAdmin(AbstractModelAdmin):
    model = CurrencyHistory
    master_user_path = "currency__master_user"
    list_display = [
        "id",
        "master_user",
        "currency",
        "pricing_policy",
        "date",
        "fx_rate",
    ]
    list_select_related = [
        "currency",
        "currency__master_user",
    ]
    list_filter = [
        "date",
    ]
    search_fields = [
        "currency__id",
        "currency__user_code",
        "currency__name",
    ]
    date_hierarchy = "date"
    raw_id_fields = [
        "currency",
        "pricing_policy",
    ]

    def master_user(self, obj):
        return obj.currency.master_user

    master_user.admin_order_field = "currency__master_user"


admin.site.register(Currency, CurrencyAdmin)
admin.site.register(CurrencyHistory, CurrencyHistoryAdmin)
