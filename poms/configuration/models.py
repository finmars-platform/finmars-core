import json
import logging

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.translation import gettext_lazy

from poms.configuration.utils import replace_special_chars_and_spaces

_l = logging.getLogger('poms.configuration')


class ConfigurationModel(models.Model):
    '''
    just a good remainder to find entity by configuration_code
    '''
    configuration_code = models.CharField(max_length=255,
                                          default='com.finmars.local',
                                          verbose_name=gettext_lazy('Configuration Code'))
    # TODO someday make it  unique=True,
    user_code = models.CharField(max_length=1024, null=True, blank=True, verbose_name=gettext_lazy('User Code'))

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

        _l.info('self.configuration_code %s' % self.configuration_code)
        _l.info('self.user_code %s' % self.user_code)

        # TODO  ADD configuration_code to POST data
        if self.user_code and self.configuration_code not in self.user_code:

            self.user_code = replace_special_chars_and_spaces(self.user_code).lower()

            if hasattr(self, 'content_type') and self.content_type:  # In case if it Attribute Type or Layout

                content_type_key = self.content_type.app_label + '.' + self.content_type.model

                self.user_code = str(self.configuration_code) + ':' + content_type_key + ':' + str(self.user_code)

            else:

                self.user_code = str(self.configuration_code) + ':' + str(self.user_code)

        super(ConfigurationModel, self).save(*args, **kwargs)


class Configuration(models.Model):
    # com.finmars.hnwi
    configuration_code = models.CharField(max_length=255, null=True, blank=True,
                                          verbose_name=gettext_lazy('configuration code'))
    # High New Worth Individual
    name = models.CharField(max_length=255, verbose_name=gettext_lazy('name'))
    short_name = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('short name'))
    description = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('notes'))
    version = models.CharField(max_length=255, verbose_name=gettext_lazy('version'))

    is_from_marketplace = models.BooleanField(default=False, verbose_name=gettext_lazy('is from marketplace'))
    is_package = models.BooleanField(default=False, verbose_name=gettext_lazy('is package'))

    manifest_data = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('manifest_data'))

    @property
    def manifest(self):
        if self.manifest_data is None:
            return None
        return json.loads(self.manifest_data)

    @manifest.setter
    def manifest(self, value):
        if value is None:
            self.manifest_data = None
        else:
            self.manifest_data = json.dumps(value, cls=DjangoJSONEncoder, sort_keys=True, indent=1)

    def __str__(self):
        return '%s (%s)' % (self.configuration_code, self.version)


class NewMemberSetupConfiguration(ConfigurationModel):
    user_code = models.CharField(max_length=1024, null=True, blank=True, verbose_name=gettext_lazy('user code'),
                                 help_text=gettext_lazy(
                                     'Unique Code for this object. Used in Configuration and Permissions Logic'))
    name = models.CharField(max_length=255, verbose_name=gettext_lazy('name'),
                            help_text="Human Readable Name of the object")
    short_name = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('short name'),
                                  help_text="Short Name of the object. Used in dropdown menus")
    public_name = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('public name'),
                                   help_text=gettext_lazy('Used if user does not have permissions to view object'))
    notes = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('notes'),
                             help_text="Notes, any useful information about the object")

    '''
    Either provide configuration_code with version or upload zip
    '''
    target_configuration_code = models.CharField(max_length=255, null=True, blank=True)
    target_configuration_version = models.CharField(max_length=255, null=True, blank=True)
    target_configuration_is_package = models.BooleanField(default=False)
    file_url = models.TextField(blank=True, default='', verbose_name=gettext_lazy('File URL'))
    file_name = models.CharField(max_length=255, blank=True, default='')
