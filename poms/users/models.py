from __future__ import unicode_literals

import json
import uuid

import pytz
from django.conf import settings
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy


from poms.common.models import NamedModel, FakeDeletableModel

import binascii
import os

from poms.common.utils import get_content_type_by_name

AVAILABLE_APPS = ['accounts', 'counterparties', 'currencies', 'instruments', 'portfolios', 'strategies', 'transactions',
                  'reports', 'users']

LANGUAGE_MAX_LENGTH = 5
TIMEZONE_MAX_LENGTH = 20
TIMEZONE_CHOICES = sorted(list((k, k) for k in pytz.all_timezones))
TIMEZONE_COMMON_CHOICES = sorted(list((k, k) for k in pytz.common_timezones))


class ResetPasswordToken(models.Model):
    class Meta:
        verbose_name = ugettext_lazy("Password Reset Token")
        verbose_name_plural = ugettext_lazy("Password Reset Tokens")

    @staticmethod
    def generate_key():
        """ generates a pseudo random code using os.urandom and binascii.hexlify """
        return binascii.hexlify(os.urandom(32)).decode()

    id = models.AutoField(
        primary_key=True
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='password_reset_tokens',
        on_delete=models.CASCADE,
        verbose_name=ugettext_lazy("The User which is associated to this password reset token")
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=ugettext_lazy("When was this token generated")
    )

    # Key field, though it is not the primary key of the model
    key = models.CharField(
        ugettext_lazy("Key"),
        max_length=64,
        db_index=True,
        unique=True
    )

    ip_address = models.GenericIPAddressField(
        ugettext_lazy("The IP address of this session"),
        default="127.0.0.1"
    )
    user_agent = models.CharField(
        max_length=256,
        verbose_name=ugettext_lazy("HTTP User Agent"),
        default=""
    )

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(ResetPasswordToken, self).save(*args, **kwargs)

    def __str__(self):
        return "Password reset token for user {user}".format(user=self.user)


class MasterUserManager(models.Manager):
    def create_master_user(self, user=None, **kwargs):
        obj = MasterUser(**kwargs)

        token = uuid.uuid4().hex

        obj.token = token

        obj.save()
        obj.create_defaults()

        # if user:
        #     Member.objects.create(master_user=obj, user=user, is_owner=True, is_admin=True)

        return obj

