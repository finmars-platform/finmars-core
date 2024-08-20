from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils.translation import gettext_lazy

from poms.common.models import (
    EXPRESSION_FIELD_LENGTH,
    DataTimeStampedModel,
    FakeDeletableModel,
    NamedModel,
    ObjectStateModel,
)
from poms.configuration.models import ConfigurationModel
from poms.obj_attrs.models import GenericAttribute
from poms.users.models import MasterUser


class AccountType(
    NamedModel, FakeDeletableModel, DataTimeStampedModel, ConfigurationModel
):
    """
    Meta Entity, part of Finmars Configuration
    Mostly used for extra fragmentation of Reports
    Maybe in future would have extra logic
    """

    master_user = models.ForeignKey(
        MasterUser,
        related_name="account_types",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    show_transaction_details = models.BooleanField(
        default=False,
        verbose_name=gettext_lazy("show transaction details"),
    )
    transaction_details_expr = models.CharField(
        max_length=EXPRESSION_FIELD_LENGTH,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("transaction details expr"),
    )
    attributes = GenericRelation(
        GenericAttribute,
        verbose_name=gettext_lazy("attributes"),
    )

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy("account type")
        verbose_name_plural = gettext_lazy("account types")
        permissions = [
            ("manage_accounttype", "Can manage account type"),
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
                "allow_null": True,
            },
            {
                "key": "short_name",
                "name": "Short name",
                "value_type": 10,
                "allow_null": True,
            },
            {
                "key": "user_code",
                "name": "User code",
                "value_type": 10,
            },
            {
                "key": "configuration_code",
                "name": "Configuration code",
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
                "allow_null": True,
            },
            {
                "key": "show_transaction_details",
                "name": "Show transaction details",
                "value_type": 50,
                "allow_null": True,
            },
            {
                "key": "transaction_details_expr",
                "name": "Transaction details expr",
                "value_type": 10,
                "allow_null": True,
            },
        ]


class Account(NamedModel, FakeDeletableModel, DataTimeStampedModel, ObjectStateModel):
    """
    One of core entities - Account
    Could stand for anything that could hold money in real world e.g. Bank Accounts,
    Broker Accounts, Transit Accounts, Insurance Accounts
    """

    master_user = models.ForeignKey(
        MasterUser,
        related_name="accounts",
        verbose_name=gettext_lazy("master user"),
        on_delete=models.CASCADE,
    )
    type = models.ForeignKey(
        AccountType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=gettext_lazy("account type"),
    )
    is_valid_for_all_portfolios = models.BooleanField(
        default=True,
        verbose_name=gettext_lazy("is valid for all portfolios"),
    )
    attributes = GenericRelation(
        GenericAttribute, verbose_name=gettext_lazy("attributes")
    )

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy("account")
        verbose_name_plural = gettext_lazy("accounts")
        permissions = [
            ("manage_account", "Can manage account"),
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
            },
            {
                "key": "notes",
                "name": "Notes",
                "value_type": 10,
            },
            {
                "key": "type",
                "name": "Type",
                "value_type": "field",
                "value_content_type": "accounts.accounttype",
                "value_entity": "account-type",
                "code": "user_code",
            },
        ]

    @property
    def is_default(self):
        return self.master_user.account_id == self.id if self.master_user_id else False
