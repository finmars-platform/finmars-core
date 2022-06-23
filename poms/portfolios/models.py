from __future__ import unicode_literals

from datetime import timedelta

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils.translation import ugettext_lazy
from django.contrib.postgres.fields import JSONField

from poms.common.models import NamedModel, FakeDeletableModel, DataTimeStampedModel
from poms.common.utils import date_now
from poms.common.wrapper_models import NamedModelAutoMapping
from poms.currencies.models import Currency
from poms.instruments.models import PricingPolicy, Instrument, PriceHistory
from poms.obj_attrs.models import GenericAttribute
from poms.obj_perms.models import GenericObjectPermission
from poms.tags.models import TagLink
from poms.users.models import MasterUser


class Portfolio(NamedModelAutoMapping, FakeDeletableModel, DataTimeStampedModel):
    master_user = models.ForeignKey(MasterUser, related_name='portfolios', verbose_name=ugettext_lazy('master user'),
                                    on_delete=models.CASCADE)
    accounts = models.ManyToManyField('accounts.Account', related_name='portfolios', blank=True,
                                      verbose_name=ugettext_lazy('accounts'))
    responsibles = models.ManyToManyField('counterparties.Responsible', related_name='portfolios', blank=True,
                                          verbose_name=ugettext_lazy('responsibles'))
    counterparties = models.ManyToManyField('counterparties.Counterparty', related_name='portfolios', blank=True,
                                            verbose_name=ugettext_lazy('counterparties'))
    transaction_types = models.ManyToManyField('transactions.TransactionType', related_name='portfolios', blank=True,
                                               verbose_name=ugettext_lazy('transaction types'))

    default_price = models.FloatField(default=100.0, verbose_name=ugettext_lazy('default price'))

    attributes = GenericRelation(GenericAttribute, verbose_name=ugettext_lazy('attributes'))
    object_permissions = GenericRelation(GenericObjectPermission, verbose_name=ugettext_lazy('object permissions'))
    tags = GenericRelation(TagLink, verbose_name=ugettext_lazy('tags'))
    attrs = JSONField(blank=True, null=True)

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = ugettext_lazy('portfolio')
        verbose_name_plural = ugettext_lazy('portfolios')
        permissions = (
            # ('view_portfolio', 'Can view portfolio'),
            ('manage_portfolio', 'Can manage portfolio'),
        )

    @property
    def is_default(self):
        return self.master_user.portfolio_id == self.id if self.master_user_id else False


class PortfolioRegister(NamedModel, FakeDeletableModel, DataTimeStampedModel):
    master_user = models.ForeignKey(MasterUser, related_name='portfolio_registers',
                                    verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE)

    portfolio = models.ForeignKey(Portfolio,
                                  verbose_name=ugettext_lazy('portfolio'), on_delete=models.CASCADE)

    linked_instrument = models.ForeignKey(Instrument,
                                          verbose_name=ugettext_lazy('linked instrument'), on_delete=models.CASCADE)

    valuation_pricing_policy = models.ForeignKey(PricingPolicy, on_delete=models.CASCADE, null=True, blank=True,
                                                 verbose_name=ugettext_lazy('pricing policy'))

    valuation_currency = models.ForeignKey('currencies.Currency',
                                           on_delete=models.PROTECT, verbose_name=ugettext_lazy('valuation currency'))

    attributes = GenericRelation(GenericAttribute, verbose_name=ugettext_lazy('attributes'))
    object_permissions = GenericRelation(GenericObjectPermission, verbose_name=ugettext_lazy('object permissions'))

    class Meta(NamedModel.Meta, FakeDeletableModel.Meta):
        verbose_name = ugettext_lazy('portfolio register')
        verbose_name_plural = ugettext_lazy('portfolio registers')

    def save(self, *args, **kwargs):
        super(PortfolioRegister, self).save(*args, **kwargs)

        if self.linked_instrument:
            self.linked_instrument.has_linked_with_portfolio = True
            self.linked_instrument.save()


