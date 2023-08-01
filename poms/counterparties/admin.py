from django.contrib import admin

from poms.common.admin import AbstractModelAdmin
from poms.counterparties.models import (
    Counterparty,
    CounterpartyGroup,
    Responsible,
    ResponsibleGroup,
)
from poms.obj_attrs.admin import GenericAttributeInline


class CounterpartyGroupAdmin(AbstractModelAdmin):
    model = CounterpartyGroup
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


class CounterpartyAdmin(AbstractModelAdmin):
    model = Counterparty
    master_user_path = "master_user"
    list_display = [
        "id",
        "master_user",
        "group",
        "user_code",
        "name",
        "is_deleted",
    ]
    list_select_related = ["master_user", "group"]
    list_filter = [
        "is_deleted",
    ]
    search_fields = ["id", "user_code", "name"]
    raw_id_fields = ["master_user", "group"]
    inlines = [
        GenericAttributeInline,
    ]


class ResponsibleGroupAdmin(AbstractModelAdmin):
    model = ResponsibleGroup
    master_user_path = "master_user"
    list_display = [
        "id",
        "master_user",
        "user_code",
        "name",
        "is_deleted",
    ]
    list_select_related = ["master_user"]
    search_fields = ["id", "user_code", "name"]
    list_filter = [
        "is_deleted",
    ]
    raw_id_fields = ["master_user"]
    inlines = []


class ResponsibleAdmin(AbstractModelAdmin):
    model = Responsible
    master_user_path = "master_user"
    list_display = [
        "id",
        "master_user",
        "group",
        "user_code",
        "name",
        "is_deleted",
    ]
    list_select_related = ["master_user", "group"]
    search_fields = ["id", "user_code", "name"]
    list_filter = [
        "is_deleted",
    ]
    raw_id_fields = ["master_user", "group"]
    inlines = [
        GenericAttributeInline,
    ]


admin.site.register(CounterpartyGroup, CounterpartyGroupAdmin)
admin.site.register(Counterparty, CounterpartyAdmin)
admin.site.register(ResponsibleGroup, ResponsibleGroupAdmin)
admin.site.register(Responsible, ResponsibleAdmin)
