from __future__ import unicode_literals, print_function

from django.contrib.contenttypes.models import ContentType
from rest_framework.decorators import detail_route, list_route
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# from poms.users.permissions import ObjectPermissionSerializer, ObjectPermission, ObjectPermissionGuard

# class PomsModelPermissionMixin(object):
#     def initial(self, request, *args, **kwargs):
#         super(PomsModelPermissionMixin, self).initial(request, *args, **kwargs)
#         if request.user.is_authenticated:
#             request.user.current_master_user = get_master_user(request)
#             request.user.current_member = get_member(request)
#
#     def get_serializer_class(self):
#         if self.request.path.endswith('permissions/'):
#             return ObjectPermissionSerializer
#         return super(PomsModelPermissionMixin, self).get_serializer_class()
#
#     def check_manage_permission(self, request, op):
#         # group_profile = getattr(group, 'profile', None)
#         # if group_profile is None:
#         #     raise PermissionDenied()
#         # if group.pk == 6:
#         #     raise PermissionDenied()
#         pass
#
#     def _get_groups(self, ctype):
#         return GroupProfile.objects. \
#             prefetch_related('group', 'group__permissions', 'group__permissions__content_type'). \
#             filter(group__permissions__content_type=ctype).distinct()
#
#     def _perms(self, request, pk=None):
#         model = self.get_queryset().model
#         ctype = ContentType.objects.get_for_model(model)
#
#         if request.method == 'GET':
#             data = []
#
#             for profile in self._get_groups(ctype):
#                 group = profile.group
#                 data.append(ObjectPermission(
#                     group=profile,
#                     # permissions=self._globalize_perms(ctype, group.permissions.filter(content_type=ctype),
#                     #                                   is_model=True)
#                     # permissions=group.permissions.filter(content_type=ctype)
#                     permissions=[p for p in group.permissions.all() if p.content_type_id == ctype.id]
#                 ))
#
#             serializer = ObjectPermissionSerializer(data, many=True)
#             return Response(serializer.data)
#
#         elif request.method in ['POST', 'PUT']:
#             serializer = ObjectPermissionSerializer(data=request.data, context={'request': request, 'model': model})
#             serializer.is_valid(raise_exception=True)
#             op = serializer.save()
#
#             profile = op.group
#             group = profile.group
#
#             self.check_manage_permission(request, op)
#
#             # all_perms = {'%s.%s' % (ctype.app_label, p.codename) for p in get_perms_for_model(model)}
#             new_perms = {'%s.%s' % (ctype.app_label, p.codename) for p in op.permissions if
#                          p.content_type_id == ctype.pk}
#             old_perms = {'%s.%s' % (ctype.app_label, p.codename) for p in
#                          group.permissions.filter(content_type=ctype)}
#
#             # all_perms = self._globalize_perms(ctype, get_perms_for_model(model), is_model=True)
#             # new_perms = self._globalize_perms(ctype, op.permissions)
#             # new_perms = {p for p in new_perms if p in all_perms}  # filter
#             # old_perms = self._globalize_perms(ctype, op.group.permissions.filter(content_type=ctype), is_model=True)
#
#             for p in new_perms - old_perms:
#                 assign_perm(p, group)
#             for p in old_perms - new_perms:
#                 remove_perm(p, group)
#
#             # op.permissions = new_perms
#
#             serializer = ObjectPermissionSerializer(instance=op, context={'request': request, 'model': model})
#             return Response(serializer.data)
#
#         return Response([])
#
#     @list_route(methods=['get', 'post'], url_path='permissions',
#                 permission_classes=[IsAuthenticated, ObjectPermissionGuard])
#     def list_perms(self, request, pk=None):
#         return self._perms(request, pk)
#
#
# class PomsObjectPermissionMixin(PomsModelPermissionMixin):
#     def _perms(self, request, pk=None):
#         model = self.get_queryset().model
#         ctype = ContentType.objects.get_for_model(model)
#         instance = self.get_object() if pk else None
#
#         if instance:
#             if request.method == 'GET':
#                 data = []
#
#                 pm = {p.codename: p for p in get_perms_for_model(model)}
#
#                 for profile in self._get_groups(ctype):
#                     group = profile.group
#                     perms = get_group_perms(group, instance)
#                     data.append(ObjectPermission(
#                         group=profile,
#                         # permissions=self._globalize_perms(ctype, perms)
#                         permissions=[pm[codename] for codename in perms if codename in pm]
#                     ))
#
#                 serializer = ObjectPermissionSerializer(data, many=True)
#                 return Response(serializer.data)
#
#             elif request.method in ['POST', 'PUT']:
#                 serializer = ObjectPermissionSerializer(data=request.data, context={'request': request})
#                 serializer.is_valid(raise_exception=True)
#                 op = serializer.save()
#
#                 self.check_manage_permission(request, op)
#
#                 profile = op.group
#                 group = profile.group
#
#                 new_perms = {'%s.%s' % (ctype.app_label, p.codename) for p in op.permissions
#                              if p.content_type_id == ctype.pk}
#                 old_perms = {'%s.%s' % (ctype.app_label, codename) for codename in get_group_perms(group, instance)}
#                 print(new_perms)
#                 print(old_perms)
#
#                 # all_perms = self._globalize_perms(ctype, get_perms_for_model(model), is_model=True)
#                 # new_perms = self._globalize_perms(ctype, op.permissions)
#                 # new_perms = {p for p in new_perms if p in all_perms}  # filter
#                 # old_perms = self._globalize_perms(ctype, get_group_perms(op.group, instance))
#
#                 for p in set(new_perms) - set(old_perms):
#                     assign_perm(p, group, instance)
#                 for p in set(old_perms) - set(new_perms):
#                     remove_perm(p, group, instance)
#
#                 # op.permissions = new_perms
#
#                 serializer = ObjectPermissionSerializer(instance=op, context={'request': request})
#                 return Response(serializer.data)
#         else:
#             return super(PomsObjectPermissionMixin, self)._perms(request, pk)
#
#     @detail_route(methods=['get', 'post'], url_path='permissions',
#                   permission_classes=[IsAuthenticated, ObjectPermissionGuard])
#     def object_perms(self, request, pk=None):
#         return self._perms(request, pk)
