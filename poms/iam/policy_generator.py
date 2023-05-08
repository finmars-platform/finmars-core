import inspect
import logging

from django.apps import apps
from rest_framework import viewsets
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin, DestroyModelMixin, ListModelMixin, \
    RetrieveModelMixin

from poms.common.mixins import ListLightModelMixin, ListEvModelMixin
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

        user_code = 'com.finmars.local:' + service_name + '-' + viewset_name.lower() + '-full'
        configuration_code = 'com.finmars.local'

        name = capitalize_first_letter(viewset_name) + ' Full Access'

        try:
            access_policy = AccessPolicy.objects.get(user_code=user_code)
        except Exception as e:
            access_policy = AccessPolicy.objects.create(user_code=user_code,
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

        user_code = 'com.finmars.local:' + service_name + '-' + viewset_name.lower() + '-readonly'
        configuration_code = 'com.finmars.local'

        name = capitalize_first_letter(viewset_name) + ' Readonly Access'
        service_name = settings.SERVICE_NAME

        try:
            access_policy = AccessPolicy.objects.get(user_code=user_code)
        except Exception as e:
            access_policy = AccessPolicy.objects.create(user_code=user_code,
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

    user_code = 'com.finmars.local:' + service_name + '-balancereport'
    configuration_code = 'com.finmars.local'

    name = 'BalanceReport Access'

    try:
        access_policy = AccessPolicy.objects.get(user_code=user_code)
    except Exception as e:
        access_policy = AccessPolicy.objects.create(user_code=user_code,
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

    user_code = 'com.finmars.local:' + service_name + '-plreport'
    configuration_code = 'com.finmars.local'

    name = 'PLReport Access'

    try:
        access_policy = AccessPolicy.objects.get(user_code=user_code)
    except Exception as e:
        access_policy = AccessPolicy.objects.create(user_code=user_code,
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

    user_code = 'com.finmars.local:' + service_name + '-transactionreport'
    configuration_code = 'com.finmars.local'

    name = 'TransactionReport Access'

    try:
        access_policy = AccessPolicy.objects.get(user_code=user_code)
    except Exception as e:
        access_policy = AccessPolicy.objects.create(user_code=user_code,
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

    user_code = 'com.finmars.local:' + service_name + '-complextransaction-view'
    configuration_code = 'com.finmars.local'

    name = 'Complex Transaction View'

    try:
        access_policy = AccessPolicy.objects.get(user_code=user_code)
    except Exception as e:
        access_policy = AccessPolicy.objects.create(user_code=user_code,
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

    user_code = 'com.finmars.local:' + service_name + '-complextransaction-book'
    configuration_code = 'com.finmars.local'

    name = 'Complex Transaction Book'

    try:
        access_policy = AccessPolicy.objects.get(user_code=user_code)
    except Exception as e:
        access_policy = AccessPolicy.objects.create(user_code=user_code,
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

    user_code = 'com.finmars.local:' + service_name + '-complextransaction-rebook'
    configuration_code = 'com.finmars.local'

    name = 'Complex Transaction Rebook'

    try:
        access_policy = AccessPolicy.objects.get(user_code=user_code)
    except Exception as e:
        access_policy = AccessPolicy.objects.create(user_code=user_code,
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



def generate_speicifc_policies_for_viewsets():

    generate_balance_report_access_policy()
    generate_pl_report_access_policy()
    generate_transaction_report_access_policy()
    generate_transaction_view_access_policy()
    generate_transaction_book_access_policy()
    generate_transaction_rebook_access_policy()


def generate_viewer_role(readonly_access_policies):
    try:
        role = Role.objects.get(user_code='com.finmars.local:viewer')
    except Exception as e:
        role = Role.objects.create(user_code='com.finmars.local:viewer', configuration_code='com.finmars.local')

    # _l.debug('generate_viewer_role.readonly_access_policies %s' % readonly_access_policies)

    extra_policies_user_codes = [
        'com.finmars.local:finmars-balancereport',
        'com.finmars.local:finmars-plreport',
        'com.finmars.local:finmars-transactionreport',
    ]

    extra_policies = list(AccessPolicy.objects.all().filter(user_code__in=extra_policies_user_codes))

    role.name = 'Viewer'
    role.description = 'Read Only Access to Data. Can view Reports, Transactions, Instruments, Portfolios etc.'

    readonly_access_policies.extend(extra_policies) # add more policies
    role.access_policies.set(readonly_access_policies)
    role.save()


def generate_data_manager_role():
    try:
        role = Role.objects.get(user_code='com.finmars.local:data-manager')
    except Exception as e:
        role = Role.objects.create(user_code='com.finmars.local:data-manager', configuration_code='com.finmars.local')

    # _l.debug('generate_viewer_role.readonly_access_policies %s' % readonly_access_policies)

    role.name = 'Data Manager'
    role.description = 'Full Access to Data. Can book Transactions, create, edit and delete  Instruments, Portfolios,  Accounts etc.'

    access_policy_user_codes = [

        'com.finmars.local:finmars-complextransaction-view',
        'com.finmars.local:finmars-complextransaction-book',
        'com.finmars.local:finmars-complextransaction-rebook',

        'com.finmars.local:finmars-transactiontype-full',
        'com.finmars.local:finmars-transactiontypeattributetype-readonly',

        'com.finmars.local:finmars-transaction-full',
        'com.finmars.local:finmars-complextransaction-full',
        'com.finmars.local:finmars-complextransactionattributetype-readonly',

        'com.finmars.local:finmars-portfolio-full',
        'com.finmars.local:finmars-portfolioattributetype-readonly',
        'com.finmars.local:finmars-account-full',
        'com.finmars.local:finmars-accountattributetype-readonly',

        'com.finmars.local:finmars-accounttype-readonly'
        'com.finmars.local:finmars-accounttypeattributetype-readonly',


        'com.finmars.local:finmars-instrument-full',
        'com.finmars.local:finmars-instrumentattributetype-readonly',
        'com.finmars.local:finmars-instrumenttype-readonly',
        'com.finmars.local:finmars-instrumenttypeattributetype-readonly',

        'com.finmars.local:finmars-pricehistory-full',
        'com.finmars.local:finmars-currencyhistory-full',

        'com.finmars.local:finmars-counterparty-full',
        'com.finmars.local:finmars-counterpartyattributetype-readonly',
        'com.finmars.local:finmars-responsible-full',
        'com.finmars.local:finmars-responsibleattributetype-readonly',

        'com.finmars.local:finmars-strategy1-full',
        'com.finmars.local:finmars-strategy1attributetype-readonly',
        'com.finmars.local:finmars-strategy2-full',
        'com.finmars.local:finmars-strategy2attributetype-readonly',
        'com.finmars.local:finmars-strategy3-full',
        'com.finmars.local:finmars-strategy3attributetype-readonly',

        'com.finmars.local:finmars-referencetable-full', # ?? maybe should go to member role

        'com.finmars.local:finmars-balancereport',
        'com.finmars.local:finmars-balancereportcustomfield-full',

        'com.finmars.local:finmars-plreport',
        'com.finmars.local:finmars-plreportcustomfield-full',

        'com.finmars.local:finmars-transactionreport',
        'com.finmars.local:finmars-transactionreportcustomfield-full',

    ]

    access_policies = AccessPolicy.objects.filter(user_code__in=access_policy_user_codes)

    role.access_policies.set(access_policies)
    role.save()


def generate_member_role():

    try:
        role = Role.objects.get(user_code='com.finmars.local:member')
    except Exception as e:
        role = Role.objects.create(user_code='com.finmars.local:member', configuration_code='com.finmars.local')

    # _l.debug('generate_viewer_role.readonly_access_policies %s' % readonly_access_policies)

    role.name = 'Member'
    role.description = 'Full Access to own Report/Data Layouts, Input Form Layouts, Dashboard Layouts, Color Pallets etc.'

    access_policy_user_codes = [


        'com.finmars.local:finmars-listlayout-full',
        'com.finmars.local:finmars-editlayout-full',
        'com.finmars.local:finmars-dashboardlayout-full',
        'com.finmars.local:finmars-contextmenulayout-full',

        'com.finmars.local:finmars-colorpalette-full',
        'com.finmars.local:finmars-entitytooltip-full',
        'com.finmars.local:finmars-templatelayout-full',

        'com.finmars.local:finmars-ecosystemdefault-readonly',
        'com.finmars.local:finmars-complextransactionuserfield-readonly',
        'com.finmars.local:finmars-transactionuserfield-readonly',
        'com.finmars.local:finmars-instrumentuserfield-readonly',

        'com.finmars.local:finmars-configuration-readonly'

    ]

    access_policies = AccessPolicy.objects.filter(user_code__in=access_policy_user_codes)

    role.access_policies.set(access_policies)
    role.save()


def generate_configuration_manager_role():
    try:
        role = Role.objects.get(user_code='com.finmars.local:configuration-manager')
    except Exception as e:
        role = Role.objects.create(user_code='com.finmars.local:configuration-manager',
                                   configuration_code='com.finmars.local')

    # _l.debug('generate_viewer_role.readonly_access_policies %s' % readonly_access_policies)

    role.name = 'Configuration Manager'
    role.description = 'Full Access to Space Settings. Can create, edit and delete Transaction Types, Instrument Types, Transaction Import Schemes, Procedures etc.'

    '''
    Exclude IAM and Members Access Policies from Configuration Manager Role
    '''
    exclude_policies = ['com.finmars.local:finmars-group-full',
                        'com.finmars.local:finmars-role-full',
                        'com.finmars.local:finmars-accesspolicy-full',
                        'com.finmars.local:finmars-usermember-full',
                        'com.finmars.local:finmars-member-full'
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

    item = AccessPolicy.objects.get(user_code='com.finmars.local:finmars-listlayout-readonly')
    add_to_list_if_not_exists('finmars:ListLayout:ping', item.policy['Statement'][0]["Action"])
    item.save()

    item = AccessPolicy.objects.get(user_code='com.finmars.local:finmars-listlayout-full')
    add_to_list_if_not_exists('finmars:ListLayout:ping', item.policy['Statement'][0]["Action"])
    item.save()

def create_base_iam_access_policies_templates():
    viewsets = get_viewsets_from_all_apps()

    # _l.info('viewsets %s' % viewsets)
    _l.info('viewsets %s' % len(viewsets))

    generate_full_access_policies_for_viewsets(viewsets)
    readonly_access_policies = generate_readonly_access_policies_for_viewsets(viewsets)

    _l.info('readonly_access_policies %s' % len(readonly_access_policies))

    generate_speicifc_policies_for_viewsets()


    patch_generated_policies()

    generate_viewer_role(readonly_access_policies)
    generate_data_manager_role()
    generate_configuration_manager_role()
    generate_member_role()
