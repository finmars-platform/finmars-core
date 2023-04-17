import traceback

from poms.configuration.utils import save_serialized_entity, save_serialized_attribute_type, save_serialized_layout

import logging
_l = logging.getLogger('poms.configuration')

def export_configuration_to_folder(source_directory, configuration, user):

    try:

        context = {
            'master_user': user.master_user,
            'member': user.member
        }

        save_serialized_entity('transactions.transactiontype',
                               configuration.configuration_code,
                               source_directory + '/transaction-types',
                               context)

        save_serialized_entity('instruments.instrumenttype',
                               configuration.configuration_code,
                               source_directory + '/instrument-types',
                               context)

        save_serialized_entity('accounts.accounttype',
                               configuration.configuration_code,
                               source_directory + '/account-types',
                               context)

        save_serialized_entity('csv_import.csvimportscheme',
                               configuration.configuration_code,
                               source_directory + '/simple-import-schemes',
                               context)

        save_serialized_entity('integrations.complextransactionimportscheme',
                               configuration.configuration_code,
                               source_directory + '/complex-transaction-import-schemes',
                               context)

        save_serialized_entity('procedures.pricingprocedure',
                               configuration.configuration_code,
                               source_directory + '/pricing-procedures',
                               context)

        save_serialized_entity('procedures.expressionprocedure',
                               configuration.configuration_code,
                               source_directory + '/expression-procedures',
                               context)

        save_serialized_entity('procedures.requestdatafileprocedure',
                               configuration.configuration_code,
                               source_directory + '/data-procedures',
                               context)

        save_serialized_entity('schedules.schedule',
                               configuration.configuration_code,
                               source_directory + '/schedules',
                               context)

        save_serialized_attribute_type('obj_attrs.genericattributetype',
                                       configuration.configuration_code,
                                       'instruments.instrument',
                                       source_directory + '/attribute-types/instrument',
                                       context)

        save_serialized_attribute_type('obj_attrs.genericattributetype',
                                       configuration.configuration_code,
                                       'accounts.account',
                                       source_directory + '/attribute-types/account',
                                       context)

        save_serialized_attribute_type('obj_attrs.genericattributetype',
                                       configuration.configuration_code,
                                       'portfolios.portfolio',
                                       source_directory + '/attribute-types/portfolio',
                                       context)

        save_serialized_attribute_type('obj_attrs.genericattributetype',
                                       configuration.configuration_code,
                                       'currencies.currency',
                                       source_directory + '/attribute-types/currency',
                                       context)

        save_serialized_attribute_type('obj_attrs.genericattributetype',
                                       configuration.configuration_code,
                                       'counterparties.counterparty',
                                       source_directory + '/attribute-types/counterparty',
                                       context)

        save_serialized_attribute_type('obj_attrs.genericattributetype',
                                       configuration.configuration_code,
                                       'counterparties.responsible',
                                       source_directory + '/attribute-types/responsible',
                                       context)

        save_serialized_entity('ui.dashboardlayout',
                               configuration.configuration_code,
                               source_directory + '/ui/layouts/dashboard',
                               context)

        save_serialized_entity('ui.contextmenulayout',
                               configuration.configuration_code,
                               source_directory + '/ui/layouts/context-menu',
                               context)

        # TODO Need to add user_code
        # save_serialized_entity('ui.complextransactionuserfieldmodel',
        #                                configuration.configuration_code,
        #                                source_directory + '/ui/user-fields/complex-transaction',
        #                                context)
        #
        # save_serialized_entity('ui.transactionuserfieldmodel',
        #                                configuration.configuration_code,
        #                                source_directory + '/ui/user-fields/transaction',
        #                                context)
        #
        # save_serialized_entity('ui.instrumentuserfieldmodel',
        #                                configuration.configuration_code,
        #                                source_directory + '/ui/user-fields/instrument',
        #                                context)

        save_serialized_layout('ui.listlayout',
                               configuration.configuration_code,
                               'portfolios.portfolio',
                               source_directory + '/ui/layouts/portfolio',
                               context)

        save_serialized_layout('ui.listlayout',
                               configuration.configuration_code,
                               'accounts.accounttype',
                               source_directory + '/ui/layouts/account-type',
                               context)

        save_serialized_layout('ui.listlayout',
                               configuration.configuration_code,
                               'accounts.account',
                               source_directory + '/ui/layouts/account',
                               context)

        save_serialized_layout('ui.listlayout',
                               configuration.configuration_code,
                               'instruments.instrumenttype',
                               source_directory + '/ui/layouts/instrument-type',
                               context)

        save_serialized_layout('ui.listlayout',
                               configuration.configuration_code,
                               'instruments.instrument',
                               source_directory + '/ui/layouts/instrument',
                               context)

        save_serialized_layout('ui.listlayout',
                               configuration.configuration_code,
                               'instruments.pricehistory',
                               source_directory + '/ui/layouts/price-history',
                               context)

        save_serialized_layout('ui.listlayout',
                               configuration.configuration_code,
                               'transactions.complextransaction',
                               source_directory + '/ui/layouts/complex-transaction',
                               context)

        save_serialized_layout('ui.listlayout',
                               configuration.configuration_code,
                               'transactions.transaction',
                               source_directory + '/ui/layouts/transaction',
                               context)
        save_serialized_layout('ui.listlayout',
                               configuration.configuration_code,
                               'transactions.transactiontype',
                               source_directory + '/ui/layouts/transaction-type',
                               context)

        save_serialized_layout('ui.listlayout',
                               configuration.configuration_code,
                               'currencies.currency',
                               source_directory + '/ui/layouts/currency',
                               context)

        save_serialized_layout('ui.listlayout',
                               configuration.configuration_code,
                               'currencies.currencyhistory',
                               source_directory + '/ui/layouts/currency-history',
                               context)

    except Exception as e:
        _l.error("Error exporting configuration e: %s" % e)
        _l.error("Error exporting configuration traceback: %s" % traceback.format_exc())
        raise Exception(e)