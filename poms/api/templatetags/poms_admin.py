from django import template


register = template.Library()


# @register.simple_tag(takes_context=True)
# def set_admin_master_user(context):
#     try:
#         return context['admin_master_user']
#     except KeyError:
#         from poms.common.admin import AbstractModelAdmin
#         request = context['request']
#         master_user = AbstractModelAdmin.get_active_master_user_object(request)
#         context['admin_master_user'] = master_user
#         return master_user


@register.simple_tag(takes_context=True)
def get_admin_master_user(context):
    from poms.common.admin import AbstractModelAdmin
    request = context['request']
    master_user = AbstractModelAdmin.get_active_master_user_object(request)
    return master_user

