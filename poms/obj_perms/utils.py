from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import Prefetch, Q
from django.utils.functional import SimpleLazyObject

from poms.obj_perms.models import GenericObjectPermission


# def get_rel_model(obj, attr_name, base_cls):
#     if isinstance(obj, Model):
#         # obj = obj.__class__
#         model = obj.__class__
#     else:
#         model = obj
#     # ctype = ContentType.objects.get_for_model(obj)
#
#     fields = (f for f in obj._meta.get_fields() if (f.one_to_many or f.one_to_one) and f.auto_created)
#     for attr in fields:
#         related_model = getattr(attr, 'related_model', None)
#         if related_model and issubclass(related_model, base_cls):
#             fk = related_model._meta.get_field(attr_name)
#             # if ctype == ContentType.objects.get_for_model(fk.rel.to):
#             # if model == fk.rel.to:
#             if issubclass(fk.rel.to, model):
#                 return attr.name, related_model
#     return None, None
#
#
# def get_obj_perms_model(obj, base_cls):
#     return get_rel_model(obj, 'content_object', base_cls)
#
#
# def get_user_obj_perms_model(obj):
#     from poms.obj_perms.models import AbstractUserObjectPermission
#     return get_obj_perms_model(obj, AbstractUserObjectPermission)
#
#
# def get_group_obj_perms_model(obj):
#     from poms.obj_perms.models import AbstractGroupObjectPermission
#     return get_obj_perms_model(obj, AbstractGroupObjectPermission)


def obj_perms_filter_objects(member, perms, queryset, model_cls=None, prefetch=True):
    if member is None:
        return queryset

    if member.is_superuser:
        return queryset

    model = model_cls or queryset.model
    # user_lookup_name, user_obj_perms_model = get_user_obj_perms_model(model)
    # group_lookup_name, group_obj_perms_model = get_group_obj_perms_model(model)
    ctype = ContentType.objects.get_for_model(model)

    print('perms %s ' % perms)

    codenames = set()
    for perm in perms:
        if '.' in perm:
            app_label, codename = perm.split('.', 1)
            if app_label != ctype.app_label:
                raise ValueError('Invalid perm %s ' % perm)
        else:
            codename = perm
        codenames.add(codename)

    if codenames:
        # f = Q()
        # if user_obj_perms_model:
        #     user_obj_perms_qs = user_obj_perms_model.objects.filter(
        #         member=member,
        #         permission__content_type=ctype,
        #         permission__codename__in=codenames
        #     )
        #     f |= Q(pk__in=user_obj_perms_qs.values_list('content_object__id', flat=True))
        # if group_obj_perms_model:
        #     group_obj_perms_qs = group_obj_perms_model.objects.filter(
        #         group__in=member.groups.all(),
        #         permission__content_type=ctype,
        #         permission__codename__in=codenames
        #     )
        #     f |= Q(pk__in=group_obj_perms_qs.values_list('content_object__id', flat=True))
        # if f:
        #     queryset = queryset.filter(f)

        queryset = queryset.filter(
            pk__in=GenericObjectPermission.objects.filter(
                content_type=ctype, permission__content_type=ctype, permission__codename__in=codenames
            ).filter(
                Q(member=member) | Q(group__in=member.groups.all())
            ).values_list('object_id', flat=True)
        )
        # queryset = queryset.filter(object_permissions__permission__content_type=ctype,
        #                            object_permissions__permission__codename__in=codenames)

        if prefetch:
            queryset = obj_perms_prefetch(queryset, my=True)

        return queryset
    else:
        return queryset.none()


def obj_perms_filter_objects_for_view(member, queryset, model=None, prefetch=True):
    model = model or queryset.model
    perms = get_view_perms(model)
    return obj_perms_filter_objects(member, perms, queryset, prefetch=prefetch)


def obj_perms_filter_object_list(member, perms, objs):
    if member.is_superuser or not objs:
        return objs
    if not isinstance(perms, set):
        perms = set(perms)
    return [obj for obj in objs if has_perms(member, obj, perms)]


def obj_perms_filter_object_list_for_view(member, objs, model=None):
    if not objs:
        return objs
    model = model or objs[0]
    perms = get_view_perms(model)
    return obj_perms_filter_object_list(member, perms, objs)


# def get_granted_permissions(member, obj):
#     if member.is_superuser:
#         return get_all_perms(obj)
#     model = obj
#     user_lookup_name, user_obj_perms_model = get_user_obj_perms_model(model)
#     group_lookup_name, group_obj_perms_model = get_group_obj_perms_model(model)
#
#     obj_perms = set()
#     if user_lookup_name:
#         user_obj_perms = getattr(obj, user_lookup_name)
#         for po in user_obj_perms.all():
#             if po.member_id == member.id:
#                 obj_perms.add(po.permission.codename)
#
#     if group_lookup_name:
#         groups_id = [g.id for g in member.groups.all()]
#         group_obj_perms = getattr(obj, group_lookup_name)
#         for po in group_obj_perms.all():
#             if po.group_id in groups_id:
#                 obj_perms.add(po.permission.codename)
#
#     return list(obj_perms)


