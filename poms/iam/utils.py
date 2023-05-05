import logging

_l = logging.getLogger('poms.iam')
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q

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
from poms.iam.models import MemberAccessPolicy, RoleAccessPolicy, GroupAccessPolicy


def parse_resource_into_object(resource):
    result = {}

    pieces = resource.split(':')

    result['type'] = pieces[0].lower()
    result['partition'] = pieces[1].lower()
    result['service'] = pieces[2].lower()
    result['region'] = pieces[3].lower()
    result['client_code'] = pieces[4].lower()
    result['content_type'] = pieces[5].lower()
    result['user_code'] = pieces[6]  # TODO user_code also to lower?

    return result


'''
parse_resource_attribute

    converts list of
    
    "frn:finmars:authorizer:eu-central:client00004:authorizer.spacebackup:space00000",
    "frn:finmars:authorizer:eu-central:client00004:authorizer.spacebackup:space00000"
    
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

    '''Getting UserAccessPolicies attached to User'''
    member_access_policies = MemberAccessPolicy.objects.filter(member=member)

    member_roles = member.iam_roles.all()
    '''Getting AccessPolicies directly attached to Role that Member assigned to'''
    direct_roles_access_policies = RoleAccessPolicy.objects.filter(role__in=member_roles)

    '''Getting AccessPolicies attached to Groups that Member is member of'''
    groups_access_policies = GroupAccessPolicy.objects.filter(group__in=member.iam_groups.all())

    '''Getting AccessPolicies attached to Groups that Role is member of'''
    role_in_groups = []
    for role in member_roles:
        role_in_groups = role_in_groups + role.iam_groups.all()

    role_in_group_access_policies = GroupAccessPolicy.objects.filter(group__in=role_in_groups)

    # _l.info('get_policy_statements.user %s' % user)
    # _l.info('get_policy_statements.items %s' % items)

    statements = []

    for item in member_access_policies:

        # _l.info('item.policy %s' % item.policy)

        if isinstance(item.policy, dict):
            statements.append(item.policy)
        else:
            statements = statements + item.policy

    for item in direct_roles_access_policies:

        # _l.info('item.policy %s' % item.policy)

        if isinstance(item.policy, dict):
            statements.append(item.policy)
        else:
            statements = statements + item.policy

    for item in groups_access_policies:

        # _l.info('item.policy %s' % item.policy)

        if isinstance(item.policy, dict):
            statements.append(item.policy)
        else:
            statements = statements + item.policy

    for item in role_in_group_access_policies:

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
                        
                        "frn:finmars:authorizer:::authorizer.spacebackup:space00000*"
                        
                        it would find
                        
                        "frn:finmars:authorizer:::authorizer.spacebackup:space00000_1"
                        "frn:finmars:authorizer:::authorizer.spacebackup:space00000_2"
                        etc
                        
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
    
    "authorizer:SpaceBackup:list"
   
    to object
    
    {
            "service": "authorizer",
            "viewset": "SpaceBackup",
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
