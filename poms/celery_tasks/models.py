from django.db import models
from django.utils.translation import ugettext_lazy

import json
from django.core.serializers.json import DjangoJSONEncoder


class CeleryTask(models.Model):
    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user'))
    member = models.ForeignKey('users.Member', verbose_name=ugettext_lazy('member'), null=True, blank=True)

    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)

    is_system_task = models.BooleanField(default=False, verbose_name=ugettext_lazy("is system task"))

    task_id = models.CharField('task_id', max_length=255, unique=True)
    task_status = models.CharField('task_status', max_length=50, blank=True, null=True)
    task_type = models.CharField('task_type', max_length=50, blank=True, null=True)

    json_data = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('json data'))

    class Meta:
        unique_together = (
            ('master_user', 'task_id')
        )

    def __str__(self):
        return 'Master_user {0.master_user.id} <Task: {0.task_id} ({0.task_status})>'.format(self)

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
