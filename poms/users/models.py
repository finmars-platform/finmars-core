from __future__ import unicode_literals

import pytz
from django.conf import settings
from django.contrib.auth.models import User, Permission
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy

from poms.common.models import NamedModel, FakeDeletableModel

AVAILABLE_APPS = ['accounts', 'counterparties', 'currencies', 'instruments', 'portfolios', 'strategies', 'transactions',
                  'reports', 'users']

LANGUAGE_MAX_LENGTH = 5
TIMEZONE_MAX_LENGTH = 20
TIMEZONE_CHOICES = sorted(list((k, k) for k in pytz.all_timezones))
TIMEZONE_COMMON_CHOICES = sorted(list((k, k) for k in pytz.common_timezones))


class MasterUserManager(models.Manager):
    def create_master_user(self, user=None, **kwargs):
        obj = MasterUser(**kwargs)
        obj.save()
        obj.create_defaults()

        if user:
            Member.objects.create(master_user=obj, user=user, is_owner=True, is_admin=True)

        return obj


class MasterUser(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True,
                            verbose_name=ugettext_lazy('name'))
    language = models.CharField(max_length=LANGUAGE_MAX_LENGTH, default=settings.LANGUAGE_CODE,
                                verbose_name=ugettext_lazy('language'))
    timezone = models.CharField(max_length=TIMEZONE_MAX_LENGTH, default=settings.TIME_ZONE,
                                verbose_name=ugettext_lazy('timezone'))
    system_currency = models.ForeignKey('currencies.Currency', null=True, blank=True, on_delete=models.PROTECT,
                                        related_name='+',
                                        verbose_name=ugettext_lazy('system currency'))

    account_type = models.ForeignKey('accounts.AccountType', null=True, blank=True, on_delete=models.PROTECT,
                                     verbose_name=ugettext_lazy('account type'))
    account = models.ForeignKey('accounts.Account', null=True, blank=True, on_delete=models.PROTECT,
                                verbose_name=ugettext_lazy('account'))

    currency = models.ForeignKey('currencies.Currency', null=True, blank=True, on_delete=models.PROTECT,
                                 verbose_name=ugettext_lazy('currency'))
    counterparty_group = models.ForeignKey('counterparties.CounterpartyGroup', null=True, blank=True,
                                           on_delete=models.PROTECT, verbose_name=ugettext_lazy('counterparty group'))
    counterparty = models.ForeignKey('counterparties.Counterparty', null=True, blank=True, on_delete=models.PROTECT,
                                     verbose_name=ugettext_lazy('counterparty'))
    responsible_group = models.ForeignKey('counterparties.ResponsibleGroup', null=True, blank=True,
                                          on_delete=models.PROTECT, verbose_name=ugettext_lazy('responsible group'))
    responsible = models.ForeignKey('counterparties.Responsible', null=True, blank=True, on_delete=models.PROTECT,
                                    verbose_name=ugettext_lazy('responsible'))

    instrument_type = models.ForeignKey('instruments.InstrumentType', null=True, blank=True, on_delete=models.PROTECT,
                                        verbose_name=ugettext_lazy('instrument type'))
    instrument = models.ForeignKey('instruments.Instrument', null=True, blank=True, on_delete=models.PROTECT,
                                   verbose_name=ugettext_lazy('instrument'))

    portfolio = models.ForeignKey('portfolios.Portfolio', null=True, blank=True, on_delete=models.PROTECT,
                                  verbose_name=ugettext_lazy('portfolio'))

    strategy1_group = models.ForeignKey('strategies.Strategy1Group', null=True, blank=True, on_delete=models.PROTECT,
                                        related_name='master_user_strategy1_group',
                                        verbose_name=ugettext_lazy('strategy1 group'))
    strategy1_subgroup = models.ForeignKey('strategies.Strategy1Subgroup', null=True, blank=True,
                                           on_delete=models.PROTECT, related_name='master_user_strategy1_subgroup',
                                           verbose_name=ugettext_lazy('strategy1 subgroup'))
    strategy1 = models.ForeignKey('strategies.Strategy1', null=True, blank=True, on_delete=models.PROTECT,
                                  related_name='master_user_strategy1', verbose_name=ugettext_lazy('strategy1'))

    strategy2_group = models.ForeignKey('strategies.Strategy2Group', null=True, blank=True, on_delete=models.PROTECT,
                                        related_name='master_user_strategy2_group',
                                        verbose_name=ugettext_lazy('strategy2 group'))
    strategy2_subgroup = models.ForeignKey('strategies.Strategy2Subgroup', null=True, blank=True,
                                           on_delete=models.PROTECT, related_name='master_user_strategy2_subgroup',
                                           verbose_name=ugettext_lazy('strategy2 subgroup'))
    strategy2 = models.ForeignKey('strategies.Strategy2', null=True, blank=True, on_delete=models.PROTECT,
                                  related_name='master_user_strategy2', verbose_name=ugettext_lazy('strategy2'))

    strategy3_group = models.ForeignKey('strategies.Strategy3Group', null=True, blank=True, on_delete=models.PROTECT,
                                        related_name='master_user_strategy3_group',
                                        verbose_name=ugettext_lazy('strategy3 group'))
    strategy3_subgroup = models.ForeignKey('strategies.Strategy3Subgroup', null=True, blank=True,
                                           on_delete=models.PROTECT, related_name='master_user_strategy3_subgroup',
                                           verbose_name=ugettext_lazy('strategy3 subgroup'))
    strategy3 = models.ForeignKey('strategies.Strategy3', null=True, blank=True, on_delete=models.PROTECT,
                                  related_name='master_user_strategy3', verbose_name=ugettext_lazy('strategy3'))

    thread_group = models.ForeignKey('chats.ThreadGroup', null=True, blank=True, on_delete=models.PROTECT,
                                     related_name='master_user_thread_group',
                                     verbose_name=ugettext_lazy('thread group'))

    transaction_type_group = models.ForeignKey('transactions.TransactionTypeGroup', null=True, blank=True,
                                               on_delete=models.PROTECT,
                                               verbose_name=ugettext_lazy('transaction type group'))

    mismatch_portfolio = models.ForeignKey('portfolios.Portfolio', null=True, blank=True, on_delete=models.PROTECT,
                                           related_name='master_user_mismatch_portfolio',
                                           verbose_name=ugettext_lazy('mismatch portfolio'))
    mismatch_account = models.ForeignKey('accounts.Account', null=True, blank=True, on_delete=models.PROTECT,
                                         related_name='master_user_mismatch_account',
                                         verbose_name=ugettext_lazy('mismatch account'))

    # TODO: what is notification_business_days
    notification_business_days = models.IntegerField(default=0)

    objects = MasterUserManager()

    class Meta:
        verbose_name = ugettext_lazy('master user')
        verbose_name_plural = ugettext_lazy('master users')
        ordering = ['name']

    def __str__(self):
        return self.name

    def create_defaults(self, user=None):
        from poms.currencies.models import currencies_data, Currency
        from poms.accounts.models import AccountType, Account
        from poms.counterparties.models import Counterparty, CounterpartyGroup, Responsible, ResponsibleGroup
        from poms.portfolios.models import Portfolio
        from poms.instruments.models import InstrumentClass, InstrumentType, EventScheduleConfig, Instrument
        from poms.integrations.models import PricingAutomatedSchedule, CurrencyMapping, ProviderClass
        from poms.strategies.models import Strategy1Group, Strategy1Subgroup, Strategy1, Strategy2Group, \
            Strategy2Subgroup, Strategy2, Strategy3Group, Strategy3Subgroup, Strategy3
        from poms.chats.models import ThreadGroup
        from poms.transactions.models import NotificationClass, TransactionTypeGroup
        from poms.obj_perms.utils import get_change_perms, assign_perms3

        if not EventScheduleConfig.objects.filter(master_user=self).exists():
            EventScheduleConfig.create_default(master_user=self)

        if not PricingAutomatedSchedule.objects.filter(master_user=self).exists():
            PricingAutomatedSchedule.objects.create(master_user=self, is_enabled=False)

        ccys = {}
        ccy = Currency.objects.create(master_user=self, name='-')
        ccy_usd = None
        for dc in currencies_data.values():
            dc_user_code = dc['user_code']
            dc_name = dc.get('name', dc_user_code)
            dc_reference_for_pricing = dc.get('reference_for_pricing', None)

            if dc_user_code == '-':
                pass
            else:
                c = Currency.objects.create(master_user=self, user_code=dc_user_code, short_name=dc_name, name=dc_name,
                                            reference_for_pricing=dc_reference_for_pricing)
                if dc_user_code == 'USD':
                    ccy_usd = c
                ccys[c.user_code] = c

        account_type = AccountType.objects.create(master_user=self, name='-')
        account = Account.objects.create(master_user=self, type=account_type, name='-')

        counterparty_group = CounterpartyGroup.objects.create(master_user=self, name='-')
        counterparty = Counterparty.objects.create(master_user=self, group=counterparty_group, name='-')
        responsible_group = ResponsibleGroup.objects.create(master_user=self, name='-')
        responsible = Responsible.objects.create(master_user=self, group=responsible_group, name='-')

        portfolio = Portfolio.objects.create(master_user=self, name='-')

        instrument_general_class = InstrumentClass.objects.get(pk=InstrumentClass.GENERAL)
        instrument_type = InstrumentType.objects.create(master_user=self, instrument_class=instrument_general_class,
                                                        name='-')
        instrument = Instrument.objects.create(master_user=self, instrument_type=instrument_type, pricing_currency=ccy,
                                               accrued_currency=ccy, name='-')

        strategy1_group = Strategy1Group.objects.create(master_user=self, name='-')
        strategy1_subgroup = Strategy1Subgroup.objects.create(master_user=self, group=strategy1_group, name='-')
        strategy1 = Strategy1.objects.create(master_user=self, subgroup=strategy1_subgroup, name='-')

        strategy2_group = Strategy2Group.objects.create(master_user=self, name='-')
        strategy2_subgroup = Strategy2Subgroup.objects.create(master_user=self, group=strategy2_group, name='-')
        strategy2 = Strategy2.objects.create(master_user=self, subgroup=strategy2_subgroup, name='-')

        strategy3_group = Strategy3Group.objects.create(master_user=self, name='-')
        strategy3_subgroup = Strategy3Subgroup.objects.create(master_user=self, group=strategy3_group, name='-')
        strategy3 = Strategy3.objects.create(master_user=self, subgroup=strategy3_subgroup, name='-')

        thread_group = ThreadGroup.objects.create(master_user=self, name='-')

        transaction_type_group = TransactionTypeGroup.objects.create(master_user=self, name='-')

        if user:
            Member.objects.create(user=user, master_user=self, is_owner=True, is_admin=True)
        group = Group.objects.create(master_user=self, name='%s' % ugettext_lazy('Default'))

        bloomberg = ProviderClass.objects.get(pk=ProviderClass.BLOOMBERG)
        for dc in currencies_data.values():
            dc_user_code = dc['user_code']
            dc_bloomberg = dc['bloomberg']

            if dc_user_code != '-' and dc_user_code in ccys:
                c = ccys[dc_user_code]
                CurrencyMapping.objects.create(master_user=self, provider=bloomberg, value=dc_bloomberg,
                                               content_object=c)

        self.system_currency = ccy_usd
        self.currency = ccy
        self.account_type = account_type
        self.account = account
        self.counterparty_group = counterparty_group
        self.counterparty = counterparty
        self.responsible_group = responsible_group
        self.responsible = responsible
        self.portfolio = portfolio
        self.instrument_type = instrument_type
        self.instrument = instrument
        self.strategy1_group = strategy1_group
        self.strategy1_subgroup = strategy1_subgroup
        self.strategy1 = strategy1
        self.strategy2_group = strategy2_group
        self.strategy2_subgroup = strategy2_subgroup
        self.strategy2 = strategy2
        self.strategy3_group = strategy3_group
        self.strategy3_subgroup = strategy3_subgroup
        self.strategy3 = strategy3
        self.thread_group = thread_group
        self.transaction_type_group = transaction_type_group
        self.mismatch_portfolio = portfolio
        self.mismatch_account = account
        self.save()

        for c in [account_type, account, counterparty_group, counterparty, responsible_group, responsible, portfolio,
                  instrument_type, instrument, strategy1_group, strategy1_subgroup, strategy1, strategy2_group,
                  strategy2_subgroup, strategy2, strategy3_group, strategy3_subgroup, strategy3, thread_group,
                  transaction_type_group]:
            for p in get_change_perms(c):
                assign_perms3(c, perms=[{'group': group, 'permission': p}])

        FakeSequence.objects.get_or_create(master_user=self, name='complex_transaction')
        FakeSequence.objects.get_or_create(master_user=self, name='transaction')

    def patch_currencies(self, overwrite_name=False, overwrite_reference_for_pricing=False):
        from poms.currencies.models import currencies_data, Currency

        ccys_existed = {c.user_code: c for c in Currency.objects.filter(master_user=self, is_deleted=False)}

        ccys = {}
        for dc in currencies_data.values():
            dc_user_code = dc['user_code']
            dc_name = dc.get('name', dc_user_code)
            dc_reference_for_pricing = dc.get('reference_for_pricing', None)

            if dc_user_code in ccys_existed:
                c1 = ccys_existed[dc_user_code]
                is_change = False

                if overwrite_name or not c1.name:
                    c1.name = dc_name
                    is_change = True

                if overwrite_name or not c1.short_name:
                    c1.short_name = dc_name
                    is_change = True

                if overwrite_name or not c1.public_name:
                    c1.public_name = dc_name
                    is_change = True

                if overwrite_reference_for_pricing or not c1.reference_for_pricing:
                    c1.reference_for_pricing = dc_reference_for_pricing
                    is_change = True

                if is_change:
                    c1.save()
            else:
                c = Currency.objects.create(master_user=self, user_code=dc_user_code, name=dc_name, short_name=dc_name,
                                            public_name=dc_name, reference_for_pricing=dc_reference_for_pricing)
                ccys[c.user_code] = c

    def patch_bloomberg_currency_mappings(self, overwrite_mapping=False):
        from poms.integrations.models import ProviderClass, CurrencyMapping
        from poms.currencies.models import currencies_data, Currency
        bloomberg = ProviderClass.objects.get(pk=ProviderClass.BLOOMBERG)

        ccys = {c.user_code: c for c in Currency.objects.filter(master_user=self)}

        mapping_existed = {m.currency_id: m
                           for m in CurrencyMapping.objects.filter(master_user=self, provider=bloomberg)}

        for dc in currencies_data.values():
            dc_user_code = dc['user_code']
            dc_bloomberg = dc['bloomberg']

            if dc_user_code != '-' and dc_user_code in ccys:
                c = ccys[dc_user_code]
                if c.id in mapping_existed:
                    if overwrite_mapping:
                        mapping = mapping_existed[c.id]
                        mapping.value = dc_bloomberg
                        mapping.save()
                else:
                    CurrencyMapping.objects.create(master_user=self, provider=bloomberg, value=dc_bloomberg, currency=c)


