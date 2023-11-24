import inspect
import logging

from django.apps import apps
from rest_framework import viewsets
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin, DestroyModelMixin, ListModelMixin, \
    RetrieveModelMixin

from poms.common.mixins import ListLightModelMixin, ListEvModelMixin
from poms.configuration.utils import get_default_configuration_code
from poms.iam.models import AccessPolicy, Role
from poms.iam.utils import capitalize_first_letter, add_to_list_if_not_exists
from poms_app import settings

_l = logging.getLogger('poms.iam')


def generate_full_access_policies_for_viewsets(viewset_classes):
    access_policies = []

    for viewset_class in viewset_classes:
        viewset_name = viewset_class.__name__.replace('ViewSet', '')
        actions = []

        # _l.info('viewset_class %s' % viewset_class)

        service_name = settings.SERVICE_NAME

        configuration_code = get_default_configuration_code()
        user_code = configuration_code + ':' + service_name + '-' + viewset_name.lower() + '-full'


        name = capitalize_first_letter(viewset_name) + ' Full Access'

        from poms.users.models import Member
        finmars_bot = Member.objects.get(username="finmars_bot")

        try:
            access_policy = AccessPolicy.objects.get(user_code=user_code)
        except Exception as e:
            access_policy = AccessPolicy.objects.create(user_code=user_code,
                                                        owner=finmars_bot,
                                                        configuration_code=configuration_code)

        access_policy.name = name

        if issubclass(viewset_class, CreateModelMixin):
            actions.append(f"{service_name}:{viewset_name}:create")

        if issubclass(viewset_class, RetrieveModelMixin):
            actions.append(f"{service_name}:{viewset_name}:retrieve")

        if issubclass(viewset_class, UpdateModelMixin):
            actions.append(f"{service_name}:{viewset_name}:update")

        if issubclass(viewset_class, DestroyModelMixin):
            actions.append(f"{service_name}:{viewset_name}:destroy")

        if issubclass(viewset_class, ListModelMixin):
            actions.append(f"{service_name}:{viewset_name}:list")

        if issubclass(viewset_class, ListLightModelMixin):
            actions.append(f"{service_name}:{viewset_name}:list_light")

        if issubclass(viewset_class, ListEvModelMixin):
            actions.append(f"{service_name}:{viewset_name}:list_ev_item")
            actions.append(f"{service_name}:{viewset_name}:list_ev_group")

        if len(actions):
            access_policy_json = {
                "Version": "2023-01-01",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": actions,
                        "Resource": "*"
                    }
                ]
            }

            access_policy.policy = access_policy_json
            access_policy.save()
        else:
            access_policy.delete()

    return access_policies


def generate_readonly_access_policies_for_viewsets(viewset_classes):
    access_policies = []

    for viewset_class in viewset_classes:
        viewset_name = viewset_class.__name__.replace('ViewSet', '')
        actions = []

        # _l.info('viewset_class %s' % viewset_class)

        service_name = settings.SERVICE_NAME

        configuration_code = get_default_configuration_code()
        user_code = configuration_code + ':' + service_name + '-' + viewset_name.lower() + '-readonly'

        name = capitalize_first_letter(viewset_name) + ' Readonly Access'
        service_name = settings.SERVICE_NAME

        from poms.users.models import Member
        finmars_bot = Member.objects.get(username="finmars_bot")

        try:
            access_policy = AccessPolicy.objects.get(user_code=user_code)
        except Exception as e:
            access_policy = AccessPolicy.objects.create(user_code=user_code,
                                                        owner=finmars_bot,
                                                        configuration_code=configuration_code)

        access_policy.name = name

        if issubclass(viewset_class, ListModelMixin):
            actions.append(f"{service_name}:{viewset_name}:list")

        if issubclass(viewset_class, RetrieveModelMixin):
            actions.append(f"{service_name}:{viewset_name}:retrieve")

        if issubclass(viewset_class, ListLightModelMixin):
            actions.append(f"{service_name}:{viewset_name}:list_light")

        if issubclass(viewset_class, ListEvModelMixin):
            actions.append(f"{service_name}:{viewset_name}:list_ev_item")
            actions.append(f"{service_name}:{viewset_name}:list_ev_group")

        if actions:
            access_policy_json = {
                "Version": "2023-01-01",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": actions,
                        "Resource": "*"
                    }
                ]
            }

            access_policy.policy = access_policy_json
            access_policy.save()
            access_policies.append(access_policy)
        else:
            access_policy.delete()

    return access_policies


