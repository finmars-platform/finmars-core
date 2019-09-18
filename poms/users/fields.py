from __future__ import unicode_literals

from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.fields import CurrentUserDefault

from poms.common.fields import PrimaryKeyRelatedFilteredField
from poms.users.filters import OwnerByMasterUserFilter
from poms.users.models import Member, Group


class CurrentMasterUserDefault(object):
    def set_context(self, serializer_field):
        request = serializer_field.context['request']
        # master_user = get_master_user(request)
        master_user = request.user.master_user
        self._master_user = master_user

    def __call__(self):
        return self._master_user


class MasterUserField(serializers.HiddenField):
    def __init__(self, **kwargs):
        kwargs['default'] = CurrentMasterUserDefault()
        super(MasterUserField, self).__init__(**kwargs)


class CurrentMemberDefault(object):
    def set_context(self, serializer_field):
        request = serializer_field.context['request']
        # member = get_member(request)
        member = request.user.member
        self._member = member

    def __call__(self):
        # return self._member
        return getattr(self, '_member', None)

class HiddenMemberField(serializers.HiddenField):
    def __init__(self, **kwargs):
        kwargs['default'] = CurrentMemberDefault()
        super(HiddenMemberField, self).__init__(**kwargs)

# TODO deprecated from django 1.10
# class HiddenMemberField(serializers.PrimaryKeyRelatedField):
#     def __init__(self, **kwargs):
#         kwargs['default'] = CurrentMemberDefault()
#         # kwargs['read_only'] = True
#         kwargs.setdefault('read_only', True)
#         super(HiddenMemberField, self).__init__(**kwargs)


class HiddenUserField(serializers.PrimaryKeyRelatedField):
    def __init__(self, **kwargs):
        kwargs['default'] = CurrentUserDefault()
        # kwargs['read_only'] = True
        kwargs.setdefault('read_only', True)
        super(HiddenUserField, self).__init__(**kwargs)


class MemberField(PrimaryKeyRelatedFilteredField):
    queryset = Member.objects
    filter_backends = [OwnerByMasterUserFilter]


class UserField(PrimaryKeyRelatedFilteredField):
    queryset = User.objects.all()


class GroupField(PrimaryKeyRelatedFilteredField):
    queryset = Group.objects.all()
    filter_backends = [OwnerByMasterUserFilter]
