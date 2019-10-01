from __future__ import unicode_literals

from django.db import models
from django.utils.text import Truncator
from django.utils.translation import ugettext_lazy

from poms.common import formula

EXPRESSION_FIELD_LENGTH = 1024


class NamedModel(models.Model):
    user_code = models.CharField(max_length=25, null=True, blank=True, verbose_name=ugettext_lazy('user code'))
    name = models.CharField(max_length=255, verbose_name=ugettext_lazy('name'))
    short_name = models.CharField(max_length=50, null=True, blank=True, verbose_name=ugettext_lazy('short name'))
    public_name = models.CharField(max_length=255, null=True, blank=True, verbose_name=ugettext_lazy('public name'),
                                   help_text=ugettext_lazy('used if user does not have permissions to view object'))
    notes = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('notes'))

    is_enabled = models.BooleanField(default=False, db_index=True, verbose_name=ugettext_lazy('is enabled'))

    class Meta:
        abstract = True
        unique_together = [
            ['master_user', 'user_code']
        ]
        ordering = ['user_code']

    def __str__(self):
        return self.user_code or ''

    def save(self, *args, **kwargs):
        if not self.user_code:
            self.user_code = Truncator(self.name).chars(25, truncate='')
        if not self.short_name:
            self.short_name = Truncator(self.name).chars(50)
        super(NamedModel, self).save(*args, **kwargs)


class TimeStampedModel(models.Model):
    created = models.DateTimeField(auto_now_add=True, editable=False, db_index=True,
                                   verbose_name=ugettext_lazy('created'))
    modified = models.DateTimeField(auto_now=True, editable=False, db_index=True,
                                    verbose_name=ugettext_lazy('modified'))

    class Meta:
        abstract = True
        get_latest_by = 'modified'
        ordering = ['created', ]


class AbstractClassModel(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, verbose_name=ugettext_lazy('ID'))
    system_code = models.CharField(max_length=255, unique=True, verbose_name=ugettext_lazy('system code'))
    name = models.CharField(max_length=255, blank=True, default='', verbose_name=ugettext_lazy('name'))
    description = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('description'))

    class Meta:
        abstract = True
        ordering = ['name']

    def __str__(self):
        return self.name

    @classmethod
    def get_by_id(cls, pk):
        attr = '_poms_cache_%s' % pk
        try:
            return getattr(cls, attr)
        except AttributeError:
            val = cls.objects.get(pk=pk)
            setattr(cls, attr, val)
            return val


class FakeDeletableModel(models.Model):
    is_deleted = models.BooleanField(default=False, db_index=True, verbose_name=ugettext_lazy('is deleted'))
    deleted_user_code =  models.CharField(max_length=25, null=True, blank=True, verbose_name=ugettext_lazy('deleted user code'))

    class Meta:
        abstract = True
        index_together = [
            ['master_user', 'is_deleted']
        ]

    def fake_delete(self):

        self.is_deleted = True

        fields_to_update = ['is_deleted']

        if hasattr(self, 'user_code'):
            self.deleted_user_code = self.user_code
            self.user_code = formula.safe_eval('generate_user_code("del", "", 0)', context={'master_user': self.master_user})

            fields_to_update.append('user_code')
            fields_to_update.append('deleted_user_code')

        if hasattr(self, 'is_enabled'):
            self.is_enabled = False
            fields_to_update.append('is_enabled')

        if hasattr(self, 'is_active'):  # instrument prop
            self.is_active = False
            fields_to_update.append('is_active')

        self.save(update_fields=fields_to_update)
