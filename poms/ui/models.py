import json

from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.text import Truncator
from django.utils.translation import ugettext_lazy
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel

from poms.common.models import AbstractClassModel, NamedModel
from poms.configuration_sharing.models import SharedConfigurationFile
from poms.users.models import MasterUser, Member, Group


class PortalInterfaceAccessModel(AbstractClassModel):
    DATA_PORTFOLIO = 6
    DATA_ACCOUNT = 3
    DATA_INSTRUMENT = 3
    DATA_RESPONSIBLE = 2
    DATA_COUNTERPARTY = 2
    DATA_CURRENCY = 6
    DATA_STRATEGIES = 2
    DATA_TRANSACTION = 7
    DATA_PRICE_HISTORY = 7
    DATA_FX_HISTORY = 7
    DATA_SIMPLE_IMPORT = 8
    DATA_TRANSACTION_IMPORT = 8
    DATA_COMPLEX_IMPORT = 8
    DATA_INSTRUMENT_DOWNLOAD = 8
    DATA_PRICES_DOWNLOAD = 8

    REPORT_BALANCE = 2
    REPORT_PL = 2
    REPORT_TRANSACTION = 3
    REPORT_PERFORMANCE = 3
    REPORT_CASH_FLOW = 5
    REPORT_DASHBOARD = 1
    REPORT_EVENT = 1
    REPORT_BOOKMARK = 1
    REPORT_INSTRUMENT_AUDIT = 7
    REPORT_TRANSACTION_AUDIT = 7
    REPORT_BASE_TRANSACTION = 10
    REPORT_ACTIVITY_LOG = 5
    REPORT_FORUM = 1

    CONFIGURATION_ACCOUNT_TYPE = 8
    CONFIGURATION_INSTRUMENT_TYPE = 10
    CONFIGURATION_TRANSACTION_TYPE = 15
    CONFIGURATION_PRICING_POLICY = 13
    CONFIGURATION_PRICE_DOWNLOAD_SCHEME = 17
    CONFIGURATION_INSTRUMENT_DOWNLOAD_SCHEME = 17
    CONFIGURATION_AUTOMATED_PRICE_DOWNLOADS = 8
    CONFIGURATION_SIMPLE_IMPORT_SCHEME = 15
    CONFIGURATION_TRANSACTION_IMPORT_SCHEME = 18
    CONFIGURATION_COMPLEX_IMPORT_SCHEME = 18
    CONFIGURATION_MAPPING_TABLES = 15
    CONFIGURATION_USER_ATTRIBUTES = 8
    CONFIGURATION_ALIASES = 8
    CONFIGURATION_TEMPLATES = 15
    CONFIGURATION_REFERENCE_TABLE = 15

    SETTINGS_NOTIFICATION = 1
    SETTINGS_EXPORT_CONFIGURATION = 15
    SETTINGS_IMPORT_CONFIGURATION = 1
    SETTINGS_EXPORT_MAPPING = 18
    SETTINGS_IMPORT_MAPPING = 18
    SETTINGS_PROVIDER = 16
    SETTINGS_INIT_CONFIGURATION = 18
    SETTINGS_USERS_GROUPS_PERMISSION = 15
    SETTINGS_NEW_OBJECTS_PERMISSION = 15
    SETTINGS_TIMEZONE = 1
    SETTINGS_ECOSYSTEM_DEFAULT = 18

    ACCOUNT_SETTINGS = 1
    ACCOUNT_PERSONAL_DATA = 1
    ACCOUNT_ECOSYSTEM_MANAGEMENT = 1

    CLASSES = (
        (1, DATA_PORTFOLIO, 'data_portfolio', ugettext_lazy("Data layer: Portfolio")),
        (2, DATA_ACCOUNT, 'data_account', ugettext_lazy("Data layer: Account")),
        (3, DATA_INSTRUMENT, 'data_instrument', ugettext_lazy("Data layer: Instrument")),
        (4, DATA_RESPONSIBLE, 'data_responsible', ugettext_lazy("Data layer: Responsible")),
        (5, DATA_COUNTERPARTY, 'data_counterparty', ugettext_lazy("Data layer: Counterparty")),
        (6, DATA_CURRENCY, 'data_currency', ugettext_lazy("Data layer: Currency")),
        (7, DATA_STRATEGIES, 'data_strategies', ugettext_lazy("Data layer: Strategies")),
        (8, DATA_TRANSACTION, 'data_transaction', ugettext_lazy("Data layer: Transaction")),
        (9, DATA_PRICE_HISTORY, 'data_price_history', ugettext_lazy("Data layer: Price History")),
        (10, DATA_FX_HISTORY, 'data_fx_history', ugettext_lazy("Data layer: FX History")),
        (11, DATA_SIMPLE_IMPORT, 'data_simple_import', ugettext_lazy("Data layer: Simple Import")),
        (12, DATA_TRANSACTION_IMPORT, 'data_transaction_import', ugettext_lazy("Data layer: Transaction Import")),
        (13, DATA_COMPLEX_IMPORT, 'data_complex_import', ugettext_lazy("Data layer: Complex Import")),
        (14, DATA_INSTRUMENT_DOWNLOAD, 'data_instrument_download', ugettext_lazy("Data layer: Instrument Download")),
        (15, DATA_PRICES_DOWNLOAD, 'data_prices_download', ugettext_lazy("Data layer: Prices Download")),

        (1001, REPORT_BALANCE, 'report_balance', ugettext_lazy("Reporting layer: Balance Report")),
        (1002, REPORT_PL, 'report_pl', ugettext_lazy("Reporting layer: P&L Report")),
        (1003, REPORT_TRANSACTION, 'report_transaction', ugettext_lazy("Reporting layer: Transaction Report")),
        (1004, REPORT_PERFORMANCE, 'report_performance', ugettext_lazy("Reporting layer: Performance Report")),
        (1005, REPORT_CASH_FLOW, 'report_cash_flow', ugettext_lazy("Reporting layer: Cash Flow Report")),
        (1006, REPORT_DASHBOARD, 'report_dashboard', ugettext_lazy("Reporting layer: Dashboard")),
        (1007, REPORT_EVENT, 'report_event', ugettext_lazy("Reporting layer: Event")),
        (1008, REPORT_BOOKMARK, 'report_bookmark', ugettext_lazy("Reporting layer: Bookmark")),
        (1009, REPORT_INSTRUMENT_AUDIT, 'report_instrument_audit', ugettext_lazy("Reporting layer: Instrument Audit")),
        (1010, REPORT_TRANSACTION_AUDIT, 'report_transaction_audit',
         ugettext_lazy("Reporting layer: Transaction Audit")),
        (1011, REPORT_BASE_TRANSACTION, 'report_base_transaction', ugettext_lazy("Reporting layer: Base Transaction")),
        (1012, REPORT_ACTIVITY_LOG, 'report_activity_log', ugettext_lazy("Reporting layer: Activity Log")),
        (1013, REPORT_FORUM, 'report_forum', ugettext_lazy("Reporting layer: Forum")),

        (2001, CONFIGURATION_ACCOUNT_TYPE, 'configuration_account_type',
         ugettext_lazy("Configurations layer: Account Type")),
        (2002, CONFIGURATION_INSTRUMENT_TYPE, 'configuration_instrument_type',
         ugettext_lazy("Configurations layer: Instrument Type")),
        (2003, CONFIGURATION_TRANSACTION_TYPE, 'configuration_transaction_type',
         ugettext_lazy("Configurations layer: Transaction Type")),
        (2004, CONFIGURATION_PRICING_POLICY, 'configuration_pricing_policy',
         ugettext_lazy("Configurations layer: Pricing Policy")),
        (2005, CONFIGURATION_PRICE_DOWNLOAD_SCHEME, 'configuration_price_download_scheme',
         ugettext_lazy("Configurations layer: Price Download Scheme")),
        (2006, CONFIGURATION_INSTRUMENT_DOWNLOAD_SCHEME, 'configuration_instrument_download_scheme',
         ugettext_lazy("Configurations layer: Instrument Download Scheme")),
        (2007, CONFIGURATION_AUTOMATED_PRICE_DOWNLOADS, 'configuration_automated_price_downloads',
         ugettext_lazy("Configurations layer: Automated Price Downloads")),
        (2008, CONFIGURATION_SIMPLE_IMPORT_SCHEME, 'configuration_simple_import_scheme',
         ugettext_lazy("Configurations layer: Simple Import Scheme")),
        (2009, CONFIGURATION_TRANSACTION_IMPORT_SCHEME, 'configuration_transaction_import_scheme',
         ugettext_lazy("Configurations layer: Transaction Import Scheme")),
        (2010, CONFIGURATION_COMPLEX_IMPORT_SCHEME, 'configuration_complex_import_scheme',
         ugettext_lazy("Configurations layer: Complex Import Scheme")),
        (2011, CONFIGURATION_MAPPING_TABLES, 'configuration_mapping_tables',
         ugettext_lazy("Configurations layer: Mapping Tables")),
        (2012, CONFIGURATION_USER_ATTRIBUTES, 'configuration_user_attributes',
         ugettext_lazy("Configurations layer: User Attributes")),
        (2013, CONFIGURATION_ALIASES, 'configuration_aliases',
         ugettext_lazy("Configurations layer: Aliases")),

        (2014, CONFIGURATION_TEMPLATES, 'configuration_template',
         ugettext_lazy("Configurations layer: Templates")),

        (2015, CONFIGURATION_REFERENCE_TABLE, 'configuration_reference_table',
         ugettext_lazy("Configurations layer: Reference Tables")),

        (3001, SETTINGS_NOTIFICATION, 'settings_notification', ugettext_lazy("Settings layer: Notification")),
        (3002, SETTINGS_EXPORT_CONFIGURATION, 'settings_export_configuration',
         ugettext_lazy("Settings layer: Export Configuration")),
        (3003, SETTINGS_IMPORT_CONFIGURATION, 'settings_import_configuration',
         ugettext_lazy("Settings layer: Import Configuration")),
        (3004, SETTINGS_EXPORT_MAPPING, 'settings_export_mapping', ugettext_lazy("Settings layer: Export Mapping")),
        (3005, SETTINGS_IMPORT_MAPPING, 'settings_import_mapping', ugettext_lazy("Settings layer: Import Mapping")),
        (3006, SETTINGS_PROVIDER, 'settings_provider', ugettext_lazy("Settings layer: Provider")),
        (3007, SETTINGS_INIT_CONFIGURATION, 'settings_init_configuration',
         ugettext_lazy("Settings layer: Init Configuration")),
        (3008, SETTINGS_USERS_GROUPS_PERMISSION, 'settings_users_groups_permission',
         ugettext_lazy("Settings layer: Users & Groups Permission")),
        (3009, SETTINGS_NEW_OBJECTS_PERMISSION, 'settings_new_objects_permission',
         ugettext_lazy("Settings layer: New Objects Permission")),
        (3010, SETTINGS_TIMEZONE, 'settings_timezone', ugettext_lazy("Settings layer: Timezone")),
        (3011, SETTINGS_ECOSYSTEM_DEFAULT, 'settings_ecosystem_default',
         ugettext_lazy("Settings layer: Ecosystem Default")),

        (4001, ACCOUNT_SETTINGS, 'account_settings', ugettext_lazy("Account layer: Settings")),
        (4002, ACCOUNT_PERSONAL_DATA, 'account_personal_data', ugettext_lazy("Account layer: Personal Data")),
        (4003, ACCOUNT_ECOSYSTEM_MANAGEMENT, 'account_ecosystem_management',
         ugettext_lazy("Account layer: Ecosystem Management")),
    )

    value = models.PositiveSmallIntegerField(default=1, verbose_name=ugettext_lazy('value'))

    class Meta(AbstractClassModel.Meta):
        verbose_name = ugettext_lazy('portal interface access')
        verbose_name_plural = ugettext_lazy('portal interface accesses')


