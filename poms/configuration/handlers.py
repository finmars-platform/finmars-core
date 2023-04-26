import logging
import traceback

from poms.configuration.export_helpers import export_instrument_types, export_pricing_policies
from poms.configuration.utils import save_serialized_entity, save_serialized_attribute_type, save_serialized_layout, \
    copy_directory
from poms_app import settings

_l = logging.getLogger('poms.configuration')

from poms.common.storage import get_storage

storage = get_storage()

def export_workflows_to_directory(source_directory, configuration, master_user, member):

    source_directory + '/workflows'

    configuration_code_as_path = '/'.join(configuration.configuration_code.split('.'))

    workflows_dir = settings.BASE_API_URL + '/workflows/' + configuration_code_as_path + '/'

    _l.info("export_workflows_to_folder.Workflows source: %s" % workflows_dir)
    _l.info("export_workflows_to_folder.Workflows destination: %s" % source_directory + '/workflows')

    storage.download_directory(workflows_dir, source_directory + '/workflows')

def export_configuration_to_directory(source_directory, configuration, master_user, member):
    try:

        context = {
            'master_user': master_user,
            'member': member
        }

        _l.info("Going to export: transactions.transactiontype")

        save_serialized_entity('transactions.transactiontypegroup',
                               configuration.configuration_code,
                               source_directory + '/transaction-type-groups',
                               context)

        save_serialized_entity('transactions.transactiontype',
                               configuration.configuration_code,
                               source_directory + '/transaction-types',
                               context)

        _l.info("Exported: transactions.transactiontype")

        _l.info("Going to export: instruments.instrumenttype")

        # save_serialized_entity('instruments.instrumenttype',
        #                        configuration.configuration_code,
        #                        source_directory + '/instrument-types',
        #                        context)

        export_instrument_types(configuration.configuration_code,
                                                        source_directory + '/instrument-types',
                                                        master_user, member)

        _l.info("Exported: instruments.instrumenttype")

        save_serialized_entity('accounts.accounttype',
                               configuration.configuration_code,
                               source_directory + '/account-types',
                               context)

        _l.info("Going to export: accounts.accounttype")

        export_pricing_policies(configuration.configuration_code, source_directory + '/pricing-policies', master_user, member)


        _l.info("Exported: accounts.accounttype")

        _l.info("Going to export: csv_import.csvimportscheme")

        save_serialized_entity('csv_import.csvimportscheme',
                               configuration.configuration_code,
                               source_directory + '/simple-import-schemes',
                               context)

        _l.info("Exported: csv_import.csvimportscheme")

        _l.info("Going to export: integrations.complextransactionimportscheme")

        save_serialized_entity('integrations.complextransactionimportscheme',
                               configuration.configuration_code,
                               source_directory + '/complex-transaction-import-schemes',
                               context)

        _l.info("Exported: integrations.complextransactionimportscheme")

        _l.info("Going to export: integrations.instrumentdownloadscheme")

        save_serialized_entity('integrations.instrumentdownloadscheme',
                               configuration.configuration_code,
                               source_directory + '/instrument-download-schemes',
                               context)

        _l.info("Exported: integrations.instrumentdownloadscheme")

        _l.info("Going to export: pricing.instrumentpricingscheme")

        save_serialized_entity('pricing.instrumentpricingscheme',
                               configuration.configuration_code,
                               source_directory + '/instrument-pricing-schemes',
                               context)

        _l.info("Exported: pricing.instrumentpricingscheme")

        _l.info("Going to export: pricing.currencypricingscheme")

        save_serialized_entity('pricing.currencypricingscheme',
                               configuration.configuration_code,
                               source_directory + '/currency-pricing-schemes',
                               context)

        _l.info("Exported: pricing.currencypricingscheme")

        _l.info("Going to export: procedures.pricingprocedure")

        save_serialized_entity('procedures.pricingprocedure',
                               configuration.configuration_code,
                               source_directory + '/pricing-procedures',
                               context)

        _l.info("Exported: procedures.pricingprocedure")

        _l.info("Going to export: procedures.expressionprocedure")

        save_serialized_entity('procedures.expressionprocedure',
                               configuration.configuration_code,
                               source_directory + '/expression-procedures',
                               context)

        _l.info("Exported: procedures.expressionprocedure")

        _l.info("Going to export: procedures.requestdatafileprocedure")

        save_serialized_entity('procedures.requestdatafileprocedure',
                               configuration.configuration_code,
                               source_directory + '/data-procedures',
                               context)

        _l.info("Exported: procedures.requestdatafileprocedure")

        _l.info("Going to export: schedules.schedule")

        save_serialized_entity('schedules.schedule',
                               configuration.configuration_code,
                               source_directory + '/schedules',
                               context)

        _l.info("Exported: schedules.schedule")

        _l.info("Going to export: obj_attrs.genericattributetype")

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

        _l.info("Exported: obj_attrs.genericattributetype")

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