class MasterUser(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True,
                            verbose_name=ugettext_lazy('name'))

    description = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('description'))

    language = models.CharField(max_length=LANGUAGE_MAX_LENGTH, default=settings.LANGUAGE_CODE,
                                verbose_name=ugettext_lazy('language'))
    timezone = models.CharField(max_length=TIMEZONE_MAX_LENGTH, default=settings.TIME_ZONE,
                                verbose_name=ugettext_lazy('timezone'))
    system_currency = models.ForeignKey('currencies.Currency', null=True, blank=True, on_delete=models.SET_NULL,
                                        related_name='+',
                                        verbose_name=ugettext_lazy('system currency'))

    account_type = models.ForeignKey('accounts.AccountType', null=True, blank=True, on_delete=models.SET_NULL,
                                     verbose_name=ugettext_lazy('account type'))
    account = models.ForeignKey('accounts.Account', null=True, blank=True, on_delete=models.SET_NULL,
                                verbose_name=ugettext_lazy('account'))

    currency = models.ForeignKey('currencies.Currency', null=True, blank=True, on_delete=models.SET_NULL,
                                 verbose_name=ugettext_lazy('currency'))
    counterparty_group = models.ForeignKey('counterparties.CounterpartyGroup', null=True, blank=True,
                                           on_delete=models.SET_NULL, verbose_name=ugettext_lazy('counterparty group'))
    counterparty = models.ForeignKey('counterparties.Counterparty', null=True, blank=True, on_delete=models.SET_NULL,
                                     verbose_name=ugettext_lazy('counterparty'))
    responsible_group = models.ForeignKey('counterparties.ResponsibleGroup', null=True, blank=True,
                                          on_delete=models.SET_NULL, verbose_name=ugettext_lazy('responsible group'))
    responsible = models.ForeignKey('counterparties.Responsible', null=True, blank=True, on_delete=models.SET_NULL,
                                    verbose_name=ugettext_lazy('responsible'))

    instrument_type = models.ForeignKey('instruments.InstrumentType', null=True, blank=True, on_delete=models.SET_NULL,
                                        verbose_name=ugettext_lazy('instrument type'))
    instrument = models.ForeignKey('instruments.Instrument', null=True, blank=True, on_delete=models.SET_NULL,
                                   verbose_name=ugettext_lazy('instrument'))

    portfolio = models.ForeignKey('portfolios.Portfolio', null=True, blank=True, on_delete=models.SET_NULL,
                                  verbose_name=ugettext_lazy('portfolio'))

    strategy1_group = models.ForeignKey('strategies.Strategy1Group', null=True, blank=True, on_delete=models.SET_NULL,
                                        related_name='master_user_strategy1_group',
                                        verbose_name=ugettext_lazy('strategy1 group'))
    strategy1_subgroup = models.ForeignKey('strategies.Strategy1Subgroup', null=True, blank=True,
                                           on_delete=models.SET_NULL, related_name='master_user_strategy1_subgroup',
                                           verbose_name=ugettext_lazy('strategy1 subgroup'))
    strategy1 = models.ForeignKey('strategies.Strategy1', null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name='master_user_strategy1', verbose_name=ugettext_lazy('strategy1'))

    strategy2_group = models.ForeignKey('strategies.Strategy2Group', null=True, blank=True, on_delete=models.SET_NULL,
                                        related_name='master_user_strategy2_group',
                                        verbose_name=ugettext_lazy('strategy2 group'))
    strategy2_subgroup = models.ForeignKey('strategies.Strategy2Subgroup', null=True, blank=True,
                                           on_delete=models.SET_NULL, related_name='master_user_strategy2_subgroup',
                                           verbose_name=ugettext_lazy('strategy2 subgroup'))
    strategy2 = models.ForeignKey('strategies.Strategy2', null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name='master_user_strategy2', verbose_name=ugettext_lazy('strategy2'))

    strategy3_group = models.ForeignKey('strategies.Strategy3Group', null=True, blank=True, on_delete=models.SET_NULL,
                                        related_name='master_user_strategy3_group',
                                        verbose_name=ugettext_lazy('strategy3 group'))
    strategy3_subgroup = models.ForeignKey('strategies.Strategy3Subgroup', null=True, blank=True,
                                           on_delete=models.SET_NULL, related_name='master_user_strategy3_subgroup',
                                           verbose_name=ugettext_lazy('strategy3 subgroup'))
    strategy3 = models.ForeignKey('strategies.Strategy3', null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name='master_user_strategy3', verbose_name=ugettext_lazy('strategy3'))

    thread_group = models.ForeignKey('chats.ThreadGroup', null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name='master_user_thread_group',
                                     verbose_name=ugettext_lazy('thread group'))

    transaction_type = models.ForeignKey('transactions.TransactionType', null=True, blank=True,
                                         on_delete=models.SET_NULL,
                                         verbose_name=ugettext_lazy('transaction type'))

    transaction_type_group = models.ForeignKey('transactions.TransactionTypeGroup', null=True, blank=True,
                                               on_delete=models.SET_NULL,
                                               verbose_name=ugettext_lazy('transaction type group'))

    mismatch_portfolio = models.ForeignKey('portfolios.Portfolio', null=True, blank=True, on_delete=models.SET_NULL,
                                           related_name='master_user_mismatch_portfolio',
                                           verbose_name=ugettext_lazy('mismatch portfolio'))
    mismatch_account = models.ForeignKey('accounts.Account', null=True, blank=True, on_delete=models.SET_NULL,
                                         related_name='master_user_mismatch_account',
                                         verbose_name=ugettext_lazy('mismatch account'))

    pricing_policy = models.ForeignKey('instruments.PricingPolicy', null=True, blank=True, on_delete=models.SET_NULL,
                                       verbose_name=ugettext_lazy('pricing policy'))

    price_download_scheme = models.ForeignKey('integrations.PriceDownloadScheme', null=True, blank=True,
                                              on_delete=models.SET_NULL,
                                              verbose_name=ugettext_lazy('price download scheme'))

    # TODO: what is notification_business_days
    notification_business_days = models.IntegerField(default=0)

    user_code_counters = ArrayField(models.IntegerField(null=True, blank=True), null=True, blank=True)

    token = models.CharField(unique=True, max_length=32, null=True, blank=True, verbose_name=ugettext_lazy('token'))

    objects = MasterUserManager()

    class Meta:
        verbose_name = ugettext_lazy('master user')
        verbose_name_plural = ugettext_lazy('master users')
        ordering = ['name']

    def __str__(self):
        return self.name

    def create_user_fields(self):

        from poms.ui.models import InstrumentUserFieldModel, TransactionUserFieldModel

        for i in range(20):
            num = str(i + 1)
            TransactionUserFieldModel.objects.create(master_user=self, key='user_text_' + num, name='User Text ' + num)

        for i in range(20):
            num = str(i + 1)
            TransactionUserFieldModel.objects.create(master_user=self, key='user_number_' + num,
                                                     name='User Number ' + num)

        for i in range(5):
            num = str(i + 1)
            TransactionUserFieldModel.objects.create(master_user=self, key='user_date_' + num, name='User Date ' + num)

        for i in range(3):
            num = str(i + 1)
            InstrumentUserFieldModel.objects.create(master_user=self, key='user_text_' + num, name='User Text ' + num)

    def create_entity_tooltips(self):

        from poms.ui.models import EntityTooltip

        entity_fields = [
            {
                "content_type": "instruments.instrument",
                "fields": [
                    {
                        "name": "User Code",
                        "key": "user_code"
                    },
                    {
                        "name": "Name",
                        "key": "name"
                    },
                    {
                        "name": "Short Name",
                        "key": "short_name"
                    },
                    {
                        "name": "Public Name",
                        "key": "public_name"
                    },
                    {
                        "name": "Notes",
                        "key": "notes"
                    },
                    {
                        "name": "Instrument Tye",
                        "key": "instrument_type"
                    },
                    {
                        "name": "Is Active",
                        "key": "is_active"
                    },
                    {
                        "name": "Reference for Pricing",
                        "key": "reference_for_pricing"
                    },
                    {
                        "name": "Maturity Date",
                        "key": "maturity_date"
                    },
                    {
                        "name": "Default Price",
                        "key": "default_price"
                    },
                    {
                        "name": "Default Accrued",
                        "key": "default_accrued"
                    },
                    {
                        "name": "Pricing Currency",
                        "key": "pricing_currency"
                    },
                    {
                        "name": "Accrued Currency",
                        "key": "accrued_currency"
                    },
                    {
                        "name": "Pricing Condition",
                        "key": "pricing_condition"
                    },
                    {
                        "name": "Price Multiplier",
                        "key": "price_multiplier"
                    },
                    {
                        "name": "Accrued Multiplier",
                        "key": "accrued_multiplier"
                    },
                    {
                        "name": "Payment Size Detail",
                        "key": "payment_size_detail"
                    },
                    {
                        "name": "Maturity Price",
                        "key": "maturity_price"
                    },
                    {
                        "name": "User Text 1",
                        "key": "user_text_1"
                    },
                    {
                        "name": "User Text 2",
                        "key": "user_text_2"
                    },
                    {
                        "name": "User Text 3",
                        "key": "user_text_3"
                    },
                ]
            },
            {
                "content_type": "instruments.instrumenttype",
                "fields": [
                    {
                        "name": "User Code",
                        "key": "user_code"
                    },
                    {
                        "name": "Name",
                        "key": "name"
                    },
                    {
                        "name": "Short Name",
                        "key": "short_name"
                    },
                    {
                        "name": "Public Name",
                        "key": "public_name"
                    },
                    {
                        "name": "Notes",
                        "key": "notes"
                    },
                    {
                        "name": "Factor Down",
                        "key": "factor_down"
                    },
                    {
                        "name": "Factor Same",
                        "key": "factor_same"
                    },
                    {
                        "name": "Factor Up",
                        "key": "factor_up"
                    },
                    {
                        "name": "Instrument Class",
                        "key": "instrument_class"
                    },
                    {
                        "name": "One Off Event",
                        "key": "one_off_event"
                    },
                    {
                        "name": "Regular Event",
                        "key": "regular_event"
                    }
                ]
            },
            {
                "content_type": "portfolios.portfolio",
                "fields": [
                    {
                        "name": "User Code",
                        "key": "user_code"
                    },
                    {
                        "name": "Name",
                        "key": "name"
                    },
                    {
                        "name": "Short Name",
                        "key": "short_name"
                    },
                    {
                        "name": "Public Name",
                        "key": "public_name"
                    },
                    {
                        "name": "Notes",
                        "key": "notes"
                    }
                ]
            },
            {
                "content_type": "accounts.account",
                "fields": [
                    {
                        "name": "User Code",
                        "key": "user_code"
                    },
                    {
                        "name": "Name",
                        "key": "name"
                    },
                    {
                        "name": "Short Name",
                        "key": "short_name"
                    },
                    {
                        "name": "Public Name",
                        "key": "public_name"
                    },
                    {
                        "name": "Notes",
                        "key": "notes"
                    },
                    {
                        "name": "Type",
                        "key": "type"
                    },
                ]
            },
            {
                "content_type": "accounts.accounttype",
                "fields": [
                    {
                        "name": "User Code",
                        "key": "user_code"
                    },
                    {
                        "name": "Name",
                        "key": "name"
                    },
                    {
                        "name": "Short Name",
                        "key": "short_name"
                    },
                    {
                        "name": "Public Name",
                        "key": "public_name"
                    },
                    {
                        "name": "Notes",
                        "key": "notes"
                    },
                    {
                        "name": "Transaction Details Expression",
                        "key": "transaction_details_expr"
                    },
                    {
                        "name": "Show Transaction Details",
                        "key": "show_transaction_details"
                    }
                ]
            },
            {
                "content_type": "counterparties.responsible",
                "fields": [
                    {
                        "name": "User Code",
                        "key": "user_code"
                    },
                    {
                        "name": "Name",
                        "key": "name"
                    },
                    {
                        "name": "Short Name",
                        "key": "short_name"
                    },
                    {
                        "name": "Public Name",
                        "key": "public_name"
                    },
                    {
                        "name": "Group",
                        "key": "group"
                    }
                ]
            },
            {
                "content_type": "counterparties.counterparty",
                "fields": [
                    {
                        "name": "User Code",
                        "key": "user_code"
                    },
                    {
                        "name": "Name",
                        "key": "name"
                    },
                    {
                        "name": "Short Name",
                        "key": "short_name"
                    },
                    {
                        "name": "Public Name",
                        "key": "public_name"
                    },
                    {
                        "name": "Notes",
                        "key": "notes"
                    },
                    {
                        "name": "Group",
                        "key": "group"
                    }
                ]
            },
            {
                "content_type": "strategies.strategy1",
                "fields": [
                    {
                        "name": "User Code",
                        "key": "user_code"
                    },
                    {
                        "name": "Name",
                        "key": "name"
                    },
                    {
                        "name": "Short Name",
                        "key": "short_name"
                    },
                    {
                        "name": "Public Name",
                        "key": "public_name"
                    },
                    {
                        "name": "Notes",
                        "key": "notes"
                    },
                    {
                        "name": "Group",
                        "key": "subgroup"
                    }
                ]
            },
            {
                "content_type": "strategies.strategy2",
                "fields": [
                    {
                        "name": "User Code",
                        "key": "user_code"
                    },
                    {
                        "name": "Name",
                        "key": "name"
                    },
                    {
                        "name": "Short Name",
                        "key": "short_name"
                    },
                    {
                        "name": "Public Name",
                        "key": "public_name"
                    },
                    {
                        "name": "Notes",
                        "key": "notes"
                    },
                    {
                        "name": "Group",
                        "key": "subgroup"
                    }
                ]
            },
            {
                "content_type": "strategies.strategy3",
                "fields": [
                    {
                        "name": "User Code",
                        "key": "user_code"
                    },
                    {
                        "name": "Name",
                        "key": "name"
                    },
                    {
                        "name": "Short Name",
                        "key": "short_name"
                    },
                    {
                        "name": "Public Name",
                        "key": "public_name"
                    },
                    {
                        "name": "Notes",
                        "key": "notes"
                    },
                    {
                        "name": "Group",
                        "key": "subgroup"
                    }

                ]
            },
            {
                "content_type": "currencies.currency",
                "fields": [
                    {
                        "name": "User Code",
                        "key": "user_code"
                    },
                    {
                        "name": "Name",
                        "key": "name"
                    },
                    {
                        "name": "Short Name",
                        "key": "short_name"
                    },
                    {
                        "name": "Public Name",
                        "key": "public_name"
                    },
                    {
                        "name": "Notes",
                        "key": "notes"
                    },
                    {
                        "name": "Default FX Rate",
                        "key": "default_fx_rate"
                    },
                    {
                        "name": "Reference For Pricing",
                        "key": "reference_for_pricing"
                    }
                ]
            },
            {
                "content_type": "instruments.pricehistory",
                "fields": [
                    {
                        "name": "Instrument",
                        "key": "instrument"
                    },
                    {
                        "name": "Date",
                        "key": "date"
                    },
                    {
                        "name": "Pricing Policy",
                        "key": "pricing_policy"
                    },
                    {
                        "name": "Principal Price",
                        "key": "principal_price"
                    },
                    {
                        "name": "Accrued Price",
                        "key": "accrued_price"
                    },
                ]
            },
            {
                "content_type": "currencies.currencyhistory",
                "fields": [
                    {
                        "name": "Currency",
                        "key": "currency"
                    },
                    {
                        "name": "Date",
                        "key": "date"
                    },
                    {
                        "name": "Pricing Policy",
                        "key": "pricing_policy"
                    },
                    {
                        "name": "FX Rate",
                        "key": "fx_rate"
                    },
                ]
            }
        ]

        for entity in entity_fields:

            content_type = get_content_type_by_name(entity['content_type'])

            for field in entity["fields"]:

                try:

                    item = EntityTooltip.objects.get(master_user=self, key=field["key"], content_type=content_type)

                    item.name = field["name"]
                    item.save()

                except EntityTooltip.DoesNotExist:

                    item = EntityTooltip.objects.create(master_user=self, name=field["name"], key=field["key"], content_type=content_type)
                    item.save()



    def create_defaults(self, user=None):
        from poms.currencies.models import currencies_data, Currency
        from poms.accounts.models import AccountType, Account
        from poms.counterparties.models import Counterparty, CounterpartyGroup, Responsible, ResponsibleGroup
        from poms.portfolios.models import Portfolio
        from poms.instruments.models import InstrumentClass, InstrumentType, EventScheduleConfig, Instrument, \
            DailyPricingModel, AccrualCalculationModel, PaymentSizeDetail, Periodicity
        from poms.integrations.models import PricingAutomatedSchedule, CurrencyMapping, ProviderClass
        from poms.strategies.models import Strategy1Group, Strategy1Subgroup, Strategy1, Strategy2Group, \
            Strategy2Subgroup, Strategy2, Strategy3Group, Strategy3Subgroup, Strategy3
        from poms.chats.models import ThreadGroup
        from poms.transactions.models import NotificationClass, TransactionTypeGroup, TransactionType
        from poms.obj_perms.utils import get_change_perms, assign_perms3
        from poms.instruments.models import PricingPolicy
        from poms.integrations.models import PriceDownloadScheme

        if not EventScheduleConfig.objects.filter(master_user=self).exists():
            EventScheduleConfig.create_default(master_user=self)

        if not PricingAutomatedSchedule.objects.filter(master_user=self).exists():
            PricingAutomatedSchedule.objects.create(master_user=self, is_enabled=False)

        price_download_scheme = PriceDownloadScheme.objects.create(master_user=self, scheme_name='-',
                                                                   provider=ProviderClass.objects.get(
                                                                       pk=ProviderClass.BLOOMBERG))

        ccys = {}
        ccy = Currency.objects.create(master_user=self, name='-', user_code='-')
        ccy_usd = None
        for dc in currencies_data.values():

            print('dc %s ' % dc)

            dc_user_code = dc['user_code']
            dc_name = dc.get('name', dc_user_code)
            # dc_reference_for_pricing = dc.get('reference_for_pricing', None)
            dc_reference_for_pricing = ''
            price_download_scheme = PriceDownloadScheme.objects.get(scheme_name='-', master_user=self)

            if dc_user_code == '-':
                pass
            else:

                if dc_user_code == 'USD':
                    c = Currency.objects.create(master_user=self, user_code=dc_user_code, short_name=dc_user_code,
                                                name=dc_name, daily_pricing_model=DailyPricingModel.objects.get(
                            pk=DailyPricingModel.SKIP), price_download_scheme=price_download_scheme,
                                                reference_for_pricing=dc_reference_for_pricing)
                    ccy_usd = c
                else:
                    c = Currency.objects.create(master_user=self, user_code=dc_user_code, short_name=dc_user_code,
                                                name=dc_name, daily_pricing_model=DailyPricingModel.objects.get(
                            pk=DailyPricingModel.DEFAULT), price_download_scheme=price_download_scheme,
                                                reference_for_pricing=dc_reference_for_pricing)
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

        transaction_type = TransactionType.objects.create(master_user=self, name='-')
        transaction_type_group = TransactionTypeGroup.objects.create(master_user=self, name='-')

        pricing_policy = PricingPolicy.objects.create(master_user=self, name='-', expr='(ask+bid)/2')
        pricing_policy_dft = PricingPolicy.objects.create(master_user=self, name='DFT', expr='(ask+bid)/2')

        bloomberg = ProviderClass.objects.get(pk=ProviderClass.BLOOMBERG)
        # for dc in currencies_data.values():
        #     dc_user_code = dc['user_code']
        #     dc_bloomberg = dc['bloomberg']
        #
        #     if dc_user_code != '-' and dc_user_code in ccys:
        #         c = ccys[dc_user_code]
        #         CurrencyMapping.objects.create(master_user=self, provider=bloomberg, value=dc_bloomberg,
        #                                        content_object=c)

        # TODO refactor later, that thing used in report logic,
        # TODO so, someday we need to change it to take defaults from EcosystemDefault
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
        self.pricing_policy = pricing_policy
        self.transaction_type = transaction_type
        self.price_download_scheme = price_download_scheme

        ecosystem_defaults = EcosystemDefault()

        ecosystem_defaults.master_user = self
        ecosystem_defaults.currency = ccy
        ecosystem_defaults.account_type = account_type
        ecosystem_defaults.account = account
        ecosystem_defaults.counterparty_group = counterparty_group
        ecosystem_defaults.counterparty = counterparty
        ecosystem_defaults.responsible_group = responsible_group
        ecosystem_defaults.responsible = responsible
        ecosystem_defaults.portfolio = portfolio
        ecosystem_defaults.instrument_type = instrument_type
        ecosystem_defaults.instrument = instrument
        ecosystem_defaults.strategy1_group = strategy1_group
        ecosystem_defaults.strategy1_subgroup = strategy1_subgroup
        ecosystem_defaults.strategy1 = strategy1
        ecosystem_defaults.strategy2_group = strategy2_group
        ecosystem_defaults.strategy2_subgroup = strategy2_subgroup
        ecosystem_defaults.strategy2 = strategy2
        ecosystem_defaults.strategy3_group = strategy3_group
        ecosystem_defaults.strategy3_subgroup = strategy3_subgroup
        ecosystem_defaults.strategy3 = strategy3
        ecosystem_defaults.thread_group = thread_group
        ecosystem_defaults.transaction_type_group = transaction_type_group
        ecosystem_defaults.mismatch_portfolio = portfolio
        ecosystem_defaults.mismatch_account = account
        ecosystem_defaults.pricing_policy = pricing_policy
        ecosystem_defaults.transaction_type = transaction_type
        ecosystem_defaults.price_download_scheme = price_download_scheme

        ecosystem_defaults.instrument_class = InstrumentClass.objects.get(pk=InstrumentClass.DEFAULT)
        ecosystem_defaults.daily_pricing_model = DailyPricingModel.objects.get(pk=DailyPricingModel.DEFAULT)
        ecosystem_defaults.accrual_calculation_model = AccrualCalculationModel.objects.get(
            pk=AccrualCalculationModel.DEFAULT)
        ecosystem_defaults.payment_size_detail = PaymentSizeDetail.objects.get(pk=PaymentSizeDetail.DEFAULT)
        ecosystem_defaults.periodicity = Periodicity.objects.get(pk=Periodicity.DEFAULT)

        ecosystem_defaults.save()

        self.create_user_fields()
        self.create_entity_tooltips()

        group = Group.objects.create(master_user=self, name='%s' % ugettext_lazy('Administrators'), role=Group.ADMIN)
        group.grant_all_permissions_to_public_group(group, master_user=self)

        group = Group.objects.create(master_user=self, name='%s' % ugettext_lazy('Guests'), role=Group.USER)

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

                c = Currency.objects.create(master_user=self, user_code=dc_user_code, name=dc_name,
                                            short_name=dc_user_code,
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


class EcosystemDefault(models.Model):
    master_user = models.ForeignKey(MasterUser, related_name='ecosystem_default',
                                    verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE,)

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

                                        verbose_name=ugettext_lazy('strategy1 group'))
    strategy1_subgroup = models.ForeignKey('strategies.Strategy1Subgroup', null=True, blank=True,
                                           on_delete=models.PROTECT,
                                           verbose_name=ugettext_lazy('strategy1 subgroup'))
    strategy1 = models.ForeignKey('strategies.Strategy1', null=True, blank=True, on_delete=models.PROTECT,
                                  verbose_name=ugettext_lazy('strategy1'))

    strategy2_group = models.ForeignKey('strategies.Strategy2Group', null=True, blank=True, on_delete=models.PROTECT,
                                        verbose_name=ugettext_lazy('strategy2 group'))
    strategy2_subgroup = models.ForeignKey('strategies.Strategy2Subgroup', null=True, blank=True,
                                           on_delete=models.PROTECT,
                                           verbose_name=ugettext_lazy('strategy2 subgroup'))
    strategy2 = models.ForeignKey('strategies.Strategy2', null=True, blank=True, on_delete=models.PROTECT,
                                  verbose_name=ugettext_lazy('strategy2'))

    strategy3_group = models.ForeignKey('strategies.Strategy3Group', null=True, blank=True, on_delete=models.PROTECT,
                                        verbose_name=ugettext_lazy('strategy3 group'))
    strategy3_subgroup = models.ForeignKey('strategies.Strategy3Subgroup', null=True, blank=True,
                                           on_delete=models.PROTECT,
                                           verbose_name=ugettext_lazy('strategy3 subgroup'))
    strategy3 = models.ForeignKey('strategies.Strategy3', null=True, blank=True, on_delete=models.PROTECT,
                                  verbose_name=ugettext_lazy('strategy3'))

    thread_group = models.ForeignKey('chats.ThreadGroup', null=True, blank=True, on_delete=models.PROTECT,
                                     verbose_name=ugettext_lazy('thread group'))

    transaction_type = models.ForeignKey('transactions.TransactionType', null=True, blank=True,
                                         on_delete=models.PROTECT,
                                         verbose_name=ugettext_lazy('transaction type'))

    transaction_type_group = models.ForeignKey('transactions.TransactionTypeGroup', null=True, blank=True,
                                               on_delete=models.PROTECT,
                                               verbose_name=ugettext_lazy('transaction type group'))

    mismatch_portfolio = models.ForeignKey('portfolios.Portfolio', null=True, blank=True, on_delete=models.PROTECT,
                                           related_name='ecosystem_default_mismatch_portfolio',
                                           verbose_name=ugettext_lazy('mismatch portfolio'))
    mismatch_account = models.ForeignKey('accounts.Account', null=True, blank=True, on_delete=models.PROTECT,
                                         related_name='ecosystem_default_mismatch_account',
                                         verbose_name=ugettext_lazy('mismatch account'))

    pricing_policy = models.ForeignKey('instruments.PricingPolicy', null=True, blank=True, on_delete=models.PROTECT,
                                       verbose_name=ugettext_lazy('pricing policy'))

    price_download_scheme = models.ForeignKey('integrations.PriceDownloadScheme', null=True, blank=True,
                                              on_delete=models.PROTECT,
                                              verbose_name=ugettext_lazy('price download scheme'))

    instrument_class = models.ForeignKey('instruments.InstrumentClass', null=True, blank=True,
                                         on_delete=models.PROTECT,
                                         verbose_name=ugettext_lazy('instrument class'))

    daily_pricing_model = models.ForeignKey('instruments.DailyPricingModel', null=True, blank=True,
                                            on_delete=models.PROTECT,
                                            verbose_name=ugettext_lazy('daily pricing model'))

    accrual_calculation_model = models.ForeignKey('instruments.AccrualCalculationModel', null=True, blank=True,
                                                  on_delete=models.PROTECT,
                                                  verbose_name=ugettext_lazy('accrual calculation model'))

    payment_size_detail = models.ForeignKey('instruments.PaymentSizeDetail', null=True, blank=True,
                                            on_delete=models.PROTECT,
                                            verbose_name=ugettext_lazy('payment size detail'))

    periodicity = models.ForeignKey('instruments.Periodicity', null=True, blank=True,
                                    on_delete=models.PROTECT,
                                    verbose_name=ugettext_lazy('periodicity'))

    pricing_condition = models.ForeignKey('instruments.PricingCondition', null=True, blank=True,
                                            on_delete=models.PROTECT,
                                            verbose_name=ugettext_lazy('pricing condition'))