def get_granted_permissions(member, obj):
    if member.is_superuser:
        return get_all_perms(obj)
    if hasattr(obj, 'object_permissions'):
        # already prefetch all in obj_perms_prefetch_one
        perms_qs = obj.object_permissions.all()
    else:
        perms_qs = GenericObjectPermission.objects.select_related('permission').filter(
            content_type=ContentType.objects.get_for_model(obj), object_id=obj.id)
    obj_perms = set()
    groups_id = {g.id for g in member.groups.all()}
    for op in perms_qs:
        if op.member_id == member.id:
            obj_perms.add(op.permission.codename)
        if op.group_id in groups_id:
            obj_perms.add(op.permission.codename)
    return list(obj_perms)


# def assign_perms(obj, members=None, groups=None, perms=None):
#     members = members or []
#     groups = groups or []
#     user_perms = []
#     group_perms = []
#     for p in perms:
#         for m in members:
#             user_perms.append({'member': m, 'permission': p})
#         for g in groups:
#             group_perms.append({'group': g, 'permission': p})
#     assign_perms2(obj, user_perms=user_perms, group_perms=group_perms)


# def assign_perms2(obj, user_perms=None, group_perms=None):
#     ctype = ContentType.objects.get_for_model(obj)
#     perms_map = SimpleLazyObject(lambda: {p.codename: p for p in Permission.objects.filter(content_type=ctype)})
#
#     def rebuild_perms(src):
#         dst = []
#         for p in src:
#             p = p.copy()
#             if isinstance(p['permission'], str):
#                 p['permission'] = perms_map[p['permission']]
#             dst.append(p)
#         return dst
#
#     user_lookup_name, user_obj_perms_model = get_user_obj_perms_model(obj)
#     group_lookup_name, group_obj_perms_model = get_group_obj_perms_model(obj)
#
#     if user_perms is not None and user_obj_perms_model:
#         user_perms = rebuild_perms(user_perms)
#
#         member_map = {m['member'].id: m['member'] for m in user_perms}
#         perms_map = {m['permission'].codename: m['permission'] for m in user_perms}
#         pcur = {(p.member_id, p.permission.codename) for p in getattr(obj, user_lookup_name).all()}
#         pnew = {(p['member'].id, p['permission'].codename) for p in user_perms}
#
#         pdelete = pcur - pnew
#         if pdelete:
#             for member_id, permission in pdelete:
#                 getattr(obj, user_lookup_name).filter(member=member_id, permission__codename=permission).delete()
#
#         padd = pnew - pcur
#         if padd:
#             for member_id, permission in padd:
#                 user_obj_perms_model(content_object=obj,
#                                      member=member_map[member_id],
#                                      permission=perms_map[permission]).save()
#
#     if group_perms is not None and group_lookup_name:
#         group_perms = rebuild_perms(group_perms)
#
#         group_map = {m['group'].id: m['group'] for m in group_perms}
#         perms_map = {m['permission'].codename: m['permission'] for m in group_perms}
#         pcur = {(p.group_id, p.permission.codename) for p in getattr(obj, group_lookup_name).all()}
#         pnew = {(p['group'].id, p['permission'].codename) for p in group_perms}
#
#         pdelete = pcur - pnew
#         if pdelete:
#             for group_id, permission in pdelete:
#                 getattr(obj, group_lookup_name).filter(group=group_id, permission__codename=permission).delete()
#
#         padd = pnew - pcur
#         if padd:
#             for group_id, permission in padd:
#                 group_obj_perms_model(content_object=obj,
#                                       group=group_map[group_id],
#                                       permission=perms_map[permission]).save()


def assign_perms3(obj, perms=None):
    # GenericObjectPermission.objects.filter(content_object=obj).delete()
    # obj.object_permissions2.delete()

    ctype = ContentType.objects.get_for_model(obj)
    perms_map = SimpleLazyObject(lambda: {p.codename: p for p in Permission.objects.filter(content_type=ctype)})

    for op in perms:
        p = op['permission']
        if isinstance(p, str):
            op['permission'] = perms_map[p]

    perms_qs = GenericObjectPermission.objects.filter(
        content_type=ContentType.objects.get_for_model(obj), object_id=obj.id)
    existed = {(a.object_id, a.group_id, a.member_id, a.permission_id): a for a in perms_qs}
    processed = []
    for p in perms:
        group = p.get('group', None)
        member = p.get('member', None)
        permission = p['permission']
        op = existed.get((obj.id, getattr(group, 'id', None), getattr(member, 'id', None), permission.id), None)
        if op:
            processed.append(op.id)
        else:
            op = GenericObjectPermission()
            op.content_object = obj
            op.group = group
            op.member = member
            op.permission = permission
            op.save()
            processed.append(op.id)
    perms_qs.exclude(pk__in=processed).delete()