class PortfolioRegisterRecord(DataTimeStampedModel):
    master_user = models.ForeignKey(MasterUser, related_name='portfolio_register_records',
                                    verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE)

    portfolio = models.ForeignKey(Portfolio,
                                  verbose_name=ugettext_lazy('portfolio'), on_delete=models.CASCADE)

    instrument = models.ForeignKey(Instrument,
                                   verbose_name=ugettext_lazy('instrument'), on_delete=models.CASCADE)

    transaction_class = models.ForeignKey('transactions.TransactionClass',
                                            related_name="register_record_transaction_class",
                                            on_delete=models.CASCADE,
                                            verbose_name=ugettext_lazy('transaction class'))

    transaction_code = models.IntegerField(default=0, verbose_name=ugettext_lazy('transaction code'))

    transaction_date = models.DateField(default=date_now, db_index=True,
                                        verbose_name=ugettext_lazy("transaction date"))

    cash_amount = models.FloatField(default=0.0, verbose_name=ugettext_lazy("cash amount"),
                                    help_text=ugettext_lazy(
                                        'Cash amount'))

    cash_currency = models.ForeignKey(Currency, related_name='register_record_cash_currency',
                                      on_delete=models.PROTECT, verbose_name=ugettext_lazy("cash currency"))

    fx_rate = models.FloatField(default=0.0, verbose_name=ugettext_lazy("fx rate"))

    cash_amount_valuation_currency = models.FloatField(default=0.0,
                                                       verbose_name=ugettext_lazy("cash amount valuation currency"),
                                                       help_text=ugettext_lazy(
                                                           'Cash amount valuation currency'))

    valuation_currency = models.ForeignKey(Currency, related_name='register_record_valuation_currency',
                                           on_delete=models.PROTECT, verbose_name=ugettext_lazy("valuation currency"))

    nav_previous_day_valuation_currency = models.FloatField(default=0.0, verbose_name=ugettext_lazy(
        "nav previous day valuation currency"))

    n_shares_previous_day = models.FloatField(default=0.0, verbose_name=ugettext_lazy("n shares previous day"))
    n_shares_added = models.FloatField(default=0.0, verbose_name=ugettext_lazy("n shares added"))

    dealing_price_valuation_currency = models.FloatField(default=0.0,
                                                         verbose_name=ugettext_lazy("dealing price valuation currency"),
                                                         help_text=ugettext_lazy(
                                                             'Dealing price valuation currency'))

    # n_shares_end_of_the_day = models.FloatField(default=0.0, verbose_name=ugettext_lazy("n shares end of the day"))
    rolling_shares_of_the_day = models.FloatField(default=0.0, verbose_name=ugettext_lazy("rolling shares  of the day"))

    previous_date_record = models.ForeignKey('portfolios.PortfolioRegisterRecord', null=True, on_delete=models.SET_NULL,
                                    verbose_name=ugettext_lazy('previous date record'))

    transaction = models.ForeignKey('transactions.Transaction', on_delete=models.CASCADE,
                                    related_name="register_record_transaction",
                                    verbose_name=ugettext_lazy('transaction'))

    complex_transaction = models.ForeignKey('transactions.ComplexTransaction',
                                            related_name="register_record_complex_transaction",
                                            on_delete=models.CASCADE,
                                            verbose_name=ugettext_lazy('complex transaction'))

    portfolio_register = models.ForeignKey(PortfolioRegister, on_delete=models.CASCADE,
                                           verbose_name=ugettext_lazy('portfolio register'))

    object_permissions = GenericRelation(GenericObjectPermission, verbose_name=ugettext_lazy('object permissions'))

    class Meta:
        verbose_name = ugettext_lazy('portfolio register record')
        verbose_name_plural = ugettext_lazy('portfolio registers record')

    # def save(self, *args, **kwargs):
    #
    #     try:
    #
    #         previous = PortfolioRegisterRecord.objects.exclude(transaction_date=self.transaction_date).filter(
    #             portfolio_register=self.portfolio_register).order_by('-transaction_date')[0]
    #
    #         date = self.transaction_date - timedelta(days=1)
    #
    #         price_history = None
    #         try:
    #             price_history = PriceHistory.objecst.get(instrument=self.instrument, date=date)
    #         except Exception as e:
    #             price_history = PriceHistory.objecst.create(instrument=self.instrument, date=date)
    #
    #
    #         portfolio_share_price =  price_history.nav / previous.n_shares_end_of_the_day
    #         nav = 123
    #
    #         price_history.portfolio_share_price = portfolio_share_price
    #         price_history.nav = nav
    #
    #         price_history.save()
    #
    #         self.dealing_price_valuation_currency = portfolio_share_price
    #
    #     except Exception as e:
    #
    #         # ROOT RECORD
    #
    #         self.dealing_price_valuation_currency = self.portfolio.default_price
    #
    #     super(PortfolioRegisterRecord, self).save(*args, **kwargs)