class Member(FakeDeletableModel):
    DO_NOT_NOTIFY = 1
    SHOW_AND_EMAIL = 2
    EMAIL_ONLY = 3
    SHOW_ONLY = 4
    STATUS_CHOICES = (
        (DO_NOT_NOTIFY, ugettext_lazy('Do not notify')),
        (SHOW_AND_EMAIL, ugettext_lazy('Show & Email notifications')),
        (EMAIL_ONLY, ugettext_lazy('Email notifications')),
        (SHOW_ONLY, ugettext_lazy('Show notifications')),
    )

    master_user = models.ForeignKey(MasterUser, related_name='members', verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='members', verbose_name=ugettext_lazy('user'))

    username = models.CharField(max_length=255, blank=True, default='', editable=False,
                                verbose_name=ugettext_lazy('username'))
    first_name = models.CharField(max_length=30, blank=True, default='', editable=False,
                                  verbose_name=ugettext_lazy('first name'))
    last_name = models.CharField(max_length=30, blank=True, default='', editable=False,
                                 verbose_name=ugettext_lazy('last name'))
    email = models.EmailField(blank=True, default='', editable=False, verbose_name=ugettext_lazy('email'))

    notification_level = models.PositiveSmallIntegerField(default=SHOW_ONLY, choices=STATUS_CHOICES, db_index=True,
                                                          verbose_name=ugettext_lazy('notification level'))

    interface_level = models.PositiveSmallIntegerField(default=20, db_index=True,
                                                       verbose_name=ugettext_lazy('interface level'))

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

