from __future__ import unicode_literals

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils.translation import gettext_lazy

from poms.common.models import NamedModel, FakeDeletableModel, DataTimeStampedModel
from poms.common.wrapper_models import NamedModelAutoMapping
from poms.obj_attrs.models import GenericAttribute
from poms.users.models import MasterUser


def _get_strategy_system_attrs(strategy_number):
    '''
    Returns system attributes for strategies.

    :param strategy_number:
    :type strategy_number: str
    :return: Attributes that front end uses
    '''
    return [
        {
            "key": "name",
            "name": "Name",
            "value_type": 10
        },
        {
            "key": "short_name",
            "name": "Short name",
            "value_type": 10
        },
        {
            "key": "user_code",
            "name": "User code",
            "value_type": 10
        },
        {
            "key": "public_name",
            "name": "Public name",
            "value_type": 10,
            "allow_null": True
        },
        {
            "key": "notes",
            "name": "Notes",
            "value_type": 10
        },
        {
            "key": "subgroup",
            "name": "Group",
            "value_type": "field",
            "value_entity": "strategy-" + strategy_number + "-subgroup",
            "value_content_type": "strategies.strategy" + strategy_number + "subgroup",
            "code": "user_code"
        },
    ]


class _SubgroupSystemAttrsMixin:
    @staticmethod
    def get_system_attrs():
        '''
        Returns system attributes for subgroups of strategies.
    
        :param strategy_number:
        :type strategy_number: str
        :return: Attributes that front end uses
        '''
        return [
           {
               "key": "name",
               "name": "Name",
               "value_type": 10
           },
           {
               "key": "short_name",
               "name": "Short name",
               "value_type": 10
           },
           {
               "key": "notes",
               "name": "Notes",
               "value_type": 10
           },
           {
               "key": "user_code",
               "name": "User code",
               "value_type": 10
           },
        ]

# 1 --


