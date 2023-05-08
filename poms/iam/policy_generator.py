from poms.iam.models import AccessPolicy, Role
from poms.iam.utils import capitalize_first_letter
from poms_app import settings
from dataclasses import asdict

from poms.common.mixins import ListLightModelMixin, ListEvModelMixin
from poms_app import settings

from rest_framework import viewsets
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin, DestroyModelMixin, ListModelMixin, \
    RetrieveModelMixin
import inspect
from django.apps import apps

import logging
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

        user_code = 'com.finmars.local:' + service_name + ':' + viewset_name.lower() + '-readonly'
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

    user_code = 'com.finmars.local:' + service_name + ':balancereport'
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
                    "com.finmars.local:balancereport:create",
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

    user_code = 'com.finmars.local:' + service_name + ':plreport'
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
                    "com.finmars.local:plreport:create",
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

    user_code = 'com.finmars.local:' + service_name + ':transactionreport'
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
                    "com.finmars.local:transactionreport:create",
                ],
                "Resource": "*"
            }
        ]
    }

    access_policy.policy = access_policy_json
    access_policy.save()

    return access_policy


def generate_speicifc_policies_for_viewsets():

    access_policies = []

    balance_report_access_policy = generate_balance_report_access_policy()
    pl_report_access_policy = generate_pl_report_access_policy()
    transaction_report_access_policy = generate_transaction_report_access_policy()


    access_policies.append(balance_report_access_policy)
    access_policies.append(pl_report_access_policy)
    access_policies.append(transaction_report_access_policy)

    return access_policies


def generate_viewer_role(readonly_access_policies):
    try:
        role = Role.objects.get(user_code='com.finmars.local:viewer')
    except Exception as e:
        role = Role.objects.create(user_code='com.finmars.local:viewer', configuration_code='com.finmars.local')

    # _l.debug('generate_viewer_role.readonly_access_policies %s' % readonly_access_policies)

    role.name = 'Viewer'
    role.access_policies.set(readonly_access_policies)
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


def create_base_iam_access_policies_templates():
    viewsets = get_viewsets_from_all_apps()

    # _l.info('viewsets %s' % viewsets)
    _l.info('viewsets %s' % len(viewsets))

    generate_full_access_policies_for_viewsets(viewsets)
    readonly_access_policies = generate_readonly_access_policies_for_viewsets(viewsets)

    generate_speicifc_policies_for_viewsets()

    generate_viewer_role(readonly_access_policies)
