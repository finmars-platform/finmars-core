from django.contrib import admin

from poms.accounts.models import Account, AccountType
from poms.common.admin import AbstractModelAdmin
from poms.obj_attrs.admin import GenericAttributeInline


class AccountTypeAdmin(AbstractModelAdmin):
    model = AccountType
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
    raw_id_fields = ["master_user"]
    inlines = []


admin.site.register(AccountType, AccountTypeAdmin)


class AccountAdmin(AbstractModelAdmin):
    model = Account
    master_user_path = "master_user"
    list_display = [
        "id",
        "master_user",
        "type",
        "user_code",
        "name",
        "is_deleted",
        "modified",
    ]
    list_select_related = ["master_user", "type"]
    list_filter = [
        "is_deleted",
    ]
    search_fields = ["id", "user_code", "name"]
    raw_id_fields = ["master_user", "type"]
    inlines = [
        GenericAttributeInline,
    ]


admin.site.register(Account, AccountAdmin)