def generate_balance_report_access_policy():
    service_name = settings.SERVICE_NAME

    configuration_code = get_default_configuration_code()
    user_code = configuration_code + ':' + service_name + '-balancereport'


    name = 'BalanceReport Access'

    from poms.users.models import Member
    finmars_bot = Member.objects.get(username="finmars_bot")

    try:
        access_policy = AccessPolicy.objects.get(user_code=user_code)
    except Exception as e:
        access_policy = AccessPolicy.objects.create(user_code=user_code,
                                                    owner=finmars_bot,
                                                    configuration_code=configuration_code)

    access_policy.name = name
    access_policy_json = {
        "Version": "2023-01-01",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": [
                    "finmars:BalanceReport:create",
                ],
                "Resource": "*"
            }
        ]
    }

    access_policy.policy = access_policy_json
    access_policy.save()

    return access_policy


def generate_pl_report_access_policy():
    service_name = settings.SERVICE_NAME

    configuration_code = get_default_configuration_code()
    user_code = configuration_code + ':' + service_name + '-plreport'

    name = 'PLReport Access'

    from poms.users.models import Member
    finmars_bot = Member.objects.get(username="finmars_bot")

    try:
        access_policy = AccessPolicy.objects.get(user_code=user_code)
    except Exception as e:
        access_policy = AccessPolicy.objects.create(user_code=user_code,
                                                    owner=finmars_bot,
                                                    configuration_code=configuration_code)

    access_policy.name = name
    access_policy_json = {
        "Version": "2023-01-01",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": [
                    "finmars:PlReport:create",
                ],
                "Resource": "*"
            }
        ]
    }

    access_policy.policy = access_policy_json
    access_policy.save()

    return access_policy


def generate_transaction_report_access_policy():
    service_name = settings.SERVICE_NAME

    configuration_code = get_default_configuration_code()
    user_code =  configuration_code + ':' + service_name + '-transactionreport'

    name = 'TransactionReport Access'

    from poms.users.models import Member
    finmars_bot = Member.objects.get(username="finmars_bot")

    try:
        access_policy = AccessPolicy.objects.get(user_code=user_code)
    except Exception as e:
        access_policy = AccessPolicy.objects.create(user_code=user_code,
                                                    owner=finmars_bot,
                                                    configuration_code=configuration_code)

    access_policy.name = name
    access_policy_json = {
        "Version": "2023-01-01",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": [
                    "finmars:TransactionReport:create",
                ],
                "Resource": "*"
            }
        ]
    }

    access_policy.policy = access_policy_json
    access_policy.save()

    return access_policy


def generate_transaction_view_access_policy():
    service_name = settings.SERVICE_NAME

    configuration_code = get_default_configuration_code()
    user_code = configuration_code + ':' + service_name + '-complextransaction-view'

    name = 'Complex Transaction View'

    from poms.users.models import Member
    finmars_bot = Member.objects.get(username="finmars_bot")

    try:
        access_policy = AccessPolicy.objects.get(user_code=user_code)
    except Exception as e:
        access_policy = AccessPolicy.objects.create(user_code=user_code,
                                                    owner=finmars_bot,
                                                    configuration_code=configuration_code)

    access_policy.name = name
    access_policy_json = {
        "Version": "2023-01-01",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": [
                    "finmars:ComplexTransaction:view",
                ],
                "Resource": "*"
            }
        ]
    }

    access_policy.policy = access_policy_json
    access_policy.save()

    return access_policy