class EntityTooltip(models.Model):
    master_user = models.ForeignKey(MasterUser,
                                    verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE)

    content_type = models.ForeignKey(ContentType, verbose_name=ugettext_lazy('content type'), on_delete=models.CASCADE)

    name = models.CharField(max_length=255, default='', blank=True, verbose_name=ugettext_lazy('name'))
    key = models.CharField(max_length=255, default='', blank=True, verbose_name=ugettext_lazy('key'))
    text = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('text'))

    class Meta:
        unique_together = [
            ['master_user', 'content_type', 'key'],
        ]


class ColorPalette(NamedModel):
    master_user = models.ForeignKey(MasterUser, verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE)
    name = models.CharField(max_length=255, default='', blank=True, verbose_name=ugettext_lazy('name'))
    is_default = models.BooleanField(default=False, verbose_name=ugettext_lazy('is default'))

    def save(self, *args, **kwargs):

        if self.is_default:
            qs = ColorPalette.objects.filter(master_user=self.master_user, is_default=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            qs.update(is_default=False)
        return super(ColorPalette, self).save(*args, **kwargs)


class ColorPaletteColor(models.Model):
    color_palette = models.ForeignKey(ColorPalette,  related_name='colors', verbose_name=ugettext_lazy('color palette'), on_delete=models.CASCADE)

    order = models.IntegerField(default=0, verbose_name=ugettext_lazy('order'))

    name = models.CharField(max_length=255, default='', blank=True, verbose_name=ugettext_lazy('name'))
    value = models.CharField(max_length=255, default='', blank=True, verbose_name=ugettext_lazy('value'))
    tooltip = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('tooltip'))

    class Meta:
        unique_together = [
            ['color_palette', 'order'],
        ]