def get_perms_codename(model, actions):
    params = {
        'action': None,
        'app_label': model._meta.app_label,
        'model_name': model._meta.model_name
    }
    ret = []
    for action in actions:
        params['action'] = action
        ret.append('%(action)s_%(model_name)s' % params)
    return ret


def get_view_perms(model):
    return get_perms_codename(model, ['view', 'change', 'manage'])


def get_change_perms(model):
    return get_perms_codename(model, ['change', 'manage'])


def get_delete_perms(model):
    return get_perms_codename(model, ['change', 'manage'])


def get_manage_perms(model):
    return get_perms_codename(model, ['manage'])


def get_all_perms(model):
    return get_perms_codename(model, ['view', 'change', 'manage'])


def has_perms(member, obj, perms):
    if member.is_superuser:
        return True
    obj_perms = get_granted_permissions(member, obj)
    return bool(set(perms) & set(obj_perms))


def has_perm(member, obj, perm):
    if member.is_superuser:
        return True
    obj_perms = get_granted_permissions(member, obj)
    return perm in obj_perms


def has_any_perms(member, obj):
    if member.is_superuser:
        return True
    perms = get_all_perms(obj)
    return has_perms(member, obj, perms)


def has_view_perms(member, obj):
    if member.is_superuser:
        return True
    perms = get_view_perms(obj)
    return has_perms(member, obj, perms)


def has_change_perms(member, obj):
    if member.is_superuser:
        return True
    perms = get_change_perms(obj)
    return has_perms(member, obj, perms)


def has_delete_perms(member, obj):
    if member.is_superuser:
        return True
    perms = get_delete_perms(obj)
    return has_perms(member, obj, perms)


def has_manage_perm(member, obj):
    if member.is_superuser:
        return True
    perms = get_manage_perms(obj)
    return has_perms(member, obj, perms)


_perms_lookups = [
    # 'user_object_permissions',
    # 'user_object_permissions__member',
    # 'user_object_permissions__permission',
    # 'user_object_permissions__permission__content_type',
    # 'group_object_permissions',
    # 'group_object_permissions__group',
    # 'group_object_permissions__permission',
    # 'group_object_permissions__permission__content_type',
    'object_permissions',
    'object_permissions__group',
    'object_permissions__member',
    'object_permissions__permission',
    'object_permissions__permission__content_type',
]


def obj_perms_prefetch_one(lookup, model):
    # user_lookup_name, user_obj_perms_model = get_user_obj_perms_model(model)
    # group_lookup_name, group_obj_perms_model = get_group_obj_perms_model(model)
    if lookup:
        # user_object_permissions = '%s__user_object_permissions' % lookup
        # group_object_permissions = '%s__group_object_permissions' % lookup
        object_permissions = '%s__object_permissions' % lookup
    else:
        # user_object_permissions = 'user_object_permissions'
        # group_object_permissions = 'group_object_permissions'
        object_permissions = 'object_permissions'
    return [
        # Prefetch(user_object_permissions, queryset=user_obj_perms_model.objects.select_related(
        #     'member', 'permission', 'permission__content_type')),
        # Prefetch(group_object_permissions, queryset=group_obj_perms_model.objects.select_related(
        #     'group', 'permission', 'permission__content_type')),

        Prefetch(object_permissions, queryset=GenericObjectPermission.objects.select_related(
            'group', 'member', 'permission', 'permission__content_type')),
    ]


def obj_perms_prefetch(queryset, my=True, lookups_related=None):
    lookups = []
    if my:
        # lookups += _perms_lookups
        lookups += obj_perms_prefetch_one(None, queryset.model)

        # user_lookup_name, user_obj_perms_model = get_user_obj_perms_model(queryset.model)
        # group_lookup_name, group_obj_perms_model = get_group_obj_perms_model(queryset.model)
        # lookups += [
        #     Prefetch("user_object_permissions",
        #              queryset=user_obj_perms_model.objects.select_related('member', 'permission',
        #                                                                   'permission__content_type')),
        #     Prefetch("group_object_permissions",
        #              queryset=group_obj_perms_model.objects.select_related('group', 'permission',
        #                                                                    'permission__content_type')),
        # ]
    if lookups_related:
        for name in lookups_related:
            if isinstance(name, (tuple, list)):
                lookup, model = name
                lookups += obj_perms_prefetch_one(lookup, model)
            else:
                for lookup in _perms_lookups:
                    lookups.append('%s__%s' % (name, lookup))
                    # lookups.append(Prefetch('%s__%s' % (name, lookup)))
    return queryset.prefetch_related(*lookups)


def get_permissions_prefetch_lookups(*lookups):
    if lookups:
        ret = []
        for name in lookups:
            lookup, model = name
            ret += obj_perms_prefetch_one(lookup, model)
        return ret
    return []