def generate_transaction_book_access_policy():
    service_name = settings.SERVICE_NAME

    configuration_code = get_default_configuration_code()
    user_code = configuration_code + ':' + service_name + '-complextransaction-book'

    name = 'Complex Transaction Book'

    from poms.users.models import Member
    finmars_bot = Member.objects.get(username="finmars_bot")

    try:
        access_policy = AccessPolicy.objects.get(user_code=user_code)
    except Exception as e:
        access_policy = AccessPolicy.objects.create(user_code=user_code,
                                                    owner=finmars_bot,
                                                    configuration_code=configuration_code)

    access_policy.name = name
    access_policy_json = {
        "Version": "2023-01-01",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": [
                    "finmars:TransactionType:book",
                ],
                "Resource": "*"
            }
        ]
    }

    access_policy.policy = access_policy_json
    access_policy.save()

    return access_policy


def generate_transaction_rebook_access_policy():
    service_name = settings.SERVICE_NAME

    configuration_code = get_default_configuration_code()
    user_code = configuration_code + ':' + service_name + '-complextransaction-rebook'

    name = 'Complex Transaction Rebook'

    from poms.users.models import Member
    finmars_bot = Member.objects.get(username="finmars_bot")

    try:
        access_policy = AccessPolicy.objects.get(user_code=user_code)
    except Exception as e:
        access_policy = AccessPolicy.objects.create(user_code=user_code,
                                                    owner=finmars_bot,
                                                    configuration_code=configuration_code)

    access_policy.name = name
    access_policy_json = {
        "Version": "2023-01-01",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": [
                    "finmars:ComplexTransaction:rebook",
                ],
                "Resource": "*"
            }
        ]
    }

    access_policy.policy = access_policy_json
    access_policy.save()

    return access_policy


def generate_init_configuration_install_access_policy():

    service_name = settings.SERVICE_NAME

    configuration_code = get_default_configuration_code()
    user_code = configuration_code + ':' + service_name + '-newmembersetupconfiguration-install'

    name = 'NewMemberSetupConfiguration Install'

    from poms.users.models import Member
    finmars_bot = Member.objects.get(username="finmars_bot")

    try:
        access_policy = AccessPolicy.objects.get(user_code=user_code)
    except Exception as e:
        access_policy = AccessPolicy.objects.create(user_code=user_code,
                                                    owner=finmars_bot,
                                                    configuration_code=configuration_code)

    access_policy.name = name
    access_policy_json = {
        "Version": "2023-01-01",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": [
                    "finmars:NewMemberSetupConfiguration:install",
                ],
                "Resource": "*"
            }
        ]
    }

    access_policy.policy = access_policy_json
    access_policy.save()

    return access_policy


def generate_speicifc_policies_for_viewsets():

    generate_balance_report_access_policy()
    generate_pl_report_access_policy()
    generate_transaction_report_access_policy()
    generate_transaction_view_access_policy()
    generate_transaction_book_access_policy()
    generate_transaction_rebook_access_policy()
    generate_init_configuration_install_access_policy()


def generate_viewer_role(readonly_access_policies):

    configuration_code = get_default_configuration_code()

    from poms.users.models import Member
    finmars_bot = Member.objects.get(username="finmars_bot")

    try:
        role = Role.objects.get(user_code=configuration_code + ':viewer')
    except Exception as e:
        role = Role.objects.create(user_code=configuration_code + ':viewer', owner=finmars_bot, configuration_code=configuration_code)

    # _l.debug('generate_viewer_role.readonly_access_policies %s' % readonly_access_policies)

    extra_policies_user_codes = [
        configuration_code + ':finmars-balancereport',
        configuration_code + ':finmars-plreport',
        configuration_code + ':finmars-transactionreport',

        # UI project has only member related rules, so no worry to gave full access to it
        configuration_code + ':finmars-listlayout-full',
        configuration_code + ':finmars-editlayout-full',
        configuration_code + ':finmars-dashboardlayout-full',
        configuration_code + ':finmars-contextmenulayout-full',

        # For Init Configuration of any member

        configuration_code + ':finmars-newmembersetupconfiguration-install'

    ]

    extra_policies = list(AccessPolicy.objects.all().filter(user_code__in=extra_policies_user_codes))

    role.name = 'Viewer'
    role.description = 'Read Only Access to Data. Can view Reports, Transactions, Instruments, Portfolios etc.'

    readonly_access_policies.extend(extra_policies) # add more policies
    role.access_policies.set(readonly_access_policies)
    role.save()