class TransactionUserFieldModel(models.Model):
    master_user = models.ForeignKey(MasterUser, related_name='transaction_user_fields',
                                    verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE)

    key = models.CharField(max_length=255, default='', blank=True, verbose_name=ugettext_lazy('key'))
    name = models.CharField(max_length=255, default='', blank=True, verbose_name=ugettext_lazy('name'))


class InstrumentUserFieldModel(models.Model):
    master_user = models.ForeignKey(MasterUser, related_name='instrument_user_fields',
                                    verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE)

    key = models.CharField(max_length=255, default='', blank=True, verbose_name=ugettext_lazy('key'))
    name = models.CharField(max_length=255, default='', blank=True, verbose_name=ugettext_lazy('name'))


class BaseUIModel(models.Model):
    json_data = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('json data'))

    origin_for_global_layout = models.ForeignKey(SharedConfigurationFile,
                                                 related_name="%(class)s_origins",
                                                 on_delete=models.SET_NULL, null=True, blank=True,
                                                 verbose_name=ugettext_lazy('origin for global layout'))

    sourced_from_global_layout = models.ForeignKey(SharedConfigurationFile, on_delete=models.SET_NULL, null=True,
                                                   blank=True,
                                                   related_name="%(class)s_subscribers",
                                                   verbose_name=ugettext_lazy('sourced for global layout'))

    class Meta:
        abstract = True

    @property
    def data(self):
        if self.json_data:
            try:
                return json.loads(self.json_data)
            except (ValueError, TypeError):
                return None
        else:
            return None

    @data.setter
    def data(self, val):
        if val:
            self.json_data = json.dumps(val, cls=DjangoJSONEncoder, sort_keys=True)
        else:
            self.json_data = None


