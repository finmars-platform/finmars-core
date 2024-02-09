import logging
import traceback

from poms.common.models import ProxyRequest, ProxyUser
from poms.common.storage import get_storage
from poms.configuration.export_helpers import (
    export_instrument_types,
    export_pricing_policies,
    export_transaction_types,
)
from poms.configuration.utils import (
    save_serialized_attribute_type,
    save_serialized_custom_fields,
    save_serialized_entity,
    save_serialized_entity_layout,
    save_serialized_layout,
)
from poms_app import settings

_l = logging.getLogger("poms.configuration")

storage = get_storage()


def export_workflows_to_directory(source_directory, configuration, master_user, member):
    configuration_code_as_path = "/".join(configuration.configuration_code.split("."))

    workflows_dir = (
            settings.BASE_API_URL + "/workflows/" + configuration_code_as_path + "/"
    )

    _l.info("export_workflows_to_folder.Workflows source: %s" % workflows_dir)
    _l.info(
        "export_workflows_to_folder.Workflows destination: %s" % source_directory
        + "/workflows"
    )

    if storage.folder_exists_and_has_files(workflows_dir):
        _l.info("export_workflows_to_folder exists")
        storage.download_directory(workflows_dir, source_directory + "/workflows")
    else:
        _l.info(
            "No workflows found for configuration: %s"
            % configuration.configuration_code
        )