def generate_full_data_manager_role():

    configuration_code = get_default_configuration_code()

    from poms.users.models import Member
    finmars_bot = Member.objects.get(username="finmars_bot")

    try:
        role = Role.objects.get(user_code=configuration_code + ':full-data-manager')
    except Exception as e:
        role = Role.objects.create(user_code=configuration_code +':full-data-manager', owner=finmars_bot, configuration_code=configuration_code)

    # _l.debug('generate_viewer_role.readonly_access_policies %s' % readonly_access_policies)

    role.name = 'Full Data Manager'
    role.description = 'Full Access to Data. Can book Transactions, create, edit and delete  Instruments, Portfolios,  Accounts etc.'

    access_policy_user_codes = [

        configuration_code + ':finmars-complextransaction-view',
        configuration_code + ':finmars-complextransaction-book',
        configuration_code + ':finmars-complextransaction-rebook',

        configuration_code + ':finmars-transactiontype-full',
        configuration_code + ':finmars-transactiontypeattributetype-readonly',

        configuration_code + ':finmars-transaction-full',
        configuration_code + ':finmars-complextransaction-full',
        configuration_code + ':finmars-complextransactionattributetype-readonly',

        configuration_code + ':finmars-portfolio-full',
        configuration_code + ':finmars-portfolioattributetype-readonly',
        configuration_code + ':finmars-account-full',
        configuration_code + ':finmars-accountattributetype-readonly',

        configuration_code + ':finmars-accounttype-readonly',
        configuration_code + ':finmars-accounttypeattributetype-readonly',


        configuration_code + ':finmars-instrument-full',
        configuration_code + ':finmars-instrumentattributetype-readonly',
        configuration_code + ':finmars-instrumenttype-readonly',
        configuration_code + ':finmars-instrumenttypeattributetype-readonly',


        configuration_code + ':finmars-currency-full',
        configuration_code + ':finmars-currencyattributetype-readonly',


        configuration_code + ':finmars-pricingpolicy-full',

        configuration_code + ':finmars-pricehistory-full',
        configuration_code + ':finmars-currencyhistory-full',

        configuration_code + ':finmars-counterparty-full',
        configuration_code + ':finmars-counterpartyattributetype-readonly',
        configuration_code + ':finmars-responsible-full',
        configuration_code + ':finmars-responsibleattributetype-readonly',

        configuration_code + ':finmars-strategy1-full',
        configuration_code + ':finmars-strategy1attributetype-readonly',
        configuration_code + ':finmars-strategy2-full',
        configuration_code + ':finmars-strategy2attributetype-readonly',
        configuration_code + ':finmars-strategy3-full',
        configuration_code + ':finmars-strategy3attributetype-readonly',

        configuration_code + ':finmars-referencetable-full', # ?? maybe should go to member role

        configuration_code + ':finmars-balancereport',
        configuration_code + ':finmars-balancereportcustomfield-full',

        configuration_code + ':finmars-plreport',
        configuration_code + ':finmars-plreportcustomfield-full',

        configuration_code + ':finmars-transactionreport',
        configuration_code + ':finmars-transactionreportcustomfield-full',

    ]

    access_policies = AccessPolicy.objects.filter(user_code__in=access_policy_user_codes)

    role.access_policies.set(access_policies)
    role.save()