class TemplateLayout(BaseUIModel):
    member = models.ForeignKey(Member, related_name='template_layouts',
                               verbose_name=ugettext_lazy('member'), on_delete=models.CASCADE)
    type = models.CharField(max_length=255, blank=True, default="", db_index=True, verbose_name=ugettext_lazy('type'))
    name = models.CharField(max_length=255, blank=True, default="", db_index=True, verbose_name=ugettext_lazy('name'))
    user_code = models.CharField(max_length=25, null=True, blank=True, verbose_name=ugettext_lazy('user code'))
    is_default = models.BooleanField(default=False, verbose_name=ugettext_lazy('is default'))

    class Meta(BaseUIModel.Meta):
        unique_together = [
            ['member', 'type', 'name'],
        ]
        ordering = ['name']

    def save(self, *args, **kwargs):

        if not self.user_code:
            self.user_code = Truncator(self.name).chars(25, truncate='')

        if self.is_default:
            qs = TemplateLayout.objects.filter(master_user=self.member, type=self.type,
                                               is_default=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            qs.update(is_default=False)
        return super(TemplateLayout, self).save(*args, **kwargs)


class ContextMenuLayout(BaseUIModel):
    member = models.ForeignKey(Member, related_name='context_menu_layouts', verbose_name=ugettext_lazy('member'),
                               on_delete=models.CASCADE)
    name = models.CharField(max_length=255, blank=True, default="", db_index=True, verbose_name=ugettext_lazy('name'))
    user_code = models.CharField(max_length=25, null=True, blank=True, verbose_name=ugettext_lazy('user code'))
    type = models.CharField(max_length=255, blank=True, default="", db_index=True, verbose_name=ugettext_lazy('type'))

    class Meta(BaseUIModel.Meta):
        unique_together = [
            ['member', 'type', 'user_code'],
        ]
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.user_code:
            self.user_code = Truncator(self.name).chars(25, truncate='')

        super(ContextMenuLayout, self).save(*args, **kwargs)


class BaseLayout(BaseUIModel):
    content_type = models.ForeignKey(ContentType, verbose_name=ugettext_lazy('content type'), on_delete=models.CASCADE)

    class Meta:
        abstract = True


class ListLayout(BaseLayout):
    member = models.ForeignKey(Member, related_name='template_list_layouts', verbose_name=ugettext_lazy('member'),
                               on_delete=models.CASCADE)
    name = models.CharField(max_length=255, blank=True, default="", db_index=True, verbose_name=ugettext_lazy('name'))
    user_code = models.CharField(max_length=25, null=True, blank=True, verbose_name=ugettext_lazy('user code'))
    is_default = models.BooleanField(default=False, verbose_name=ugettext_lazy('is default'))
    is_active = models.BooleanField(default=False, verbose_name=ugettext_lazy('is active'))

    is_fixed = models.BooleanField(default=False, verbose_name=ugettext_lazy('is fixeds'))

    class Meta(BaseLayout.Meta):
        unique_together = [
            ['member', 'content_type', 'user_code'],
        ]
        ordering = ['name']

    def save(self, *args, **kwargs):

        is_fixed = True

        if not self.user_code:
            self.user_code = Truncator(self.name).chars(25, truncate='')

        if self.is_default:
            qs = ListLayout.objects.filter(member=self.member, content_type=self.content_type, is_default=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            qs.update(is_default=False)

            qs = ListLayout.objects.filter(member=self.member, content_type=self.content_type, is_active=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            qs.update(is_active=False)

        return super(ListLayout, self).save(*args, **kwargs)

    def __str__(self):
        return self.name


class DashboardLayout(BaseUIModel):
    member = models.ForeignKey(Member, related_name='dashboard_layouts', verbose_name=ugettext_lazy('member'),
                               on_delete=models.CASCADE)
    name = models.CharField(max_length=255, blank=True, default="", db_index=True, verbose_name=ugettext_lazy('name'))
    user_code = models.CharField(max_length=25, null=True, blank=True, verbose_name=ugettext_lazy('user code'))
    is_default = models.BooleanField(default=False, verbose_name=ugettext_lazy('is default'))
    is_active = models.BooleanField(default=False, verbose_name=ugettext_lazy('is active'))

    class Meta(BaseLayout.Meta):
        unique_together = [
            ['member', 'user_code'],
        ]
        ordering = ['name']

    def save(self, *args, **kwargs):

        if not self.user_code:
            self.user_code = Truncator(self.name).chars(25, truncate='')

        if self.is_default:
            qs = DashboardLayout.objects.filter(member=self.member, is_default=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            qs.update(is_default=False)

            qs = DashboardLayout.objects.filter(member=self.member, is_active=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            qs.update(is_active=False)

        return super(DashboardLayout, self).save(*args, **kwargs)

    def __str__(self):
        return self.name


class ConfigurationExportLayout(BaseUIModel):
    member = models.ForeignKey(Member, related_name='configuration_export_layouts',
                               verbose_name=ugettext_lazy('member'), on_delete=models.CASCADE)
    name = models.CharField(max_length=255, blank=True, default="", db_index=True, verbose_name=ugettext_lazy('name'))
    is_default = models.BooleanField(default=False, verbose_name=ugettext_lazy('is default'))

    class Meta(BaseUIModel.Meta):
        unique_together = [
            ['member', 'name'],
        ]
        ordering = ['name']

    def save(self, *args, **kwargs):
        if self.is_default:
            qs = ConfigurationExportLayout.objects.filter(member=self.member, is_default=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            qs.update(is_default=False)
        return super(ConfigurationExportLayout, self).save(*args, **kwargs)

    def __str__(self):
        return self.name


class EditLayout(BaseLayout):
    member = models.ForeignKey(Member, related_name='edit_layouts', verbose_name=ugettext_lazy('member'),
                               on_delete=models.CASCADE)

    class Meta(BaseLayout.Meta):
        unique_together = [
            ['member', 'content_type'],
        ]
        ordering = ['content_type']


class Bookmark(BaseUIModel, MPTTModel):
    member = models.ForeignKey(Member, related_name='bookmarks', verbose_name=ugettext_lazy('member'),
                               on_delete=models.CASCADE)
    parent = TreeForeignKey('self', null=True, blank=True, related_name='children', db_index=True,
                            verbose_name=ugettext_lazy('parent'), on_delete=models.CASCADE)
    name = models.CharField(max_length=100, verbose_name=ugettext_lazy('name'))
    uri = models.CharField(max_length=256, null=True, blank=True, verbose_name=ugettext_lazy('uri'))
    list_layout = models.ForeignKey(ListLayout, null=True, blank=True, related_name='bookmarks',
                                    on_delete=models.SET_NULL, verbose_name=ugettext_lazy('list layout'))

    class MPTTMeta:
        order_insertion_by = ['member', 'name']

    class Meta:
        verbose_name = ugettext_lazy('bookmark')
        verbose_name_plural = ugettext_lazy('bookmarks')
        ordering = ['tree_id', 'level', 'name']

    def __str__(self):
        return self.name


class Dashboard(models.Model):
    member = models.ForeignKey(Member, related_name='dashboards', verbose_name=ugettext_lazy('member'),
                               on_delete=models.CASCADE)

    class Meta:
        verbose_name = ugettext_lazy('dashboard')
        verbose_name_plural = ugettext_lazy('dashboard')


class Configuration(BaseUIModel):
    master_user = models.ForeignKey(MasterUser, related_name='configuration_files',
                                    verbose_name=ugettext_lazy('master user'), on_delete=models.CASCADE)
    name = models.CharField(max_length=255, blank=True, default="", db_index=True, verbose_name=ugettext_lazy('name'))
    description = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('description'))

    class Meta(BaseLayout.Meta):
        unique_together = [
            ['master_user', 'name'],
        ]

    ordering = ['name']
