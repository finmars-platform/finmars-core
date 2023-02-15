import json
from django.contrib.contenttypes.models import ContentType

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils.translation import gettext_lazy

from poms.users.models import MasterUser, Member


class HistoricalRecord(models.Model):
    '''
    2023.01 Feature
    It listen changes of models and store JSON output after save
    In Finmars Web interface users can check history of changes for specific entity e.g. Instrument, Complex Transaction
    TODO: probably need to store only diff with change, not the whole JSON output
    '''
    master_user = models.ForeignKey(MasterUser, verbose_name=gettext_lazy('master user'), on_delete=models.CASCADE)
    member = models.ForeignKey(Member, null=True, blank=True, verbose_name=gettext_lazy('member'),
                               on_delete=models.SET_NULL)

    user_code = models.CharField(max_length=255, null=True, blank=True, verbose_name=gettext_lazy('user code'))
    content_type = models.ForeignKey(ContentType, verbose_name=gettext_lazy('content type'), on_delete=models.CASCADE)

    notes = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('notes'))

    created = models.DateTimeField(auto_now_add=True, editable=False, null=True, db_index=True,
                                   verbose_name=gettext_lazy('created'))

    json_data = models.TextField(null=True, blank=True, verbose_name=gettext_lazy('json data'))

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

    def __str__(self):
        return self.member.username + ' changed ' + self.user_code + ' (' + str(self.content_type) + ') at ' + str(self.created.strftime("%Y-%m-%d, %H:%M:%S"))

    class Meta:
        verbose_name = gettext_lazy('history record')
        verbose_name_plural = gettext_lazy('history records')
        index_together = [
            ['user_code', 'content_type']
        ]
        ordering = ['-created']