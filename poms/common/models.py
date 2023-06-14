from __future__ import unicode_literals

from django.core.cache import cache
from django.db import models
from django.utils.translation import gettext_lazy

from poms.expressions_engine import formula
from poms.common.middleware import get_request

EXPRESSION_FIELD_LENGTH = 4096


class OwnerModel(models.Model):
    owner = models.ForeignKey('users.Member', verbose_name=gettext_lazy('owner'),
                              on_delete=models.CASCADE)

    class Meta:
        abstract = True


class NamedModel(models.Model):
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

    is_enabled = models.BooleanField(default=True, db_index=True, verbose_name=gettext_lazy('is enabled'))

    class Meta:
        abstract = True
        unique_together = [
            ['master_user', 'user_code']
        ]
        ordering = ['user_code']

    def __str__(self):
        return self.user_code or ''

    def save(self, *args, **kwargs):

        cache.clear()

        if not self.user_code:
            # self.user_code = Truncator(self.name).chars(25, truncate='')
            self.user_code = self.name
        if not self.short_name:
            self.short_name = self.name
            # self.short_name = Truncator(self.name).chars(50)
        super(NamedModel, self).save(*args, **kwargs)


class DataTimeStampedModel(models.Model):
    created = models.DateTimeField(auto_now_add=True, editable=False, null=True, db_index=True,
                                   verbose_name=gettext_lazy('created'))
    modified = models.DateTimeField(auto_now=True, editable=False, db_index=True,
                                    verbose_name=gettext_lazy('modified'))

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    created = models.DateTimeField(auto_now_add=True, editable=False, db_index=True,
                                   verbose_name=gettext_lazy('created'))
    modified = models.DateTimeField(auto_now=True, editable=False, db_index=True,
                                    verbose_name=gettext_lazy('modified'))

    class Meta:
        abstract = True
        get_latest_by = 'modified'
        ordering = ['created', ]


class AbstractClassModel(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, verbose_name=gettext_lazy('ID'))
    user_code = models.CharField(max_length=255, unique=True, verbose_name=gettext_lazy('user code'))
    name = models.CharField(max_length=255, blank=True, default='', verbose_name=gettext_lazy('name'))
    short_name = models.CharField(max_length=255, blank=True, default='', verbose_name=gettext_lazy('short name'))
    description = models.TextField(blank=True, default='', verbose_name=gettext_lazy('description'))

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
    is_deleted = models.BooleanField(default=False, db_index=True,
                                     verbose_name=gettext_lazy('is deleted'),
                                     help_text="Mark object as deleted. Does not actually delete the object.")
    deleted_user_code = models.CharField(max_length=255, null=True, blank=True,
                                         verbose_name=gettext_lazy('deleted user code'),
                                         help_text="Stores original user_code of object. Deleted objects has null user_code which makes it available again.")

    class Meta:
        abstract = True
        index_together = [
            ['master_user', 'is_deleted']
        ]

    def fake_delete(self):

        from poms.system_messages.handlers import send_system_message

        self.is_deleted = True

        fields_to_update = ['is_deleted', 'modified']
        try:
            member = get_request().user.member
        except Exception as e:
            from poms.common.celery import get_active_celery_task_id
            from poms.celery_tasks.models import CeleryTask

            celery_task_id = get_active_celery_task_id()

            celery_task = CeleryTask.objects.get(celery_task_id=celery_task_id)
            member = celery_task.member

        if hasattr(self, 'user_code'):
            self.deleted_user_code = self.user_code
            self.user_code = formula.safe_eval('generate_user_code("del", "", 0)',
                                               context={'master_user': self.master_user})

            self.name = '(del) ' + self.name
            self.short_name = '(del) ' + self.short_name

            fields_to_update.append('user_code')
            fields_to_update.append('name')
            fields_to_update.append('short_name')
            fields_to_update.append('deleted_user_code')

        if hasattr(self, 'is_enabled'):
            self.is_enabled = False
            fields_to_update.append('is_enabled')

        if hasattr(self, 'is_active'):  # instrument prop
            self.is_active = False
            fields_to_update.append('is_active')

        entity_name = self._meta.model_name

        send_system_message(master_user=self.master_user,
                            performed_by=member.username,
                            section='data',
                            type='warning',
                            title='Delete ' + entity_name + ' (manual)',
                            description=entity_name + ' was deleted (manual) - ' + self.name,
                            )

        self.save(update_fields=fields_to_update)


# These models need to create custom context, that could be passed to serializers
class ProxyUser(object):

    def __init__(self, member, master_user):
        self.member = member
        self.master_user = master_user


class ProxyRequest(object):

    def __init__(self, user):
        self.user = user
