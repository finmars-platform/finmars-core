from poms.configuration.utils import save_serialized_entity, save_serialized_attribute_type


def export_configuration_to_folder(source_directory, configuration, user):
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
