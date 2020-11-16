from __future__ import unicode_literals

import logging

from django.contrib.auth import user_logged_in, user_login_failed, get_user_model
from django.dispatch import receiver

from poms import notifications
from poms.audit.models import AuthLogEntry
from poms.common.middleware import get_request

_l = logging.getLogger('poms.audit')


@receiver(user_logged_in, dispatch_uid='audit_user_logged_in')
def audit_user_logged_in(request=None, user=None, **kwargs):
    AuthLogEntry.objects.create(user=user, is_success=True,
                                user_agent=getattr(request, 'user_agent', None),
                                user_ip=getattr(request, 'user_ip', None))
    notifications.send([user], actor=user, verb='logged in')


@receiver(user_login_failed, dispatch_uid='audit_user_login_failed')
def audit_user_login_failed(credentials=None, **kwargs):
    if credentials is None:
        return
    request = get_request()
    username = credentials.get('username', None)
    if username is None:
        return
    user_model = get_user_model()
    try:
        user = user_model.objects.get(username=username)
    except user_model.DoesNotExist:
        return
    AuthLogEntry.objects.create(user=user,
                                is_success=False,
                                user_agent=getattr(request, 'user_agent', None),
                                user_ip=getattr(request, 'user_ip', None))
    # notifications.send([user], actor=user, verb='login failed')