class OtpToken(models.Model):

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='otp_tokens', verbose_name=ugettext_lazy('OTP Token'))

    name = models.CharField(max_length=80, verbose_name=ugettext_lazy('name'))

    secret = models.CharField(max_length=16, blank=True, default='', editable=False,
                                verbose_name=ugettext_lazy('secret'))


class InviteToMasterUser(models.Model):

    SENT = 0
    ACCEPTED = 1
    DECLINED = 2

    STATUS_CHOICES = ((SENT, 'Sent'),
               (ACCEPTED, 'Accepted'),
               (DECLINED, 'Declined'),
               )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='invites_to_master_user', verbose_name=ugettext_lazy('user'), on_delete=models.CASCADE)
    from_member = models.ForeignKey(Member, related_name="invites_to_users",
                                    verbose_name=ugettext_lazy('from_member'), on_delete=models.CASCADE)

    master_user = models.ForeignKey(MasterUser, related_name='invites_to_users', verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE)

    groups = models.ManyToManyField('Group', blank=True, related_name='invites', verbose_name=ugettext_lazy('groups'))

    status = models.IntegerField(default=0, choices=STATUS_CHOICES)

    class Meta:
        verbose_name = ugettext_lazy('invite to master user')
        verbose_name_plural = ugettext_lazy('invites to master user')

        unique_together = [
            ['user', 'master_user']
        ]

    def __str__(self):
        return 'status: %s' % self.status


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='profile',
                                verbose_name=ugettext_lazy('user'), on_delete=models.CASCADE)
    language = models.CharField(max_length=LANGUAGE_MAX_LENGTH, default=settings.LANGUAGE_CODE,
                                verbose_name=ugettext_lazy('language'))
    timezone = models.CharField(max_length=TIMEZONE_MAX_LENGTH, default=settings.TIME_ZONE,
                                verbose_name=ugettext_lazy('timezone'))

    two_factor_verification = models.BooleanField(default=False, verbose_name=ugettext_lazy('two factor verification'))

    class Meta:
        verbose_name = ugettext_lazy('profile')
        verbose_name_plural = ugettext_lazy('profiles')

    def __str__(self):
        return self.user.username


