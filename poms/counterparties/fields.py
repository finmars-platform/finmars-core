from poms.common.fields import UserCodeOrPrimaryKeyRelatedField
from poms.counterparties.models import (
    Counterparty,
    CounterpartyGroup,
    Responsible,
    ResponsibleGroup,
)
from poms.users.filters import OwnerByMasterUserFilter


class CounterpartyGroupDefault(object):
    requires_context = True

    def set_context(self, serializer_field):
        from poms_app import settings

        from poms.users.models import MasterUser

        self._master_user = MasterUser.objects.get(base_api_url=settings.BASE_API_URL)

    def __call__(self, serializer_field):
        from poms.users.models import EcosystemDefault

        self.set_context(serializer_field)
        self.ecosystem_defaults = EcosystemDefault.objects.get(
            master_user=self._master_user
        )

        return self.ecosystem_defaults.counterparty_group


class CounterpartyGroupField(UserCodeOrPrimaryKeyRelatedField):
    queryset = CounterpartyGroup.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]


class CounterpartyDefault(object):
    requires_context = True

    def set_context(self, serializer_field):
        from poms_app import settings

        from poms.users.models import MasterUser

        self._master_user = MasterUser.objects.get(base_api_url=settings.BASE_API_URL)

    def __call__(self, serializer_field):
        self.set_context(serializer_field)
        from poms.users.models import EcosystemDefault

        self.ecosystem_defaults = EcosystemDefault.objects.get(
            master_user=self._master_user
        )

        return self.ecosystem_defaults.counterparty


class CounterpartyField(UserCodeOrPrimaryKeyRelatedField):
    queryset = Counterparty.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]


class ResponsibleGroupDefault(object):
    requires_context = True

    def set_context(self, serializer_field):
        from poms_app import settings

        from poms.users.models import MasterUser

        self._master_user = MasterUser.objects.get(base_api_url=settings.BASE_API_URL)

    def __call__(self, serializer_field):
        self.set_context(serializer_field)
        from poms.users.models import EcosystemDefault

        self.ecosystem_defaults = EcosystemDefault.objects.get(
            master_user=self._master_user
        )

        return self.ecosystem_defaults.responsible_group


class ResponsibleGroupField(UserCodeOrPrimaryKeyRelatedField):
    queryset = ResponsibleGroup.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]


class ResponsibleDefault(object):
    requires_context = True

    def set_context(self, serializer_field):
        from poms_app import settings

        from poms.users.models import MasterUser

        self._master_user = MasterUser.objects.get(base_api_url=settings.BASE_API_URL)

    def __call__(self, serializer_field):
        from poms.users.models import EcosystemDefault

        self.set_context(serializer_field)
        self.ecosystem_defaults = EcosystemDefault.objects.get(
            master_user=self._master_user
        )

        return self.ecosystem_defaults.responsible


class ResponsibleField(UserCodeOrPrimaryKeyRelatedField):
    queryset = Responsible.objects
    filter_backends = [
        OwnerByMasterUserFilter,
    ]