#
# def is_track_enabled(obj):
#     ret = history.is_active() and reversion.is_registered(obj)
#     # ret = reversion.is_registered(obj)
#     # _l.debug('track_enabled: %s -> %s', repr(obj), ret)
#     return ret
#
#
# def fields_to_set(fields):
#     ret = set()
#     for k, v in six.iteritems(fields):
#         if isinstance(v, list):
#             ret.add((k, tuple(v)))
#         else:
#             ret.add((k, v))
#     return ret
#
#
# def _to_json_value(value):
#     if type(value) in six.string_types:
#         return value
#     elif type(value) in six.integer_types:
#         return value
#     elif type(value) in [list, tuple, dict]:
#         return value
#     return force_text(value)
#
#
# @receiver(post_init, dispatch_uid='tracker_on_init')
# def tracker_post_init(sender, instance=None, **kwargs):
#     if not is_track_enabled(instance):
#         return
#     if instance.pk:
#         instance._tracker_data = django_serializers.serialize('python', [instance])[0]
#     else:
#         instance._tracker_data = {'pk': None, 'fields': {}}
#
#
# @receiver(post_save, dispatch_uid='tracker_on_save')
# def tracker_post_save(sender, instance=None, created=None, **kwargs):
#     if not is_track_enabled(instance):
#         return
#     if not hasattr(instance, '_tracker_data'):
#         return
#     _l.debug('post_save: sender=%s, instance=%s, created=%s, kwargs=%s',
#              sender, instance, created, kwargs)
#
#     if created:
#         history.object_added(instance)
#     else:
#         c = django_serializers.serialize('python', [instance])[0]
#         i = instance._tracker_data
#
#         if c['pk'] == i['pk']:
#             cfields = fields_to_set(c['fields'])
#             ifileds = fields_to_set(i['fields'])
#             changed = ifileds - cfields
#             if changed:
#                 fields = []
#                 for attr, v in changed:
#                     f = instance._meta.get_field(attr)
#                     old_value_id = i['fields'].get(attr, None)
#                     new_value_id = c['fields'].get(attr, None)
#                     old_value = None
#                     new_value = None
#
#                     if f.one_to_one or f.one_to_many:
#                         ct = ContentType.objects.get_for_model(f.related_model)
#                         if old_value_id:
#                             obj = ct.get_object_for_this_type(pk=old_value_id)
#                             old_value = {
#                                 'id': obj.id,
#                                 'object_repr': force_text(obj),
#                             }
#                         if new_value_id:
#                             obj = ct.get_object_for_this_type(pk=new_value_id)
#                             new_value = {
#                                 'id': obj.id,
#                                 'object_repr': force_text(obj),
#                             }
#                     else:
#                         old_value = old_value_id
#                         new_value = new_value_id
#                     # elif f.many_to_many:
#                     #     # ct = ContentType.objects.get_for_model(f.related_model)
#                     #     # old_value = [force_text(ct.get_object_for_this_type(pk=rpk)) for rpk in old_value]
#                     #     # new_value = [force_text(ct.get_object_for_this_type(pk=rpk)) for rpk in new_value]
#                     #     pass
#                     old_value = _to_json_value(old_value)
#                     new_value = _to_json_value(new_value)
#                     fields.append({
#                         'name': six.text_type(f.name),
#                         'verbose_name': six.text_type(f.verbose_name),
#                         'old_value': old_value,
#                         'new_value': new_value,
#                     })
#                 # fields.sort()
#                 history.object_changed(instance, fields)
#
#
# @receiver(m2m_changed, dispatch_uid='tracker_on_m2m_changed')
# def tracker_on_m2m_changed(sender, instance=None, action=None, reverse=None, model=None, pk_set=None, **kwargs):
#     if not is_track_enabled(instance):
#         return
#     if not hasattr(instance, '_tracker_data'):
#         return
#
#     _l.debug('m2m_changed.%s: sender=%s, instance=%s, reverse=%s, model=%s, pk_set=%s, kwargs=%s',
#              action, sender, instance, reverse, model, pk_set, kwargs)
#
#     if action not in ['pre_remove', 'pre_add']:
#         return
#
#     attr = None
#     attr_ctype = ContentType.objects.get_for_model(model)
#     for f in instance._meta.get_fields():
#         if f.many_to_many:
#             if f.auto_created:
#                 if f.through == sender:
#                     # f = ft
#                     attr = f.related_name
#                     break
#             else:
#                 if f.rel.through == sender:
#                     # f = ft
#                     attr = f.name
#                     break
#     if attr is None:
#         return
#
#     if attr not in instance._tracker_data:
#         instance._tracker_data[attr] = [o.pk for o in getattr(instance, attr).all()]
#     _l.debug('\t %s - %s -> %s', attr, attr_ctype, instance._tracker_data[attr])
#
#     field_data = history.object_changed_get_field(instance, attr)
#     if field_data is None:
#         field_data = {
#             'name': six.text_type(attr),
#             'verbose_name': six.text_type(model._meta.verbose_name_plural),
#         }
#
#         value = []
#         for pk in instance._tracker_data[attr]:
#             obj = attr_ctype.get_object_for_this_type(pk=pk)
#             value.append({
#                 'id': obj.id,
#                 'object_repr': force_text(obj),
#             })
#
#         field_data['old_value'] = value
#         field_data['new_value'] = value
#
#     new_value = set(x['id'] for x in field_data['new_value'])
#     if action == 'pre_remove':
#         new_value = new_value.difference(pk_set)
#     elif action == 'pre_add':
#         new_value = new_value.union(pk_set)
#
#     value = []
#     for pk in new_value:
#         obj = attr_ctype.get_object_for_this_type(pk=pk)
#         value.append({
#             'id': obj.id,
#             'object_repr': force_text(obj),
#         })
#     field_data['new_value'] = value
#
#     # if old_value:
#     #     obj = ct.get_object_for_this_type(pk=old_value_id)
#     #     old_value = {
#     #         'object_id': obj.id,
#     #         'object_repr': force_text(obj),
#     #     }
#     # if new_value_id:
#     #     obj = ct.get_object_for_this_type(pk=new_value_id)
#     #     new_value = {
#     #         'object_id': obj.id,
#     #         'object_repr': force_text(obj),
#     #     }
#     history.object_changed_update_field(instance, field_data)
#
#     _l.debug('\t %s: %s -> %s', attr, field_data['old_value'], field_data['new_value'])
#
#     pass
#
#
# @receiver(post_delete, dispatch_uid='tracker_on_delete')
# def tracker_post_delete(sender, instance=None, **kwargs):
#     if not is_track_enabled(instance):
#         return
#     if not hasattr(instance, '_tracker_data'):
#         return
#     _l.debug('post_delete: sender=%s, instance=%s, kwargs=%s',
#              sender, instance, kwargs)
#     history.object_deleted(instance)
