from poms.chats.models import Thread, ThreadGroup
from poms.common.fields import PrimaryKeyRelatedFilteredField
from poms.obj_perms.fields import PrimaryKeyRelatedFilteredWithObjectPermissionField
from poms.users.filters import OwnerByMasterUserFilter


class ThreadGroupDefault(object):

    requires_context = True

    def set_context(self, serializer_field):
        request = serializer_field.context['request']
        self._master_user = request.user.master_user

    def __call__(self, serializer_field):
        self.set_context(serializer_field)
        return self._master_user.thread_group


class ThreadGroupField(PrimaryKeyRelatedFilteredField):
    queryset = ThreadGroup.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]


class ThreadField(PrimaryKeyRelatedFilteredWithObjectPermissionField):
    queryset = Thread.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]
