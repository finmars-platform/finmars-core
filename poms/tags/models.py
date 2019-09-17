from __future__ import unicode_literals

from django.contrib.contenttypes.fields import GenericRelation, GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import ugettext_lazy

from poms.common.models import NamedModel
from poms.obj_perms.models import GenericObjectPermission


class Tag(NamedModel):
    master_user = models.ForeignKey('users.MasterUser', related_name='tags', verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE)
    content_types = models.ManyToManyField(ContentType, related_name='tags', blank=True,
                                           verbose_name=ugettext_lazy('content types'))

    # account_types = models.ManyToManyField('accounts.AccountType', related_name='tags', blank=True,
    #                                        verbose_name=ugettext_lazy('account types'))
    # accounts = models.ManyToManyField('accounts.Account', related_name='tags', blank=True,
    #                                   verbose_name=ugettext_lazy('accounts'))
    #
    # currencies = models.ManyToManyField('currencies.Currency', related_name='tags', blank=True,
    #                                     verbose_name=ugettext_lazy('currencies'))
    #
    # instrument_types = models.ManyToManyField('instruments.InstrumentType', related_name='tags', blank=True,
    #                                           verbose_name=ugettext_lazy('instrument types'))
    # instruments = models.ManyToManyField('instruments.Instrument', related_name='tags', blank=True,
    #                                      verbose_name=ugettext_lazy('instruments'))
    #
    # counterparty_groups = models.ManyToManyField('counterparties.CounterpartyGroup', related_name='tags', blank=True,
    #                                              verbose_name=ugettext_lazy('counterparty groups'))
    # counterparties = models.ManyToManyField('counterparties.Counterparty', related_name='tags', blank=True,
    #                                         verbose_name=ugettext_lazy('counterparties'))
    # responsible_groups = models.ManyToManyField('counterparties.ResponsibleGroup', related_name='tags', blank=True,
    #                                             verbose_name=ugettext_lazy('responsible groups'))
    # responsibles = models.ManyToManyField('counterparties.Responsible', related_name='tags', blank=True,
    #                                       verbose_name=ugettext_lazy('responsibles'))
    #
    # portfolios = models.ManyToManyField('portfolios.Portfolio', related_name='tags', blank=True,
    #                                     verbose_name=ugettext_lazy('portfolios'))
    #
    # transaction_type_groups = models.ManyToManyField('transactions.TransactionTypeGroup', related_name='tags',
    #                                                  blank=True, verbose_name=ugettext_lazy('transaction type groups'))
    # transaction_types = models.ManyToManyField('transactions.TransactionType', related_name='tags', blank=True,
    #                                            verbose_name=ugettext_lazy('transaction types'))
    #
    # strategy1_groups = models.ManyToManyField('strategies.Strategy1Group', related_name='tags', blank=True,
    #                                           verbose_name=ugettext_lazy('strategy1 groups'))
    # strategy1_subgroups = models.ManyToManyField('strategies.Strategy1Subgroup', related_name='tags', blank=True,
    #                                              verbose_name=ugettext_lazy('strategy1 subgroups'))
    # strategies1 = models.ManyToManyField('strategies.Strategy1', related_name='tags', blank=True,
    #                                      verbose_name=ugettext_lazy('strategies1'))
    #
    # strategy2_groups = models.ManyToManyField('strategies.Strategy2Group', related_name='tags', blank=True,
    #                                           verbose_name=ugettext_lazy('strategy2 groups'))
    # strategy2_subgroups = models.ManyToManyField('strategies.Strategy2Subgroup', related_name='tags', blank=True,
    #                                              verbose_name=ugettext_lazy('strategy2 subgroups'))
    # strategies2 = models.ManyToManyField('strategies.Strategy2', related_name='tags', blank=True,
    #                                      verbose_name=ugettext_lazy('strategies2'))
    #
    # strategy3_groups = models.ManyToManyField('strategies.Strategy3Group', related_name='tags', blank=True,
    #                                           verbose_name=ugettext_lazy('strategy3 groups'))
    # strategy3_subgroups = models.ManyToManyField('strategies.Strategy3Subgroup', related_name='tags', blank=True,
    #                                              verbose_name=ugettext_lazy('strategy3 subgroups'))
    # strategies3 = models.ManyToManyField('strategies.Strategy3', related_name='tags', blank=True,
    #                                      verbose_name=ugettext_lazy('strategies3'))
    #
    # thread_groups = models.ManyToManyField('chats.ThreadGroup', related_name='tags', blank=True)
    # threads = models.ManyToManyField('chats.Thread', related_name='tags', blank=True)

    object_permissions = GenericRelation(GenericObjectPermission, verbose_name=ugettext_lazy('object permissions'))

    class Meta(NamedModel.Meta):
        verbose_name = ugettext_lazy('tag')
        verbose_name_plural = ugettext_lazy('tags')
        permissions = [
            # ('view_tag', 'Can view tag'),
            ('manage_tag', 'Can manage tag'),
        ]


# class TagUserObjectPermission(AbstractUserObjectPermission):
#     content_object = models.ForeignKey(Tag, related_name='user_object_permissions',
#                                        verbose_name=ugettext_lazy('content object'))
#
#     class Meta(AbstractUserObjectPermission.Meta):
#         verbose_name = ugettext_lazy('tags - user permission')
#         verbose_name_plural = ugettext_lazy('tags - user permissions')
#
#
# class TagGroupObjectPermission(AbstractGroupObjectPermission):
#     content_object = models.ForeignKey(Tag, related_name='group_object_permissions',
#                                        verbose_name=ugettext_lazy('content object'))
#
#     class Meta(AbstractGroupObjectPermission.Meta):
#         verbose_name = ugettext_lazy('tags - group permission')
#         verbose_name_plural = ugettext_lazy('tags - group permissions')


class TagLink(models.Model):
    tag = models.ForeignKey(Tag, related_name='links', verbose_name=ugettext_lazy('tag'), on_delete=models.CASCADE)

    content_type = models.ForeignKey(ContentType, null=True, blank=True, verbose_name=ugettext_lazy('content type'), on_delete=models.CASCADE)
    object_id = models.BigIntegerField(verbose_name=ugettext_lazy('object id'))
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name = ugettext_lazy('tag link')
        verbose_name_plural = ugettext_lazy('tag links')

    def __str__(self):
        return '%s @ %s' % (self.content_object, self.tag)
