from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils.translation import gettext_lazy

from poms.common.models import DataTimeStampedModel, FakeDeletableModel, NamedModel
from poms.common.wrapper_models import NamedModelAutoMapping
from poms.obj_attrs.models import GenericAttribute
from poms.users.models import MasterUser


# noinspection PyUnresolvedReferences
class CounterpartyGroup(NamedModel, FakeDeletableModel):
    master_user = models.ForeignKey(
        MasterUser,
        related_name="counterparty_groups",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy("counterparty group")
        verbose_name_plural = gettext_lazy("counterparty groups")
        permissions = [
            ("manage_counterpartygroup", "Can manage counterparty group"),
        ]

    @staticmethod
    def get_system_attrs():
        """
        Returns attributes that front end uses
        """
        return [
            {
                "key": "name",
                "name": "Name",
                "value_type": 10,
            },
            {
                "key": "short_name",
                "name": "Short name",
                "value_type": 10,
            },
            {
                "key": "notes",
                "name": "Notes",
                "value_type": 10,
            },
            {
                "key": "user_code",
                "name": "User code",
                "value_type": 10,
            },
            {
                "key": "public_name",
                "name": "Public name",
                "value_type": 10,
            },
        ]

    @property
    def is_default(self):
        return (
            self.master_user.counterparty_group_id == self.id
            if self.master_user_id
            else False
        )


# noinspection PyUnresolvedReferences
class Counterparty(NamedModelAutoMapping, FakeDeletableModel, DataTimeStampedModel):

    """
    One of Core Finmars entities, real world meaning is hold here
    information about Company, Bank, Broker, StockExchange or other entity
    who envolved into transaction e.g. Revolut
    """

    master_user = models.ForeignKey(
        MasterUser,
        related_name="counterparties",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    group = models.ForeignKey(
        CounterpartyGroup,
        related_name="counterparties",
        null=True,
        blank=True,
        verbose_name=gettext_lazy("group"),
        on_delete=models.SET_NULL,
    )
    is_valid_for_all_portfolios = models.BooleanField(
        default=True,
        verbose_name=gettext_lazy("is valid for all portfolios"),
    )
    attributes = GenericRelation(
        GenericAttribute,
        verbose_name=gettext_lazy("attributes"),
    )

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy("counterparty")
        verbose_name_plural = gettext_lazy("counterparties")
        ordering = ["user_code"]
        permissions = [
            ("manage_counterparty", "Can manage counterparty"),
        ]

    @staticmethod
    def get_system_attrs():
        """
        Returns attributes that front end uses
        """
        return [
            {
                "key": "name",
                "name": "Name",
                "value_type": 10,
            },
            {
                "key": "short_name",
                "name": "Short name",
                "value_type": 10,
            },
            {
                "key": "user_code",
                "name": "User code",
                "value_type": 10,
            },
            {
                "key": "public_name",
                "name": "Public name",
                "value_type": 10,
                "allow_null": True,
            },
            {"key": "notes", "name": "Notes", "value_type": 10},
            {
                "key": "group",
                "name": "Group",
                "value_type": "field",
                "value_entity": "counterparty-group",
                "value_content_type": "counterparties.counterpartygroup",
                "code": "user_code",
            },
            {
                "key": "portfolios",
                "name": "Portfolios",
                "value_type": "mc_field",
            },
        ]

    @property
    def is_default(self):
        return (
            self.master_user.counterparty_id == self.id
            if self.master_user_id
            else False
        )


# noinspection PyUnresolvedReferences
class ResponsibleGroup(NamedModel, FakeDeletableModel):
    master_user = models.ForeignKey(
        MasterUser,
        related_name="responsible_groups",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy("responsible group")
        verbose_name_plural = gettext_lazy("responsible groups")
        permissions = [
            ("manage_responsiblegroup", "Can manage responsible group"),
        ]

    @staticmethod
    def get_system_attrs():
        """
        Returns attributes that front end uses
        """
        return [
            {
                "key": "name",
                "name": "Name",
                "value_type": 10,
            },
            {
                "key": "short_name",
                "name": "Short name",
                "value_type": 10,
            },
            {
                "key": "notes",
                "name": "Notes",
                "value_type": 10,
            },
            {
                "key": "user_code",
                "name": "User code",
                "value_type": 10,
            },
            {
                "key": "public_name",
                "name": "Public name",
                "value_type": 10,
            },
        ]

    @property
    def is_default(self):
        return (
            self.master_user.counterparty_group_id == self.id
            if self.master_user_id
            else False
        )


# noinspection PyUnresolvedReferences
class Responsible(NamedModelAutoMapping, FakeDeletableModel, DataTimeStampedModel):
    """
    One of Core Finmars entities, real world meaning is to indicate
    who is executing/initiator of Transaction
    """

    master_user = models.ForeignKey(
        MasterUser,
        related_name="responsibles",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    group = models.ForeignKey(
        ResponsibleGroup,
        related_name="responsibles",
        null=True,
        blank=True,
        verbose_name=gettext_lazy("group"),
        on_delete=models.SET_NULL,
    )
    is_valid_for_all_portfolios = models.BooleanField(
        default=True,
        verbose_name=gettext_lazy("is valid for all portfolios"),
    )
    attributes = GenericRelation(
        GenericAttribute,
        verbose_name=gettext_lazy("attributes"),
    )

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy("responsible")
        verbose_name_plural = gettext_lazy("responsibles")
        ordering = ["user_code"]
        permissions = [
            ("manage_responsible", "Can manage responsible"),
        ]

    @staticmethod
    def get_system_attrs():
        """
        Returns attributes that front end uses
        """
        return [
            {
                "key": "name",
                "name": "Name",
                "value_type": 10,
            },
            {
                "key": "short_name",
                "name": "Short name",
                "value_type": 10,
            },
            {
                "key": "user_code",
                "name": "User code",
                "value_type": 10,
            },
            {
                "key": "public_name",
                "name": "Public name",
                "value_type": 10,
                "allow_null": True,
            },
            {
                "key": "notes",
                "name": "Notes",
                "value_type": 10,
            },
            {
                "key": "group",
                "name": "Group",
                "value_content_type": "counterparties.responsiblegroup",
                "value_entity": "responsible-group",
                "code": "user_code",
                "value_type": "field",
            },
            {
                "key": "portfolios",
                "name": "Portfolios",
                "value_content_type": "portfolios.portfolio",
                "value_entity": "portfolio",
                "code": "user_code",
                "value_type": "mc_field",
            },
        ]

    @property
    def is_default(self):
        return (
            self.master_user.responsible_id == self.id if self.master_user_id else False
        )