class Member(FakeDeletableModel):
    master_user = models.ForeignKey(MasterUser, related_name='members', verbose_name=ugettext_lazy('master user'))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='members', verbose_name=ugettext_lazy('user'))

    username = models.CharField(max_length=255, blank=True, default='', editable=False,
                                verbose_name=ugettext_lazy('username'))
    first_name = models.CharField(max_length=30, blank=True, default='', editable=False,
                                  verbose_name=ugettext_lazy('first name'))
    last_name = models.CharField(max_length=30, blank=True, default='', editable=False,
                                 verbose_name=ugettext_lazy('last name'))
    email = models.EmailField(blank=True, default='', editable=False, verbose_name=ugettext_lazy('email'))

    join_date = models.DateTimeField(auto_now_add=True, verbose_name=ugettext_lazy('join date'))
    is_owner = models.BooleanField(default=False, verbose_name=ugettext_lazy('is owner'))
    is_admin = models.BooleanField(default=False, verbose_name=ugettext_lazy('is admin'))

    groups = models.ManyToManyField('Group', blank=True, related_name='members', verbose_name=ugettext_lazy('groups'))

    # permissions = models.ManyToManyField(Permission, blank=True)

    class Meta(FakeDeletableModel.Meta):
        verbose_name = ugettext_lazy('member')
        verbose_name_plural = ugettext_lazy('members')
        unique_together = [
            ['master_user', 'user']
        ]
        ordering = ['username']

    def __str__(self):
        return self.username

    def fake_delete(self):
        self.user = None
        self.is_deleted = True
        self.save()

    @property
    def is_superuser(self):
        return self.is_owner or self.is_admin

    @property
    def display_name(self):
        if self.first_name or self.last_name:
            return ' '.join([self.first_name, self.last_name])
        else:
            return self.username


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='profile',
                                verbose_name=ugettext_lazy('user'))
    language = models.CharField(max_length=LANGUAGE_MAX_LENGTH, default=settings.LANGUAGE_CODE,
                                verbose_name=ugettext_lazy('language'))
    timezone = models.CharField(max_length=TIMEZONE_MAX_LENGTH, default=settings.TIME_ZONE,
                                verbose_name=ugettext_lazy('timezone'))

    class Meta:
        verbose_name = ugettext_lazy('profile')
        verbose_name_plural = ugettext_lazy('profiles')

    def __str__(self):
        return self.user.username


