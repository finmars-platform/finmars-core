from __future__ import unicode_literals

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import ugettext_lazy

from poms.users.models import Member, Group


# class AbstractObjectPermission(models.Model):
#     # in child object: content_object -> actual object
#     permission = models.ForeignKey(Permission, verbose_name=ugettext_lazy('permission'))
#
#     class Meta:
#         abstract = True
#
#
# class AbstractUserObjectPermission(AbstractObjectPermission):
#     # in child object: content_object -> actual object
#     member = models.ForeignKey(Member, verbose_name=ugettext_lazy('member'))
#
#     class Meta(AbstractObjectPermission.Meta):
#         abstract = True
#         unique_together = [
#             ['content_object', 'member', 'permission']
#         ]
#         verbose_name = ugettext_lazy('user permission')
#         verbose_name_plural = ugettext_lazy('user permissions')
#
#     def __str__(self):
#         return 'Member "%s" %s "%s"' % (self.member, self.permission.name.lower(), self.content_object)
#
#
# class AbstractGroupObjectPermission(AbstractObjectPermission):
#     # in child object: content_object -> actual object
#     group = models.ForeignKey(Group, verbose_name=ugettext_lazy('group'))
#
#     class Meta(AbstractObjectPermission.Meta):
#         abstract = True
#         unique_together = [
#             ['content_object', 'group', 'permission']
#         ]
#         verbose_name = ugettext_lazy('group permission')
#         verbose_name_plural = ugettext_lazy('group permissions')
#
#     def __str__(self):
#         return 'Group "%s" %s "%s"' % (self.group, self.permission.name.lower(), self.content_object)


class GenericObjectPermission(models.Model):
    group = models.ForeignKey(Group, null=True, blank=True, verbose_name=ugettext_lazy('group'), on_delete=models.CASCADE)
    member = models.ForeignKey(Member, null=True, blank=True, verbose_name=ugettext_lazy('member'), on_delete=models.CASCADE)

    content_type = models.ForeignKey(ContentType, verbose_name=ugettext_lazy('content type'), on_delete=models.CASCADE)
    object_id = models.BigIntegerField(verbose_name=ugettext_lazy('object id'))
    content_object = GenericForeignKey('content_type', 'object_id')

    permission = models.ForeignKey(Permission, verbose_name=ugettext_lazy('permission'), on_delete=models.CASCADE)

    class Meta:
        verbose_name = ugettext_lazy('object permission')
        verbose_name_plural = ugettext_lazy('object permissions')
        index_together = [
            ['content_type', 'object_id'],
            ['content_type', 'group']
        ]

    def __str__(self):
        if self.group:
            return 'Group "%s" %s "%s"' % (self.group, self.permission.name.lower(), self.content_object)
        if self.member:
            return 'Member "%s" %s "%s"' % (self.member, self.permission.name.lower(), self.content_object)
        return ''
