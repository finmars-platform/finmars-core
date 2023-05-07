import logging

from poms_app import settings

_l = logging.getLogger('poms.iam')
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.mixins import CreateModelMixin, UpdateModelMixin, DestroyModelMixin, ListModelMixin, \
    RetrieveModelMixin
import inspect
from django.apps import apps
from itertools import chain

'''
    parse_resource_into_object

    converts:
        frn:finmars:authorizer:eu-central:client00004:authorizer.spacebackup:space00000
    to
        {
         "type": "frn",
         "service": "authorizer
         ...
         "user_code": "space00000"
        }

    '''
from poms.iam.models import AccessPolicy


def parse_resource_into_object(resource):
    result = {}

    pieces = resource.split(':', 3)

    result['type'] = pieces[0].lower()
    result['service'] = pieces[1].lower()
    result['content_type'] = pieces[2].lower()
    result['user_code'] = pieces[3].lower()

    return result


'''
parse_resource_attribute

    converts list of
    
    "frn:finmars:authorizer:authorizer.spacebackup:space00000",
    "frn:finmars:authorizer:authorizer.spacebackup:space00000"
    
    list of objects
    
    [
        {
            "type": "frn",
            ...,
            "user_code": "space00000"
        },
        {
            "type": "frn",
            ...,
            "user_code": "space00001"
        }
    ]

'''


def parse_resource_attribute(resources):
    result = []

    for resource in resources:
        result.append(parse_resource_into_object(resource))

    return result


def get_statements(member):
    # AccessPolicies directly assigned to the member
    member_policies = member.access_policies.all()

    # AccessPolicies assigned to the member through roles
    role_policies = AccessPolicy.objects.filter(roles__members=member).distinct()

    # AccessPolicies assigned to the member through groups
    group_policies = AccessPolicy.objects.filter(groups__members=member).distinct()

    # Combine all AccessPolicies
    all_policies = set(chain(member_policies, role_policies, group_policies))

    statements = []

    for item in all_policies:

        # _l.info('item.policy %s' % item.policy)

        if isinstance(item.policy, dict):
            statements.append(item.policy)
        else:
            statements = statements + item.policy

    _l.info('get_policy_statements.statements %s' % statements)

    return statements


def filter_queryset_with_access_policies(user, queryset):
    if user.is_superuser:
        return queryset

    # _l.info("filter_queryset_with_access_policies here")

    if user.member.is_admin:
        return queryset

    statements = get_statements(user)

    # _l.info('ObjectPermissionBackend.filter_queryset.statements %s' % statements)

    '''
    Important clause
    We will not grant access to objects if Access Policy is not configured
    '''
    if not len(statements):
        return []

    app_label = queryset.model._meta.app_label
    model_name = queryset.model._meta.model_name

    content_type_key = app_label + '.' + model_name

    # _l.info('ObjectPermissionBackend.filter_queryset.app_label %s' % app_label)
    # _l.info('ObjectPermissionBackend.filter_queryset.model_name %s' % model_name)

    q = Q()

    '''
    TODO improve logic to handle statements
    for now I only parse {"effect": "allow"}
    and go through the resources and do basic icontains lookup
    
    Its enough for Space Backup Permissions, but in future this method requires updates
    
    '''
    for statement in statements:

        if statement['effect'] == 'allow':

            if statement['resource']:

                resources = parse_resource_attribute(statement['resource'])

                # _l.info('resources %s' % resources)

                for resource in resources:

                    if content_type_key == resource['content_type']:

                        val = resource['user_code']

                        '''
                        * means that we have pattern e.g.
                        
                        "frn:finmars:portfolios.portfolio:portfolio*"
                        
                        it would find following objects
                        
                        "portfolio_1"
                        "portfolio_2"
                        
                        '''
                        if '*' in val:
                            val = val.split('*')[0]

                        q = q | Q(**{'user_code__icontains': val})

    # _l.info('q %s' % q)

    '''
    Another Important clause
    If somehow Access Statements above cause not effect
    We also will not grant access to objects
    '''
    if not len(q):
        return []

    # _l.info('ObjectPermissionBackend.filter_queryset before access filter: %s' % queryset.count())

    result = queryset.filter(q)

    return result


'''
 action_statement_into_object

    converts action
    
    "finmars:portfolio:list"
   
    to object
    
    {
            "service": "finmars",
            "viewset": "portfolio",
            "action": "list"
        },

'''


def action_statement_into_object(action):
    pieces = action.split(':')

    result = {
        'service': pieces[0].lower(),
        'viewset': pieces[1].lower(),
        'action': pieces[2].lower(),
    }

    return result

def capitalize_first_letter(string):
    if len(string) > 0:
        return string[0].upper() + string[1:]
    else:
        return string

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

        if len(actions):
            access_policy_json = {
                "Version": "2023-01-01",
                "Statement": [
                    {
                        "Effect": "Allow",
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

        if actions:
            access_policy_json = {
                "Version": "2023-01-01",
                "Statement": [
                    {
                        "Effect": "Allow",
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
    generate_readonly_access_policies_for_viewsets(viewsets)