def export_configuration_to_directory(
        source_directory, configuration, master_user, member
):
    try:
        proxy_user = ProxyUser(member, master_user)
        proxy_request = ProxyRequest(proxy_user)

        context = {
            "request": proxy_request,
            "master_user": master_user,
            "member": member,
        }

        _l.info("Going to export: transactions.transactiontype")

        save_serialized_entity(
            "transactions.transactiontypegroup",
            configuration.configuration_code,
            source_directory + "/transaction-type-groups",
            context,
        )

        export_transaction_types(
            configuration.configuration_code,
            source_directory + "/transaction-types",
            master_user,
            member,
        )

        _l.info("Exported: transactions.transactiontype")

        _l.info("Going to export: instruments.instrumenttype")

        export_instrument_types(
            configuration.configuration_code,
            source_directory + "/instrument-types",
            master_user,
            member,
        )

        _l.info("Exported: instruments.instrumenttype")

        save_serialized_entity(
            "accounts.accounttype",
            configuration.configuration_code,
            source_directory + "/account-types",
            context,
        )

        _l.info("Going to export: portfolios.portfoliotype")

        save_serialized_entity(
            "portfolios.portfoliotype",
            configuration.configuration_code,
            source_directory + "/portfolio-types",
            context,
        )

        _l.info("Going to export: accounts.accounttype")

        export_pricing_policies(
            configuration.configuration_code,
            source_directory + "/pricing-policies",
            master_user,
            member,
        )

        _l.info("Exported: accounts.accounttype")

        _l.info("Going to export: csv_import.csvimportscheme")

        save_serialized_entity(
            "csv_import.csvimportscheme",
            configuration.configuration_code,
            source_directory + "/simple-import-schemes",
            context,
        )

        _l.info("Exported: csv_import.csvimportscheme")

        _l.info("Going to export: integrations.complextransactionimportscheme")

        save_serialized_entity(
            "integrations.complextransactionimportscheme",
            configuration.configuration_code,
            source_directory + "/complex-transaction-import-schemes",
            context,
        )

        _l.info("Exported: integrations.complextransactionimportscheme")

        _l.info("Going to export: integrations.mappingtable")

        save_serialized_entity(
            "integrations.mappingtable",
            configuration.configuration_code,
            source_directory + "/mapping-tables",
            context,
        )

        _l.info("Exported: integrations.mappingtable")

        _l.info("Going to export: integrations.instrumentdownloadscheme")

        save_serialized_entity(
            "integrations.instrumentdownloadscheme",
            configuration.configuration_code,
            source_directory + "/instrument-download-schemes",
            context,
        )

        _l.info("Exported: integrations.instrumentdownloadscheme")

        _l.info("Going to export: pricing.instrumentpricingscheme")

        save_serialized_entity(
            "pricing.instrumentpricingscheme",
            configuration.configuration_code,
            source_directory + "/instrument-pricing-schemes",
            context,
        )

        _l.info("Exported: pricing.instrumentpricingscheme")

        _l.info("Going to export: pricing.currencypricingscheme")

        save_serialized_entity(
            "pricing.currencypricingscheme",
            configuration.configuration_code,
            source_directory + "/currency-pricing-schemes",
            context,
        )

        _l.info("Exported: pricing.currencypricingscheme")

        _l.info("Going to export: procedures.pricingprocedure")

        save_serialized_entity(
            "procedures.pricingprocedure",
            configuration.configuration_code,
            source_directory + "/pricing-procedures",
            context,
        )

        _l.info("Exported: procedures.pricingprocedure")

        _l.info("Going to export: procedures.expressionprocedure")

        save_serialized_entity(
            "procedures.expressionprocedure",
            configuration.configuration_code,
            source_directory + "/expression-procedures",
            context,
        )

        _l.info("Exported: procedures.expressionprocedure")

        _l.info("Going to export: procedures.requestdatafileprocedure")

        save_serialized_entity(
            "procedures.requestdatafileprocedure",
            configuration.configuration_code,
            source_directory + "/data-procedures",
            context,
        )

        _l.info("Exported: procedures.requestdatafileprocedure")

        _l.info("Going to export: schedules.schedule")

        save_serialized_entity(
            "schedules.schedule",
            configuration.configuration_code,
            source_directory + "/schedules",
            context,
        )

        _l.info("Exported: schedules.schedule")

        save_serialized_entity(
            "configuration.newmembersetupconfiguration",
            configuration.configuration_code,
            source_directory + "/new-user-setups",
            context,
        )

        _l.info("Going to export: obj_attrs.genericattributetype")

        save_serialized_attribute_type(
            "obj_attrs.genericattributetype",
            configuration.configuration_code,
            "instruments.instrument",
            source_directory + "/attribute-types/instrument",
            context,
        )

        save_serialized_attribute_type(
            "obj_attrs.genericattributetype",
            configuration.configuration_code,
            "accounts.account",
            source_directory + "/attribute-types/account",
            context,
        )

        save_serialized_attribute_type(
            "obj_attrs.genericattributetype",
            configuration.configuration_code,
            "portfolios.portfolio",
            source_directory + "/attribute-types/portfolio",
            context,
        )

        save_serialized_attribute_type(
            "obj_attrs.genericattributetype",
            configuration.configuration_code,
            "currencies.currency",
            source_directory + "/attribute-types/currency",
            context,
        )

        save_serialized_attribute_type(
            "obj_attrs.genericattributetype",
            configuration.configuration_code,
            "counterparties.counterparty",
            source_directory + "/attribute-types/counterparty",
            context,
        )

        _l.info("Exported: obj_attrs.genericattributetype")

        save_serialized_attribute_type(
            "obj_attrs.genericattributetype",
            configuration.configuration_code,
            "counterparties.responsible",
            source_directory + "/attribute-types/responsible",
            context,
        )

        save_serialized_custom_fields(
            configuration.configuration_code,
            "reports.balancereport",
            source_directory + "/custom-columns/balance-report",
            context,
        )

        save_serialized_custom_fields(
            configuration.configuration_code,
            "reports.plreport",
            source_directory + "/custom-columns/pl-report",
            context,
        )

        save_serialized_custom_fields(
            configuration.configuration_code,
            "reports.transactionreport",
            source_directory + "/custom-columns/transaction-report",
            context,
        )

        # save_serialized_entity('ui.dashboardlayout',
        #                        configuration.configuration_code,
        #                        source_directory + '/ui/layouts/dashboard',
        #                        context)

        save_serialized_layout(
            "ui.dashboardlayout",
            configuration.configuration_code,
            source_directory + "/ui/layouts/dashboard",
            context,
        )

        save_serialized_layout(
            "ui.memberlayout",
            configuration.configuration_code,
            source_directory + "/ui/layouts/member-layout",
            context,
        )

        save_serialized_layout(
            "ui.contextmenulayout",
            configuration.configuration_code,
            source_directory + "/ui/layouts/context-menu",
            context,
        )

        save_serialized_layout(
            "ui.mobilelayout",
            configuration.configuration_code,
            source_directory + "/ui/layouts/mobile-layout",
            context,
        )

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

        save_serialized_entity_layout(
            "ui.listlayout",
            configuration.configuration_code,
            "portfolios.portfolio",
            source_directory + "/ui/layouts/portfolio",
            context,
        )

        save_serialized_entity_layout(
            "ui.listlayout",
            configuration.configuration_code,
            "portfolios.portfolioregister",
            source_directory + "/ui/layouts/portfolio-register",
            context,
        )

        save_serialized_entity_layout(
            "ui.listlayout",
            configuration.configuration_code,
            "portfolios.portfolioregisterrecord",
            source_directory + "/ui/layouts/portfolio-register-record",
            context,
        )

        save_serialized_entity_layout(
            "ui.listlayout",
            configuration.configuration_code,
            "portfolios.portfoliohistory",
            source_directory + "/ui/layouts/portfolio-history",
            context,
        )

        save_serialized_entity_layout(
            "ui.listlayout",
            configuration.configuration_code,
            "accounts.accounttype",
            source_directory + "/ui/layouts/account-type",
            context,
        )

        save_serialized_entity_layout(
            "ui.listlayout",
            configuration.configuration_code,
            "accounts.account",
            source_directory + "/ui/layouts/account",
            context,
        )

        save_serialized_entity_layout(
            "ui.listlayout",
            configuration.configuration_code,
            "instruments.instrumenttype",
            source_directory + "/ui/layouts/instrument-type",
            context,
        )

        save_serialized_entity_layout(
            "ui.listlayout",
            configuration.configuration_code,
            "instruments.instrument",
            source_directory + "/ui/layouts/instrument",
            context,
        )

        save_serialized_entity_layout(
            "ui.listlayout",
            configuration.configuration_code,
            "instruments.pricehistory",
            source_directory + "/ui/layouts/price-history",
            context,
        )

        save_serialized_entity_layout(
            "ui.listlayout",
            configuration.configuration_code,
            "transactions.complextransaction",
            source_directory + "/ui/layouts/complex-transaction",
            context,
        )

        save_serialized_entity_layout(
            "ui.listlayout",
            configuration.configuration_code,
            "transactions.transaction",
            source_directory + "/ui/layouts/transaction",
            context,
        )
        save_serialized_entity_layout(
            "ui.listlayout",
            configuration.configuration_code,
            "transactions.transactiontype",
            source_directory + "/ui/layouts/transaction-type",
            context,
        )

        save_serialized_entity_layout(
            "ui.listlayout",
            configuration.configuration_code,
            "currencies.currency",
            source_directory + "/ui/layouts/currency",
            context,
        )

        save_serialized_entity_layout(
            "ui.listlayout",
            configuration.configuration_code,
            "currencies.currencyhistory",
            source_directory + "/ui/layouts/currency-history",
            context,
        )

        save_serialized_entity_layout(
            "ui.listlayout",
            configuration.configuration_code,
            "reports.balancereport",
            source_directory + "/ui/layouts/balance-report",
            context,
        )

        save_serialized_entity_layout(
            "ui.listlayout",
            configuration.configuration_code,
            "reports.plreport",
            source_directory + "/ui/layouts/pl-report",
            context,
        )

        save_serialized_entity_layout(
            "ui.listlayout",
            configuration.configuration_code,
            "reports.transactionreport",
            source_directory + "/ui/layouts/transaction-report",
            context,
        )

        save_serialized_entity_layout(
            "ui.listlayout",
            configuration.configuration_code,
            "reports.performancereport",
            source_directory + "/ui/layouts/performance-report",
            context,
        )

        save_serialized_entity_layout(
            "ui.listlayout",
            configuration.configuration_code,
            "counterparties.responsible",
            source_directory + "/ui/layouts/responsibles",
            context,
        )

        save_serialized_entity_layout(
            "ui.listlayout",
            configuration.configuration_code,
            "counterparties.counterparty",
            source_directory + "/ui/layouts/counterparties",
            context,
        )

        save_serialized_entity_layout(
            "ui.listlayout",
            configuration.configuration_code,
            "strategies.strategy1",
            source_directory + "/ui/layouts/strategies1",
            context,
        )

        save_serialized_entity_layout(
            "ui.listlayout",
            configuration.configuration_code,
            "strategies.strategy2",
            source_directory + "/ui/layouts/strategies2",
            context,
        )

        save_serialized_entity_layout(
            "ui.listlayout",
            configuration.configuration_code,
            "strategies.strategy3",
            source_directory + "/ui/layouts/strategies2",
            context,
        )

        save_serialized_entity_layout(
            "ui.listlayout",
            configuration.configuration_code,
            "pricing.pricehistoryerror",
            source_directory + "/ui/layouts/price-journal",
            context,
        )

        save_serialized_entity_layout(
            "ui.listlayout",
            configuration.configuration_code,
            "pricing.currencyhistoryerror",
            source_directory + "/ui/layouts/fxrate-journal",
            context,
        )

        save_serialized_entity_layout(
            "ui.listlayout",
            configuration.configuration_code,
            "integrations.complextransactionimportscheme",
            source_directory + "/ui/layouts/complex-transaction-import-scheme",
            context,
        )

        save_serialized_entity_layout(
            "ui.listlayout",
            configuration.configuration_code,
            "csv_import.csvimportscheme",
            source_directory + "/ui/layouts/simple-import-scheme",
            context,
        )

        # Form Layouts

        save_serialized_entity_layout(
            "ui.editlayout",
            configuration.configuration_code,
            "portfolios.portfolio",
            source_directory + "/ui/form-layouts/portfolio",
            context,
        )

        save_serialized_entity_layout(
            "ui.editlayout",
            configuration.configuration_code,
            "portfolios.portfoliohistory",
            source_directory + "/ui/form-layouts/portfolio-history",
            context,
        )

        save_serialized_entity_layout(
            "ui.editlayout",
            configuration.configuration_code,
            "accounts.accounttype",
            source_directory + "/ui/form-layouts/account-type",
            context,
        )

        save_serialized_entity_layout(
            "ui.editlayout",
            configuration.configuration_code,
            "accounts.account",
            source_directory + "/ui/form-layouts/account",
            context,
        )

        save_serialized_entity_layout(
            "ui.editlayout",
            configuration.configuration_code,
            "instruments.instrumenttype",
            source_directory + "/ui/form-layouts/instrument-type",
            context,
        )

        save_serialized_entity_layout(
            "ui.editlayout",
            configuration.configuration_code,
            "instruments.instrument",
            source_directory + "/ui/form-layouts/instrument",
            context,
        )

        save_serialized_entity_layout(
            "ui.editlayout",
            configuration.configuration_code,
            "instruments.pricehistory",
            source_directory + "/ui/form-layouts/price-history",
            context,
        )

        save_serialized_entity_layout(
            "ui.editlayout",
            configuration.configuration_code,
            "transactions.complextransaction",
            source_directory + "/ui/form-layouts/complex-transaction",
            context,
        )

        save_serialized_entity_layout(
            "ui.editlayout",
            configuration.configuration_code,
            "transactions.transaction",
            source_directory + "/ui/form-layouts/transaction",
            context,
        )
        save_serialized_entity_layout(
            "ui.editlayout",
            configuration.configuration_code,
            "transactions.transactiontype",
            source_directory + "/ui/form-layouts/transaction-type",
            context,
        )

        save_serialized_entity_layout(
            "ui.editlayout",
            configuration.configuration_code,
            "currencies.currency",
            source_directory + "/ui/form-layouts/currency",
            context,
        )

        save_serialized_entity_layout(
            "ui.editlayout",
            configuration.configuration_code,
            "currencies.currencyhistory",
            source_directory + "/ui/form-layouts/currency-history",
            context,
        )

        save_serialized_entity_layout(
            "ui.editlayout",
            configuration.configuration_code,
            "reports.balancereport",
            source_directory + "/ui/form-layouts/balance-report",
            context,
        )

        save_serialized_entity_layout(
            "ui.editlayout",
            configuration.configuration_code,
            "reports.plreport",
            source_directory + "/ui/form-layouts/pl-report",
            context,
        )

        save_serialized_entity_layout(
            "ui.editlayout",
            configuration.configuration_code,
            "reports.transactionreport",
            source_directory + "/ui/form-layouts/transaction-report",
            context,
        )

        save_serialized_entity_layout(
            "ui.editlayout",
            configuration.configuration_code,
            "counterparties.responsible",
            source_directory + "/ui/form-layouts/responsibles",
            context,
        )

        save_serialized_entity_layout(
            "ui.editlayout",
            configuration.configuration_code,
            "counterparties.counterparty",
            source_directory + "/ui/form-layouts/counterparties",
            context,
        )

        save_serialized_entity_layout(
            "ui.editlayout",
            configuration.configuration_code,
            "strategies.strategy1",
            source_directory + "/ui/form-layouts/strategies1",
            context,
        )

        save_serialized_entity_layout(
            "ui.editlayout",
            configuration.configuration_code,
            "strategies.strategy2",
            source_directory + "/ui/form-layouts/strategies2",
            context,
        )

        save_serialized_entity_layout(
            "ui.editlayout",
            configuration.configuration_code,
            "strategies.strategy3",
            source_directory + "/ui/form-layouts/strategies3",
            context,
        )

        save_serialized_entity_layout(
            "ui.editlayout",
            configuration.configuration_code,
            "pricing.pricehistoryerror",
            source_directory + "/ui/form-layouts/price-journal",
            context,
        )

        save_serialized_entity_layout(
            "ui.editlayout",
            configuration.configuration_code,
            "pricing.currencyhistoryerror",
            source_directory + "/ui/form-layouts/fxrate-journal",
            context,
        )

        save_serialized_entity_layout(
            "ui.editlayout",
            configuration.configuration_code,
            "portfolios.portfolioregister",
            source_directory + "/ui/form-layouts/portfolio-register",
            context,
        )

        save_serialized_entity_layout(
            "ui.editlayout",
            configuration.configuration_code,
            "portfolios.portfolioregisterrecord",
            source_directory + "/ui/form-layouts/portfolio-register-record",
            context,
        )

        save_serialized_entity_layout(
            "ui.editlayout",
            configuration.configuration_code,
            "transactions.transaction",
            source_directory + "/ui/form-layouts/transaction",
            context,
        )

        # Aliases

        try:
            save_serialized_entity(
                "ui.instrumentuserfield",
                configuration.configuration_code,
                source_directory + "/ui/instrument-user-fields",
                context,
            )

            save_serialized_entity(
                "ui.transactionuserfield",
                configuration.configuration_code,
                source_directory + "/ui/transaction-user-fields",
                context,
            )

            save_serialized_entity(
                "ui.complextransactionuserfield",
                configuration.configuration_code,
                source_directory + "/ui/complex-transaction-user-fields",
                context,
            )

        except Exception as e:
            _l.error("Could not export aliases e: %s" % e)

        #     IAM
        save_serialized_entity(
            "iam.group",
            configuration.configuration_code,
            source_directory + "/iam/groups",
            context,
        )
        save_serialized_entity(
            "iam.role",
            configuration.configuration_code,
            source_directory + "/iam/roles",
            context,
        )
        save_serialized_entity(
            "iam.accesspolicy",
            configuration.configuration_code,
            source_directory + "/iam/access-policies",
            context,
        )

        # Reference Table

        save_serialized_entity(
            "reference_tables.referencetable",
            configuration.configuration_code,
            source_directory + "/reference-tables",
            context,
        )

    except Exception as e:
        _l.error(f"Error exporting configuration {e} trace {traceback.format_exc()}")
        raise e
