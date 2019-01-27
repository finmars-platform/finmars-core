import json

from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.translation import ugettext_lazy
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel

from poms.users.models import MasterUser, Member


class BaseUIModel(models.Model):
    json_data = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('json data'))

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


class BaseLayout(BaseUIModel):
    content_type = models.ForeignKey(ContentType, verbose_name=ugettext_lazy('content type'))

    class Meta:
        abstract = True


class TemplateListLayout(BaseLayout):
    master_user = models.ForeignKey(MasterUser, related_name='template_list_layouts',
                                    verbose_name=ugettext_lazy('master user'))
    name = models.CharField(max_length=255, blank=True, default="", db_index=True, verbose_name=ugettext_lazy('name'))
    is_default = models.BooleanField(default=False, verbose_name=ugettext_lazy('is default'))

    class Meta(BaseLayout.Meta):
        unique_together = [
            ['master_user', 'content_type', 'name'],
        ]
        ordering = ['name']

    def save(self, *args, **kwargs):
        if self.is_default:
            qs = TemplateListLayout.objects.filter(master_user=self.master_user, content_type=self.content_type,
                                                   is_default=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            qs.update(is_default=False)
        return super(TemplateListLayout, self).save(*args, **kwargs)


class TemplateEditLayout(BaseLayout):
    master_user = models.ForeignKey(MasterUser, related_name='edit_layouts', verbose_name=ugettext_lazy('master user'))

    class Meta(BaseLayout.Meta):
        unique_together = [
            ['master_user', 'content_type'],
        ]
        ordering = ['content_type']


class ListLayout(BaseLayout):
    member = models.ForeignKey(Member, related_name='template_list_layouts', verbose_name=ugettext_lazy('member'))
    name = models.CharField(max_length=255, blank=True, default="", db_index=True, verbose_name=ugettext_lazy('name'))
    is_default = models.BooleanField(default=False, verbose_name=ugettext_lazy('is default'))

    class Meta(BaseLayout.Meta):
        unique_together = [
            ['member', 'content_type', 'name'],
        ]
        ordering = ['name']

    def save(self, *args, **kwargs):
        if self.is_default:
            qs = ListLayout.objects.filter(member=self.member, content_type=self.content_type, is_default=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            qs.update(is_default=False)
        return super(ListLayout, self).save(*args, **kwargs)

    def __str__(self):
        return self.name


class ConfigurationExportLayout(BaseUIModel):
    member = models.ForeignKey(Member, related_name='configuration_export_layouts', verbose_name=ugettext_lazy('member'))
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
    member = models.ForeignKey(Member, related_name='edit_layouts', verbose_name=ugettext_lazy('member'))

    class Meta(BaseLayout.Meta):
        unique_together = [
            ['member', 'content_type'],
        ]
        ordering = ['content_type']


class Bookmark(BaseUIModel, MPTTModel):
    member = models.ForeignKey(Member, related_name='bookmarks', verbose_name=ugettext_lazy('member'))
    parent = TreeForeignKey('self', null=True, blank=True, related_name='children', db_index=True,
                            verbose_name=ugettext_lazy('parent'))
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
    member = models.ForeignKey(Member, related_name='dashboards', verbose_name=ugettext_lazy('member'))

    class Meta:
        verbose_name = ugettext_lazy('dashboard')
        verbose_name_plural = ugettext_lazy('dashboard')


class Configuration(BaseUIModel):
    master_user = models.ForeignKey(MasterUser, related_name='configuration_files',
                                    verbose_name=ugettext_lazy('master user'))
    name = models.CharField(max_length=255, blank=True, default="", db_index=True, verbose_name=ugettext_lazy('name'))
    description = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('description'))

    class Meta(BaseLayout.Meta):
        unique_together = [
            ['master_user', 'name'],
        ]
    ordering = ['name']