def generate_base_data_manager_role():

    configuration_code = get_default_configuration_code()

    from poms.users.models import Member
    finmars_bot = Member.objects.get(username="finmars_bot")

    try:
        role = Role.objects.get(user_code=configuration_code + ':base-data-manager')
    except Exception as e:
        role = Role.objects.create(user_code=configuration_code + ':base-data-manager', owner=finmars_bot, configuration_code=configuration_code)

    # _l.debug('generate_viewer_role.readonly_access_policies %s' % readonly_access_policies)

    role.name = 'Base Data Manager'
    role.description = 'Only access to essentials. Can book Transactions, View Reports, View Prices.'

    access_policy_user_codes = [

        configuration_code + ':finmars-complextransaction-view',
        configuration_code + ':finmars-complextransaction-book',
        configuration_code + ':finmars-complextransaction-rebook',

        configuration_code + ':finmars-transactiontype-full',
        configuration_code + ':finmars-transactiontypeattributetype-readonly',

        configuration_code + ':finmars-transaction-full',
        configuration_code + ':finmars-complextransaction-full',
        configuration_code + ':finmars-complextransactionattributetype-readonly',

        # configuration_code + ':finmars-portfolio-full', # not for base manager. see full-data-manager
        configuration_code + ':finmars-portfolioattributetype-readonly',
        # configuration_code + ':finmars-account-full', # not for base manager. see full-data-manager
        configuration_code + ':finmars-accountattributetype-readonly',

        configuration_code + ':finmars-accounttype-readonly',
        configuration_code + ':finmars-accounttypeattributetype-readonly',


        # configuration_code + ':finmars-instrument-full', # not for base manager. see full-data-manager
        configuration_code + ':finmars-instrumentattributetype-readonly',
        configuration_code + ':finmars-instrumenttype-readonly',
        configuration_code + ':finmars-instrumenttypeattributetype-readonly',

        configuration_code + ':finmars-currency-full',
        configuration_code + ':finmars-currencyattributetype-readonly',

        configuration_code + ':finmars-pricingpolicy-full',

        configuration_code + ':finmars-pricehistory-full',
        configuration_code + ':finmars-currencyhistory-full',

        configuration_code + ':finmars-counterparty-full',
        configuration_code + ':finmars-counterpartyattributetype-readonly',
        configuration_code + ':finmars-responsible-full',
        configuration_code + ':finmars-responsibleattributetype-readonly',

        configuration_code + ':finmars-strategy1-full',
        configuration_code + ':finmars-strategy1attributetype-readonly',
        configuration_code + ':finmars-strategy2-full',
        configuration_code + ':finmars-strategy2attributetype-readonly',
        configuration_code + ':finmars-strategy3-full',
        configuration_code + ':finmars-strategy3attributetype-readonly',

        configuration_code + ':finmars-referencetable-full', # ?? maybe should go to member role

        configuration_code + ':finmars-balancereport',
        configuration_code + ':finmars-balancereportcustomfield-full',

        configuration_code + ':finmars-plreport',
        configuration_code + ':finmars-plreportcustomfield-full',

        configuration_code + ':finmars-transactionreport',
        configuration_code + ':finmars-transactionreportcustomfield-full',

    ]

    access_policies = AccessPolicy.objects.filter(user_code__in=access_policy_user_codes)

    role.access_policies.set(access_policies)
    role.save()


def generate_member_role():

    configuration_code = get_default_configuration_code()

    from poms.users.models import Member
    finmars_bot = Member.objects.get(username="finmars_bot")

    try:
        role = Role.objects.get(user_code=configuration_code + ':member')
    except Exception as e:
        role = Role.objects.create(user_code=configuration_code + ':member', owner=finmars_bot, configuration_code=configuration_code)

    # _l.debug('generate_viewer_role.readonly_access_policies %s' % readonly_access_policies)

    role.name = 'Member'
    role.description = 'Full Access to own Report/Data Layouts, Input Form Layouts, Dashboard Layouts, Color Pallets etc.'

    access_policy_user_codes = [


        configuration_code + ':finmars-listlayout-full',
        configuration_code + ':finmars-editlayout-full',
        configuration_code + ':finmars-dashboardlayout-full',
        configuration_code + ':finmars-contextmenulayout-full',

        configuration_code + ':finmars-colorpalette-full',
        configuration_code + ':finmars-entitytooltip-full',
        configuration_code + ':finmars-templatelayout-full',

        configuration_code + ':finmars-ecosystemdefault-readonly',
        configuration_code + ':finmars-complextransactionuserfield-readonly',
        configuration_code + ':finmars-transactionuserfield-readonly',
        configuration_code + ':finmars-instrumentuserfield-readonly',

        configuration_code + ':finmars-configuration-readonly'

    ]

    access_policies = AccessPolicy.objects.filter(user_code__in=access_policy_user_codes)

    role.access_policies.set(access_policies)
    role.save()