class Strategy1Group(NamedModel, FakeDeletableModel):
    master_user = models.ForeignKey(MasterUser, related_name='strategy1_groups',
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy('strategy1 group')
        verbose_name_plural = gettext_lazy('strategy1 groups')
        ordering = ['user_code']
        permissions = [
            # ('view_strategy1group', 'Can view strategy1 group'),
            ('manage_strategy1group', 'Can manage strategy1 group'),
        ]
        # unique_together = [
        #     ['master_user', 'user_code']
        # ]

    @property
    def is_default(self):
        return self.master_user.strategy1_group_id == self.id if self.master_user_id else False


class Strategy1Subgroup(NamedModel, FakeDeletableModel, _SubgroupSystemAttrsMixin):
    master_user = models.ForeignKey(MasterUser, related_name='strategy1_subgroups',
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)
    group = models.ForeignKey(Strategy1Group, null=True, blank=True, on_delete=models.PROTECT, related_name='subgroups')

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy('strategy1 subgroup')
        verbose_name_plural = gettext_lazy('strategy1 subgroups')
        ordering = ['user_code']
        permissions = [
            # ('view_strategy1subgroup', 'Can view strategy1 subgroup'),
            ('manage_strategy1subgroup', 'Can manage strategy1 subgroup'),
        ]
        # unique_together = [
        #     ['group', 'user_code']
        # ]

    @staticmethod
    def get_system_attrs():
        """
        Returns attributes that front end uses
        """
        return _get_strategy_system_attrs("1")

    @property
    def is_default(self):
        return self.master_user.strategy1_subgroup_id == self.id if self.master_user_id else False


class Strategy1(NamedModelAutoMapping, FakeDeletableModel, DataTimeStampedModel):
    master_user = models.ForeignKey(MasterUser, related_name='strategies1', verbose_name=gettext_lazy('master user'),
                                    on_delete=models.CASCADE)
    subgroup = models.ForeignKey(Strategy1Subgroup, null=True, blank=True, on_delete=models.PROTECT,
                                 related_name='strategies')

    attributes = GenericRelation(GenericAttribute, verbose_name=gettext_lazy('attributes'))

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy('strategy1')
        verbose_name_plural = gettext_lazy('strategies1')
        ordering = ['user_code']
        permissions = [
            # ('view_strategy1', 'Can view strategy1'),
            ('manage_strategy1', 'Can manage strategy1'),
        ]
        # unique_together = [
        #     ['subgroup', 'user_code']
        # ]

    @staticmethod
    def get_system_attrs():
        """
        Returns attributes that front end uses
        """
        return _get_strategy_system_attrs("1")

    @property
    def is_default(self):
        return self.master_user.strategy1_id == self.id if self.master_user_id else False


# 2 --


class Strategy2Group(NamedModel, FakeDeletableModel):
    master_user = models.ForeignKey(MasterUser, related_name='strategy2_groups',
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy('strategy2 group')
        verbose_name_plural = gettext_lazy('strategy2 groups')
        ordering = ['user_code']
        permissions = [
            # ('view_strategy2group', 'Can view strategy2 group'),
            ('manage_strategy2group', 'Can manage strategy2 group'),
        ]
        # unique_together = [
        #     ['master_user', 'user_code']
        # ]

    @property
    def is_default(self):
        return self.master_user.strategy2_group_id == self.id if self.master_user_id else False


class Strategy2Subgroup(NamedModel, FakeDeletableModel, _SubgroupSystemAttrsMixin):
    master_user = models.ForeignKey(MasterUser, related_name='strategy2_subgroups',
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)
    group = models.ForeignKey(Strategy2Group, null=True, blank=True, on_delete=models.PROTECT, related_name='subgroups')

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy('strategy2 subgroup')
        verbose_name_plural = gettext_lazy('strategy2 subgroups')
        ordering = ['user_code']
        permissions = [
            # ('view_strategy2subgroup', 'Can view strategy2 subgroup'),
            ('manage_strategy2subgroup', 'Can manage strategy2 subgroup'),
        ]
        # unique_together = [
        #     ['group', 'user_code']
        # ]

    @property
    def is_default(self):
        return self.master_user.strategy2_subgroup_id == self.id if self.master_user_id else False


class Strategy2(NamedModelAutoMapping, FakeDeletableModel, DataTimeStampedModel):
    master_user = models.ForeignKey(MasterUser, related_name='strategies2', verbose_name=gettext_lazy('master user'),
                                    on_delete=models.CASCADE)
    subgroup = models.ForeignKey(Strategy2Subgroup, null=True, blank=True, on_delete=models.PROTECT,
                                 related_name='strategies')

    attributes = GenericRelation(GenericAttribute, verbose_name=gettext_lazy('attributes'))

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy('strategy2')
        verbose_name_plural = gettext_lazy('strategies2')
        ordering = ['user_code']
        permissions = [
            # ('view_strategy2', 'Can view strategy2'),
            ('manage_strategy2', 'Can manage strategy2'),
        ]
        # unique_together = [
        #     ['subgroup', 'user_code']
        # ]

    @staticmethod
    def get_system_attrs():
        """
        Returns attributes that front end uses
        """
        return _get_strategy_system_attrs("2")

    @property
    def is_default(self):
        return self.master_user.strategy2_id == self.id if self.master_user_id else False


# 3 --


class Strategy3Group(NamedModel, FakeDeletableModel):
    master_user = models.ForeignKey(MasterUser, related_name='strategy3_groups',
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy('strategy3 group')
        verbose_name_plural = gettext_lazy('strategy3 groups')
        ordering = ['user_code']
        permissions = [
            # ('view_strategy3group', 'Can view strategy3 group'),
            ('manage_strategy3group', 'Can manage strategy3 group'),
        ]
        # unique_together = [
        #     ['master_user', 'user_code']
        # ]

    @property
    def is_default(self):
        return self.master_user.strategy3_group_id == self.id if self.master_user_id else False


class Strategy3Subgroup(NamedModel, FakeDeletableModel, _SubgroupSystemAttrsMixin):
    master_user = models.ForeignKey(MasterUser, related_name='strategy3_subgroups',
                                    verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)
    group = models.ForeignKey(Strategy3Group, null=True, blank=True, on_delete=models.PROTECT, related_name='subgroups')

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy('strategy3 subgroup')
        verbose_name_plural = gettext_lazy('strategy3 subgroups')
        ordering = ['user_code']
        permissions = [
            # ('view_strategy3subgroup', 'Can view strategy3 subgroup'),
            ('manage_strategy3subgroup', 'Can manage strategy3 subgroup'),
        ]
        # unique_together = [
        #     ['group', 'user_code']
        # ]

    @property
    def is_default(self):
        return self.master_user.strategy3_subgroup_id == self.id if self.master_user_id else False


class Strategy3(NamedModelAutoMapping, FakeDeletableModel, DataTimeStampedModel):
    master_user = models.ForeignKey(MasterUser, related_name='strategies3', verbose_name=gettext_lazy('master user'),
                                    on_delete=models.CASCADE)
    subgroup = models.ForeignKey(Strategy3Subgroup, null=True, blank=True, on_delete=models.PROTECT,
                                 related_name='strategies')

    attributes = GenericRelation(GenericAttribute, verbose_name=gettext_lazy('attributes'))

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = gettext_lazy('strategy3')
        verbose_name_plural = gettext_lazy('strategies3')
        ordering = ['user_code']
        permissions = [
            # ('view_strategy3', 'Can view strategy3'),
            ('manage_strategy3', 'Can manage strategy3'),
        ]
        # unique_together = [
        #     ['subgroup', 'user_code']
        # ]

    @staticmethod
    def get_system_attrs():
        """
        Returns attributes that front end uses
        """
        return _get_strategy_system_attrs("3")

    @property
    def is_default(self):
        return self.master_user.strategy3_id == self.id if self.master_user_id else False
