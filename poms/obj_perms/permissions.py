from rest_framework.permissions import BasePermission

from poms.obj_perms.utils import get_granted_permissions


class PomsObjectPermission(BasePermission):
    perms_map = {
        'GET': [],
        'OPTIONS': [],
        'HEAD': [],

        'POST': ['add_%(model_name)s'],
        'PUT': ['change_%(model_name)s'],
        'PATCH': ['change_%(model_name)s'],
        # 'DELETE': ['delete_%(model_name)s'],
        'DELETE': ['change_%(model_name)s'],
    }

    def get_required_object_permissions(self, method, model_cls):
        kwargs = {
            'app_label': model_cls._meta.app_label,
            'model_name': model_cls._meta.model_name
        }
        return {perm % kwargs for perm in self.perms_map[method]}

    def has_object_permission(self, request, view, obj):
        # member = request.user.member
        # if member.is_superuser:
        #     return True
        # req_perms = self.get_required_object_permissions(request.method, obj)
        # if not req_perms:
        #     return True
        # perms = get_granted_permissions(member, obj)
        # return req_perms.issubset(perms)
        return self.simple_has_object_permission(request.user.member, request.method, obj)

    def simple_has_object_permission(self, member, http_method, obj):

        if member.is_superuser:
            return True
        req_perms = self.get_required_object_permissions(http_method, obj)
        if not req_perms:
            return True
        perms = get_granted_permissions(member, obj)
        return req_perms.issubset(perms)


class PomsFunctionPermission(BasePermission):

    def has_permission(self, request, view):

        member = request.user.member

        if member.is_owner or member.is_admin:
            has_access = True
            return has_access

        has_access = False

        url_to_function_map = {
            '/api/v1/import/csv-validate/': 'function.import_data',
            '/api/v1/import/csv/': 'function.import_data',
            '/api/v1/import/complex-transaction-csv-file-import-validate/': 'function.import_transactions',
            '/api/v1/import/complex-transaction-csv-file-import/': 'function.import_transactions',
            # '/api/v1/import/csv/': 'function.import_complex',
            '/api/v1/import/instrument/': 'function.provider_download_instrument',
            '/api/v1/import/pricing/': 'function.provider_download_price',
        }

        for group in member.groups.all():

            if group.permission_table:
                if group.permission_table['function']:
                    for item in group.permission_table['function']:
                        if item['content_type'] == url_to_function_map[request.path]:
                            if item['data']:
                                if item['data']['creator_view']:
                                    has_access = True

        return has_access


class PomsConfigurationPermission(BasePermission):

    def has_permission(self, request, view):

        member = request.user.member

        if member.is_owner or member.is_admin:
            has_access = True
            return has_access

        if request.method == 'GET':
            has_access = True
            return has_access

        has_access = False

        url_to_function_map = {

            '/api/v1/portfolios/portfolio-attribute-type/': 'obj_attrs.attributetype',
            '/api/v1/accounts/account-attribute-type/': 'obj_attrs.attributetype',
            '/api/v1/instruments/instrument-attribute-type/': 'obj_attrs.attributetype',
            '/api/v1/counterparties/counterparty-attribute-type/': 'obj_attrs.attributetype',
            '/api/v1/counterparties/responsible-attribute-type/': 'obj_attrs.attributetype',
            '/api/v1/currencies/currency-attribute-type/': 'obj_attrs.attributetype',
            '/api/v1/strategies/1/strategy-attribute-type/': 'obj_attrs.attributetype',
            '/api/v1/strategies/2/strategy-attribute-type/': 'obj_attrs.attributetype',
            '/api/v1/strategies/3/strategy-attribute-type/': 'obj_attrs.attributetype',

            '/api/v1/accounts/account-type-attribute-type/': 'obj_attrs.attributetype',
            '/api/v1/instruments/instrument-type-attribute-type/': 'obj_attrs.attributetype',
            '/api/v1/transactions/transaction-type-attribute-type/': 'obj_attrs.attributetype',

            '/api/v1/reference-tables/reference-table/': 'reference_tables.referencetable',
            '/api/v1/ui/template-layout/': 'ui.templatelayout',

            '/api/v1/import/portfolio-mapping/': 'integrations.mappingtable',
            '/api/v1/import/account-mapping/': 'integrations.mappingtable',
            '/api/v1/import/instrument-mapping/': 'integrations.mappingtable',
            '/api/v1/import/responsible-mapping/': 'integrations.mappingtable',
            '/api/v1/import/counterparty-mapping/': 'integrations.mappingtable',
            '/api/v1/import/currency-mapping/': 'integrations.mappingtable',
            '/api/v1/import/strategy1-mapping/': 'integrations.mappingtable',
            '/api/v1/import/strategy2-mapping/': 'integrations.mappingtable',
            '/api/v1/import/strategy3-mapping/': 'integrations.mappingtable',
            '/api/v1/import/account-type-mapping/': 'integrations.mappingtable',
            '/api/v1/import/instrument-type-mapping/': 'integrations.mappingtable',
            '/api/v1/import/pricing-policy-mapping/': 'integrations.mappingtable',
            '/api/v1/import/price-download-scheme-mapping/': 'integrations.mappingtable',
            '/api/v1/import/daily-pricing-model-mapping/': 'integrations.mappingtable',
            '/api/v1/import/payment-size-detail-mapping/': 'integrations.mappingtable',
            '/api/v1/import/accrual-calculation-model-mapping/': 'integrations.mappingtable',
            '/api/v1/import/periodicity-mapping/': 'integrations.mappingtable',

            '/api/v1/import/price-download-scheme/': 'integrations.pricedownloadscheme',
            '/api/v1/import/instrument-scheme/': 'integrations.instrumentdownloadscheme',
            '/api/v1/import/csv/scheme/': 'csv_import.csvimportscheme',
            '/api/v1/import/complex-transaction-import-scheme/': 'integrations.complextransactionimportscheme',
            '/api/v1/import/complex/scheme/': 'complex_import.compleximportscheme',
            '/api/v1/ui/instrument-user-field/': 'ui.userfield',
        }

        if request.path in url_to_function_map:

            for group in member.groups.all():

                if group.permission_table:
                    if group.permission_table['configuration']:
                        for item in group.permission_table['configuration']:
                                if item['content_type'] == url_to_function_map[request.path]:
                                    if item['data']:
                                        if item['data']['creator_change']:
                                            has_access = True
        else:
            has_access = True

        return has_access