class Group(models.Model):

    ADMIN = 1
    USER = 2

    # Only used in determine who can manage groups and users
    # If user has is_admin: True he will see everything anyway

    ROLE_CHOICES = (
        (ADMIN, ugettext_lazy('Admin')),
        (USER, ugettext_lazy('User')),
    )

    master_user = models.ForeignKey(MasterUser, related_name='groups', verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE )
    name = models.CharField(max_length=80, verbose_name=ugettext_lazy('name'))

    role = models.PositiveSmallIntegerField(default=USER, choices=ROLE_CHOICES, db_index=True,
                                                         verbose_name=ugettext_lazy('role'))

    permission_table_json_data = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('json data'))

    @property
    def permission_table(self):
        if self.permission_table_json_data:
            try:
                return json.loads(self.permission_table_json_data)
            except (ValueError, TypeError):
                return None
        else:
            return None

    @permission_table.setter
    def permission_table(self, val):
        if val:
            self.permission_table_json_data = json.dumps(val, cls=DjangoJSONEncoder, sort_keys=True)
        else:
            self.permission_table_json_data = None

    class Meta:
        verbose_name = ugettext_lazy('group')
        verbose_name_plural = ugettext_lazy('groups')
        unique_together = [
            ['master_user', 'name']
        ]
        ordering = ['name']

    def __str__(self):
        return self.name

    def grant_all_permissions_to_model_objects(self, model, master_user, group):

        from poms.obj_perms.utils import get_view_perms, append_perms3, get_all_perms

        for item in model.objects.filter(master_user=master_user):

            perms = []

            for p in get_all_perms(item):

                perms.append({'group': group, 'permission': p})

            append_perms3(item, perms=perms)

    def grant_view_permissions_to_model_objects(self, model, master_user, group):

        from poms.obj_perms.utils import get_view_perms, append_perms3, get_all_perms

        for item in model.objects.filter(master_user=master_user):

            perms = []

            for p in get_view_perms(item):

                perms.append({'group': group, 'permission': p})

            append_perms3(item, perms=perms)

    def grant_all_permissions_to_public_group(self, instance, master_user):

        from poms.accounts.models import Account, AccountType
        from poms.chats.models import ThreadGroup, Thread
        from poms.counterparties.models import CounterpartyGroup, Counterparty, ResponsibleGroup, Responsible
        from poms.instruments.models import InstrumentType, Instrument
        from poms.obj_attrs.models import GenericAttributeType
        from poms.portfolios.models import Portfolio
        from poms.strategies.models import Strategy1Group, Strategy1Subgroup, Strategy1, Strategy2Group, Strategy2Subgroup, \
            Strategy2, Strategy3Group, Strategy3Subgroup, Strategy3
        from poms.transactions.models import TransactionTypeGroup, TransactionType, ComplexTransaction, Transaction

        self.grant_all_permissions_to_model_objects(Account, master_user, instance)
        self.grant_all_permissions_to_model_objects(AccountType, master_user, instance)

        self.grant_all_permissions_to_model_objects(Strategy1Group, master_user, instance)
        self.grant_all_permissions_to_model_objects(Strategy1Subgroup, master_user, instance)
        self.grant_all_permissions_to_model_objects(Strategy1, master_user, instance)

        self.grant_all_permissions_to_model_objects(Strategy2Group, master_user, instance)
        self.grant_all_permissions_to_model_objects(Strategy2Subgroup, master_user, instance)
        self.grant_all_permissions_to_model_objects(Strategy2, master_user, instance)

        self.grant_all_permissions_to_model_objects(Strategy3Group, master_user, instance)
        self.grant_all_permissions_to_model_objects(Strategy3Subgroup, master_user, instance)
        self.grant_all_permissions_to_model_objects(Strategy3, master_user, instance)

        self.grant_all_permissions_to_model_objects(GenericAttributeType, master_user, instance)

        self.grant_all_permissions_to_model_objects(InstrumentType, master_user, instance)
        self.grant_all_permissions_to_model_objects(Instrument, master_user, instance)

        self.grant_all_permissions_to_model_objects(TransactionTypeGroup, master_user, instance)
        self.grant_all_permissions_to_model_objects(TransactionType, master_user, instance)

        self.grant_all_permissions_to_model_objects(ThreadGroup, master_user, instance)
        self.grant_all_permissions_to_model_objects(Thread, master_user, instance)

        self.grant_all_permissions_to_model_objects(Portfolio, master_user, instance)

        self.grant_all_permissions_to_model_objects(CounterpartyGroup, master_user, instance)
        self.grant_all_permissions_to_model_objects(Counterparty, master_user, instance)

        self.grant_all_permissions_to_model_objects(ResponsibleGroup, master_user, instance)
        self.grant_all_permissions_to_model_objects(Responsible, master_user, instance)

        self.grant_all_permissions_to_model_objects(ComplexTransaction, master_user, instance)
        self.grant_view_permissions_to_model_objects(Transaction, master_user, instance)



class FakeSequence(models.Model):
    master_user = models.ForeignKey(MasterUser, related_name='fake_sequences',
                                    verbose_name=ugettext_lazy('master user'),on_delete=models.CASCADE )
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
