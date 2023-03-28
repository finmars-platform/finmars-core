from django.db import models
from django.utils.translation import gettext_lazy


class ConfigurationModel(models.Model):

    '''
    just a good remainder to find entity by configuration_code
    '''
    configuration_code = models.CharField(max_length=255,
                                          default='com.finmars.local',
                                          verbose_name=gettext_lazy('configuration code'))

    user_code = models.CharField(max_length=510, null=True, blank=True, verbose_name=gettext_lazy('user code'))

    class Meta:
        abstract = True

    '''
    That is because we still need unique value e.g.
        
        - com.finmars.hnwi:buy_sell
        - com.finmars.asset_manager:buy_sell
        
        frn:finmars:backend:::transactions.transactiontype:com.finmars.local:*
        frn:finmars:backend:::transactions.transactiontype:com.finmars.hnwi:*
        
        in that case con.finmars.hnwi already a user_code
        and :* is user_code qualifier
        
    '''
    def save(self, *args, **kwargs):

        if self.configuration_code not in self.user_code:

            self.user_code = str(self.configuration_code) + ':' + str(self.user_code)

        super(ConfigurationModel, self).save(*args, **kwargs)


class Configuration(models.Model):
    # com.finmars.hnwi
    configuration_code = models.CharField(max_length=255, null=True, blank=True,
                                          verbose_name=gettext_lazy('configuration code'))
    # High New Worth Individual
    name = models.CharField(max_length=255, verbose_name=gettext_lazy('name'))
    short_name = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('short name'))
    notes = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('notes'))
    version = models.CharField(max_length=255, verbose_name=gettext_lazy('version'))
