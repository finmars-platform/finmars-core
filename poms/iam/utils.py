import logging

from django.conf import settings
from django.core.cache import cache
from django.db.models import Q, QuerySet

from poms.iam.models import AccessPolicy, ResourceGroup
from poms.users.models import Member

_l = logging.getLogger('poms.iam')
from django.contrib.contenttypes.models import ContentType



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

'''
    parse_resource_into_object

    converts:
        frn:finmars:authorizer:authorizer:spacebackup:space00000
    to
        {
         "type": "frn",
         "service": "authorizer"
         "app_label": authorizer",
         "model": "spacebackup",
         ...
         "user_code": "space00000"
        }
'''

def parse_resource_into_object(resource):
    result = {}

    pieces = resource.split(':', 4) # split only first 4 :

    result['type'] = pieces[0].lower()
    result['service'] = pieces[1].lower()
    result['app_label'] = pieces[2].lower()
    result['model'] = pieces[3].lower()
    result['user_code'] = pieces[4].lower()

    return result


'''
parse_resource_attribute

    converts list of
    
    "frn:finmars:authorizer:authorizer:spacebackup:space00000",
    "frn:finmars:authorizer:authorizer:spacebackup:space00000"
    
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



def get_member_access_policies(member: Member) -> QuerySet:
    """
    Get all AccessPolicy objects for the member from cache or db
    Args:
        member:
    Returns:
        list of AccessPolicy objects
    """

    cache_key = f'member_access_policies_{member.id}'
    access_policies = cache.get(cache_key)

    if access_policies is None:
        access_policies = AccessPolicy.objects.filter(
            Q(members=member) |
            Q(iam_roles__members=member) |
            Q(iam_groups__members=member)
        ).distinct()

        # Cache the result for a specific duration (e.g., 5 minutes)
        cache.set(cache_key, access_policies, settings.ACCESS_POLICY_CACHE_TTL)

    return access_policies


def get_statements(member: Member) -> list:
    """
    Get all AccessPolicy statements for member/owner
    Args:
        member: policies owner
    Returns:
        list of AccessPolicy json fields (statements)
    """

    statements = []
    for item in get_member_access_policies(member):

        policy = lowercase_keys_and_values(item.policy)

        statements.extend(
            lowercase_keys_and_values(statement)
            for statement in policy['statement']
        )

    return statements


from django.db.models import Q
from django.contrib.contenttypes.models import ContentType

def filter_queryset_with_access_policies(member, queryset, view):
    if not member:
        return queryset.none()

    if member.is_admin:
        return queryset

    statements = get_statements(member)

    '''
    Important clause:
    We will not grant access to objects if Access Policy is not configured.
    '''
    if not len(statements):
        return queryset.none()

    _l.debug('filter_queryset_with_access_policies.statements %s' % len(statements))

    app_label = queryset.model._meta.app_label
    model_name = queryset.model._meta.model_name
    content_type_key = f"{app_label}.{model_name}"

    q = Q()
    view_related_statements = []
    viewset_name = view.__class__.__name__.replace('ViewSet', '').lower()

    # Filter statements related to the current view
    for statement in statements:
        if any(viewset_name == action_statement_into_object(act)["viewset"]
               for act in statement["action"]):
            view_related_statements.append(statement)

    _l.debug('filter_queryset_with_access_policies.view_related_statements %s' % len(view_related_statements))

    for statement in view_related_statements:
        if statement['effect'] == 'allow':
            resources = statement.get('resource', [])

            # Handle '*' resource (no restrictions)
            if '*' in resources:
                q |= Q(id__isnull=False)
                continue

            # Parse and expand resources if there are ResourceGroups
            expanded_resources = set()
            for resource in resources:
                if resource.startswith("frn:finmars:iam:resourcegroup:"):
                    # Handle ResourceGroup resource
                    resource_group_code = resource.split(":")[-1]
                    try:
                        resource_group = ResourceGroup.objects.get(user_code=resource_group_code)
                        assignments = resource_group.assignments.all()

                        # Add each assigned object's user_code as a resource
                        expanded_resources.update(
                            f"frn:finmars:{assignment.content_type.app_label}.{assignment.content_type.model}:{assignment.object_user_code}"
                            for assignment in assignments if assignment.object_user_code
                        )
                    except ResourceGroup.DoesNotExist:
                        _l.warning(f"ResourceGroup with user_code {resource_group_code} does not exist.")
                        continue
                else:
                    expanded_resources.add(resource)

            # Apply the filters for expanded resources
            for resource in expanded_resources:
                parsed_resource = parse_resource_into_object(resource)
                _l.info('filter_queryset_with_access_policies.parsed_resource %s' % parsed_resource)

                # Match the content type and apply filters
                if parsed_resource['content_type'] == content_type_key:
                    user_code_val = parsed_resource['user_code']
                    if '*' in user_code_val:
                        # Apply wildcard match
                        base_code = user_code_val.split('*')[0]
                        q |= Q(user_code__icontains=base_code)
                    else:
                        q |= Q(user_code=user_code_val)

    _l.debug('filter_queryset_with_access_policies.q %s' % len(q))

    '''
    Important clause:
    If Access Statements do not grant access, we deny access to objects.
    '''
    if not q:
        return queryset.none()

    _l.debug('ObjectPermissionBackend.filter_queryset before access filter: %s' % queryset.count())

    result = queryset.filter(q)
    _l.info('ObjectPermissionBackend.filter_queryset q %s' % q)

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

    try:
        pieces = action.split(':')

        result = {
            'service': pieces[0].lower(),
            'viewset': pieces[1].lower(),
            'action': pieces[2].lower(),
        }

        return result

    except Exception as e:
        raise Exception("Action is invalid %s" % action)


def capitalize_first_letter(string):
    if len(string) > 0:
        return string[0].upper() + string[1:]
    else:
        return string


def get_allowed_queryset(member, queryset):
    if not member:
        return queryset.none()

    if member.is_admin:
        return queryset

    # Get allowed resources for the member and model
    allowed_resources = get_allowed_resources(member, queryset.model, queryset)
    allowed_user_codes = []

    _l.debug('get_allowed_queryset.allowed_resources %s' % allowed_resources)

    # Extract user codes from allowed resources
    for resource in allowed_resources:
        parsed_resource = parse_resource_into_object(resource)
        allowed_user_codes.append(parsed_resource['user_code'])

    # Filter queryset based on allowed user codes
    return queryset.filter(user_code__in=allowed_user_codes)


def get_allowed_resources(member, model, queryset):
    """
    Returns a list of allowed resources for a user based on their access policies for the given model and action.
    """
    # Get all AccessPolicy objects for the user
    access_policies = get_member_access_policies(member)
    allowed_resources = []
    related_access_policies = []

    # Filter access policies related to the current model
    for access_policy in access_policies:
        policy = lowercase_keys_and_values(access_policy.policy)
        is_related = False

        for statement in policy["statement"]:
            for action in statement.get('action', []):
                action_object = action_statement_into_object(action)

                # Ensure viewset matches the model name (case-insensitive)
                if model.__name__.lower() == action_object['viewset']:
                    is_related = True

        if is_related:
            related_access_policies.append(policy)

    for policy in related_access_policies:
        for statement in policy.get("statement", []):
            if statement.get("effect") == "allow":
                resources = statement.get("resource", [])

                # Expand resources for ResourceGroups
                expanded_resources = set()
                for resource in resources:
                    if resource == "*":
                        # Allow access to all resources in queryset if wildcard is used
                        for obj in queryset:
                            expanded_resources.add(
                                f"frn:finmars:{model._meta.app_label.lower()}:{model.__name__.lower()}:{obj.user_code}"
                            )
                    elif resource.startswith("frn:finmars:iam:resourcegroup:"):
                        # Handle ResourceGroup resource
                        resource_group_code = resource.split(":")[-1]
                        try:
                            resource_group = ResourceGroup.objects.get(user_code=resource_group_code)
                            assignments = resource_group.assignments.all()

                            # Add each assigned object's user_code to the expanded resources list
                            expanded_resources.update(
                                f"frn:finmars:{assignment.content_type.app_label}:{assignment.content_type.model}:{assignment.object_user_code}"
                                for assignment in assignments if assignment.object_user_code
                            )
                        except ResourceGroup.DoesNotExist:
                            _l.warning(f"ResourceGroup with user_code {resource_group_code} does not exist.")
                            continue
                    else:
                        expanded_resources.add(resource)

                allowed_resources.extend(expanded_resources)

    return list(allowed_resources)
