from __future__ import unicode_literals

from django.contrib import admin

from poms.common.admin import AbstractModelAdmin
from poms.obj_attrs.admin import GenericAttributeInline
from poms.obj_perms.admin import GenericObjectPermissionInline
from poms.portfolios.models import Portfolio, PortfolioRegister, PortfolioRegisterRecord


class PortfolioAdmin(AbstractModelAdmin):
    model = Portfolio
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'user_code', 'name', 'is_deleted', ]
    list_select_related = ['master_user']
    list_filter = ['is_deleted', ]
    search_fields = ['id', 'user_code', 'name']
    raw_id_fields = ['master_user', 'accounts', 'responsibles', 'counterparties', 'transaction_types']
    inlines = [
        # AbstractAttributeInline,
        GenericAttributeInline,
        GenericObjectPermissionInline,
        # UserObjectPermissionInline,
        # GroupObjectPermissionInline,
    ]


admin.site.register(Portfolio, PortfolioAdmin)

#
# class PortfolioAttributeTypeAdmin(AbstractAttributeTypeAdmin):
#     inlines = [
#         AbstractAttributeTypeClassifierInline,
#         AbstractAttributeTypeOptionInline,
#         GenericObjectPermissionInline,
#         # UserObjectPermissionInline,
#         # GroupObjectPermissionInline,
#     ]
#
#
# admin.site.register(PortfolioAttributeType, PortfolioAttributeTypeAdmin)
#
# admin.site.register(PortfolioClassifier, ClassifierAdmin)


class PortfolioRegisterAdmin(AbstractModelAdmin):
    model = PortfolioRegister
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'portfolio', 'linked_instrument', 'valuation_pricing_policy', 'valuation_currency']
    raw_id_fields = ['master_user', 'portfolio', 'linked_instrument', 'valuation_pricing_policy', 'valuation_currency']



admin.site.register(PortfolioRegister, PortfolioRegisterAdmin)


class PortfolioRegisterRecordAdmin(AbstractModelAdmin):
    model = PortfolioRegisterRecord
    master_user_path = 'master_user'
    list_display = ['id', 'master_user', 'transaction_date', 'portfolio', 'instrument', 'transaction_type', 'portfolio_register']
    raw_id_fields = ['master_user', 'portfolio', 'instrument', 'portfolio_register']



admin.site.register(PortfolioRegisterRecord, PortfolioRegisterRecordAdmin)
