import logging


_l = logging.getLogger('poms.iam')
from django.db.models import Q

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
from poms.iam.models import AccessPolicy, Role

def add_to_list_if_not_exists(string, my_list):
    if string not in my_list:
        my_list.append(string)

def lowercase_keys_and_values(dictionary):
    new_dict = {}
    for key, value in dictionary.items():
        new_key = key.lower() if isinstance(key, str) else key
        if isinstance(value, dict):
            new_value = lowercase_keys_and_values(value)
        elif isinstance(value, str):
            new_value = value.lower()
        elif isinstance(value, list):
            new_value = [lowercase_keys_and_values(item) if isinstance(item, dict) else item for item in value]
        else:
            new_value = value

        new_dict[new_key] = new_value

    return new_dict


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
    member_policies = member.iam_access_policies.all()

    # AccessPolicies assigned to the member through roles
    role_policies = AccessPolicy.objects.filter(iam_roles__members=member).distinct()

    # AccessPolicies assigned to the member through groups
    group_policies = AccessPolicy.objects.filter(iam_groups__members=member).distinct()

    # Combine all AccessPolicies
    all_policies = set(chain(member_policies, role_policies, group_policies))

    statements = []

    for item in all_policies:

        # _l.info('item.policy %s' % item.policy)

        policy = lowercase_keys_and_values(item.policy)

        for statement in policy['statement']:
            statements.append(lowercase_keys_and_values(statement))

    # _l.debug('get_policy_statements.statements %s' % statements)

    return statements


def filter_queryset_with_access_policies(member, queryset, view):

    if member.is_admin:
        return queryset

    statements = get_statements(member)

    # _l.info('ObjectPermissionBackend.filter_queryset.statements %s' % statements)

    '''
    Important clause
    We will not grant access to objects if Access Policy is not configured
    '''
    if not len(statements):
        return queryset.none()

    _l.debug('filter_queryset_with_access_policies.statements %s' % len(statements))

    app_label = queryset.model._meta.app_label
    model_name = queryset.model._meta.model_name

    content_type_key = app_label + '.' + model_name

    # _l.info('ObjectPermissionBackend.filter_queryset.app_label %s' % app_label)
    # _l.info('ObjectPermissionBackend.filter_queryset.model_name %s' % model_name)

    q = Q()

    view_related_statements = []

    for statement in statements:

        related = False

        for action_statement in statement["action"]:

            action_object = action_statement_into_object(action_statement)

            if view.basename.lower() == action_object['viewset']:
                related = True

        if related:
            view_related_statements.append(statement)

    _l.debug('filter_queryset_with_access_policies.statements %s' % len(statements))
    _l.debug('filter_queryset_with_access_policies.view_related_statements %s' % len(view_related_statements))

    for statement in view_related_statements:

        if statement['effect'] == 'allow':

            if statement['resource']:

                if statement['resource'] == '*':

                    no_filter_q = Q(id__isnull=False)

                    q = q | no_filter_q

                else:

                    resources = parse_resource_attribute(statement['resource'])

                    _l.info('filter_queryset_with_access_policies.resources %s' % resources)

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
                            else:
                                q = q | Q(**{'user_code': val})

    _l.debug('filter_queryset_with_access_policies.q %s' % len(q))

    '''
    Another Important clause
    If somehow Access Statements above cause not effect
    We also will not grant access to objects
    '''
    if not len(q):
        return queryset.none()

    _l.debug('ObjectPermissionBackend.filter_queryset before access filter: %s' % queryset.count())

    _l.info('ObjectPermissionBackend.filter_queryset q %s' % q)

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


def get_allowed_queryset(member, queryset):
    # Retrieve the user's Access Policies and apply the filtering logic
    # You might need to adjust the logic based on your Access Policies implementation
    # TODO maybe has performance issues
    allowed_resources = get_allowed_resources(member, queryset.model, queryset)
    allowed_user_codes = []

    _l.info('get_allowed_queryset.allowed_resources %s' % allowed_resources)

    for resource in allowed_resources:

        prefix, app, content_type, user_code = resource.split(':', 3)

        allowed_user_codes.append(user_code)

    return queryset.filter(user_code__in=allowed_user_codes)


def get_allowed_resources(member,  model, queryset):
    """
    Returns a list of allowed resources for a user based on their access policies for the given action and model.

    in most cases queryset consists of one item
    Args:
        member (Member): The user whose access policies are being checked.
        action (str): The action being performed (e.g. "retrieve", "list", "create", etc.)
        model (Model): The Django model being accessed.
        queryset (QuerySet): The queryset of objects being accessed.

    Returns:
        list: A list of allowed resource strings.
    """

    # Get all AccessPolicy objects for the user
    access_policies = AccessPolicy.objects.filter(
        Q(members=member) |
        Q(iam_roles__members=member) |
        Q(iam_groups__members=member)
    ).distinct()

    allowed_resources = []

    related_access_policies = []

    for access_policy in access_policies:

        policy = lowercase_keys_and_values(access_policy.policy)

        is_related = False

        for statement in policy["statement"]:

            for action in statement.get('action', []):

                action_object = action_statement_into_object(action)

                '''
                Important, there is a possible issue, in this appoach I limit myself that
                modelName should be equal viewsetName, in most cases it should work great
                
                but for example we have viewset PortfolioAttributeType, but our model is GenericAttributeType
                It means that permission engine would not able create resource access policy for this model
                
                '''
                if model.__name__.lower() == action_object['viewset']:
                    is_related = True

        if is_related:
            related_access_policies.append(policy)

    # _l.info('related_access_policies %s' % related_access_policies)

    for policy in related_access_policies:

        for statement in policy.get("statement", []):

            if statement.get("effect") == "allow":
                resources = statement.get("resource", [])
                for resource in resources:
                    # If a wildcard is used, return all resources in the queryset
                    if resource == "*":
                        for obj in queryset:
                            allowed_resources.append(f"frn:finmars:{model._meta.app_label.lower()}.{model.__name__.lower()}:{obj.user_code}")
                    else:
                        allowed_resources.append(resource)

    return allowed_resources