def generate_configuration_manager_role():

    configuration_code = get_default_configuration_code()

    from poms.users.models import Member
    finmars_bot = Member.objects.get(username="finmars_bot")

    try:
        role = Role.objects.get(user_code=configuration_code + ':configuration-manager')
    except Exception as e:
        role = Role.objects.create(user_code=configuration_code + ':configuration-manager',
                                   owner=finmars_bot,
                                   configuration_code=configuration_code)

    # _l.debug('generate_viewer_role.readonly_access_policies %s' % readonly_access_policies)

    role.name = 'Configuration Manager'
    role.description = 'Full Access to Space Settings. Can create, edit and delete Transaction Types, Instrument Types, Transaction Import Schemes, Procedures etc.'

    '''
    Exclude IAM and Members Access Policies from Configuration Manager Role
    '''
    exclude_policies = [configuration_code + ':finmars-group-full',
                        configuration_code + ':finmars-role-full',
                        configuration_code + ':finmars-accesspolicy-full',
                        configuration_code + ':finmars-usermember-full',
                        configuration_code + ':finmars-member-full'
                        ]

    access_policies = AccessPolicy.objects.all().filter(user_code__icontains='-full').exclude(
        user_code__in=exclude_policies)

    role.access_policies.set(access_policies)

    role.save()


def get_viewsets_from_app(app_name):
    app_config = apps.get_app_config(app_name)
    viewset_classes = []

    for model_name, model_class in app_config.models.items():

        # _l.info('get_viewsets_from_app.model_name %s' % model_name)
        # _l.info('get_viewsets_from_app.app_config.name %s' % app_config.name)

        module_path = f'{app_config.name}.views'

        try:
            viewsets_module = __import__(module_path, fromlist=[model_name])
        except ImportError:
            continue

        for name, obj in inspect.getmembers(viewsets_module):
            if inspect.isclass(obj) and issubclass(obj, viewsets.ViewSetMixin) and obj != viewsets.ViewSetMixin:
                if "abstract" not in name.lower():
                    viewset_classes.append(obj)

    return viewset_classes


def get_viewsets_from_all_apps():
    all_viewsets = []

    for app_config in apps.get_app_configs():
        if not app_config.name.startswith('poms'):
            continue  # Skip Django's built-in apps

        app_viewsets = get_viewsets_from_app(app_config.label)
        all_viewsets.extend(app_viewsets)

    return all_viewsets

def patch_generated_policies():

    configuration_code = get_default_configuration_code()

    item = AccessPolicy.objects.get(user_code=configuration_code + ':finmars-listlayout-readonly')
    add_to_list_if_not_exists('finmars:ListLayout:ping', item.policy['Statement'][0]["Action"])
    item.save()

    item = AccessPolicy.objects.get(user_code=configuration_code + ':finmars-listlayout-full')
    add_to_list_if_not_exists('finmars:ListLayout:ping', item.policy['Statement'][0]["Action"])
    item.save()

def create_base_iam_access_policies_templates():

    _l = logging.getLogger('provision')

    viewsets = get_viewsets_from_all_apps()

    # _l.info('viewsets %s' % viewsets)
    _l.info('create_base_iam_access_policies_templates.viewsets %s' % len(viewsets))

    configuration_code = get_default_configuration_code()

    if AccessPolicy.objects.filter(configuration_code=configuration_code).count() == 0:

        _l.info('create_base_iam_access_policies_templates Access Policies are not found. Generating...')

        generate_full_access_policies_for_viewsets(viewsets)

        _l.info('create_base_iam_access_policies_templates.generate_full_access_policies_for_viewsets done')
        readonly_access_policies = generate_readonly_access_policies_for_viewsets(viewsets)

        _l.info('create_base_iam_access_policies_templates.generate_readonly_access_policies_for_viewsets done')

        _l.info('create_base_iam_access_policies_templates.readonly_access_policies %s' % len(readonly_access_policies))

        generate_speicifc_policies_for_viewsets()

        _l.info('create_base_iam_access_policies_templates.generate_speicifc_policies_for_viewsets done')

        patch_generated_policies()

        _l.info('create_base_iam_access_policies_templates.patch_generated_policies done')

        generate_viewer_role(readonly_access_policies)

    _l.info('create_base_iam_access_policies_templates.going to generate roles')

    generate_full_data_manager_role()
    generate_base_data_manager_role()
    generate_configuration_manager_role()
    generate_member_role()

    _l.info('create_base_iam_access_policies_templates.generating roles done')