class Group(models.Model):
    master_user = models.ForeignKey(MasterUser, related_name='groups', verbose_name=ugettext_lazy('master user'), )
    name = models.CharField(max_length=80, verbose_name=ugettext_lazy('name'))

    # permissions = models.ManyToManyField(Permission, verbose_name=ugettext_lazy('permissions'), blank=True,
    #                                      related_name='poms_groups')

    class Meta:
        verbose_name = ugettext_lazy('group')
        verbose_name_plural = ugettext_lazy('groups')
        unique_together = [
            ['master_user', 'name']
        ]
        ordering = ['name']
        # permissions = [
        #     ('view_group', 'Can view group')
        # ]

    def __str__(self):
        return self.name


class FakeSequence(models.Model):
    master_user = models.ForeignKey(MasterUser, related_name='fake_sequences',
                                    verbose_name=ugettext_lazy('master user'), )
    name = models.CharField(max_length=80, verbose_name=ugettext_lazy('name'))
    value = models.PositiveIntegerField(default=0, verbose_name=ugettext_lazy('value'))

    class Meta:
        verbose_name = ugettext_lazy('fake sequence')
        verbose_name_plural = ugettext_lazy('fake sequences')
        unique_together = [
            ['master_user', 'name']
        ]
        ordering = ['name']
        # permissions = [
        #     ('view_group', 'Can view group')
        # ]

    def __str__(self):
        return "%s: %s" % (self.name, self.value)

    # @staticmethod
    # def inc1(master_user, name):
    #     for i in range(20):
    #         seq = SimpleSequence.objects.get_or_create(master_user=master_user, name=name)
    #         newval = seq.value + 1
    #         updated = SimpleSequence.objects.filter(id=seq.id, value=seq.value).update(value=newval)
    #         if updated == 1:
    #             return newval
    #     return RuntimeError('simple sequence optimistic lock error')

    @classmethod
    def next_value(cls, master_user, name, d=1):

        # seq = SimpleSequence.objects.select_for_update().get_or_create(master_user=master_user, name=name)
        # seq = SimpleSequence.objects.select_for_update().get(master_user=master_user, name=name)

        seq, created = cls.objects.update_or_create(master_user=master_user, name=name)

        if not d:
            d = 1
        if d == 1:
            seq.value += 1
        else:
            seq.value = ((seq.value + d) // d) * d

        seq.save(update_fields=['value'])

        return seq.value


@receiver(post_save, dispatch_uid='create_profile', sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance=None, created=None, **kwargs):
    if created:
        UserProfile.objects.create(
            user=instance,
            language=settings.LANGUAGE_CODE,
            timezone=settings.TIME_ZONE,
        )


@receiver(post_save, dispatch_uid='update_member_when_member_created', sender=Member)
def update_member_when_member_created(sender, instance=None, created=None, **kwargs):
    if created:
        instance.username = instance.user.username
        instance.first_name = instance.user.first_name
        instance.last_name = instance.user.last_name
        instance.email = instance.user.email
        instance.save(update_fields=['username', 'first_name', 'last_name', 'email'])


@receiver(post_save, dispatch_uid='update_member_when_user_updated', sender=settings.AUTH_USER_MODEL)
def update_member_when_user_updated(sender, instance=None, created=None, **kwargs):
    if not created:
        instance.members.all().update(
            username=instance.username,
            first_name=instance.first_name,
            last_name=instance.last_name,
            email=instance.email
        )
