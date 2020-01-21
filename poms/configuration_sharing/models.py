import json

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy

from poms.users.models import MasterUser, Member

from django.conf import settings


class SharedConfigurationFile(models.Model):
    name = models.CharField(max_length=255)

    PUBLIC = 1
    MASTER_USER_ONLY = 2
    PUBLICITY_TYPE_CHOICES = (
        (PUBLIC, ugettext_lazy('Public')),
        (MASTER_USER_ONLY, ugettext_lazy('Master User Only')),
    )

    json_data = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('json data'))

    notes = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes'))

    publicity_type = models.PositiveSmallIntegerField(default=PUBLIC, choices=PUBLICITY_TYPE_CHOICES, db_index=True,
                                                      verbose_name=ugettext_lazy('publicity type'))

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                               verbose_name=ugettext_lazy('user'))

    linked_master_user = models.ForeignKey(MasterUser, null=True, blank=True,
                                           verbose_name=ugettext_lazy('linked master user'), on_delete=models.CASCADE)

    def __str__(self):
        return str(self.name)

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


class InviteToSharedConfigurationFile(models.Model):

    SENT = 0
    ACCEPTED = 1
    DECLINED = 2

    STATUS_CHOICES = ((SENT, 'Sent'),
                      (ACCEPTED, 'Accepted'),
                      (DECLINED, 'Declined'),
                      )

    member_from = models.ForeignKey(Member, related_name="my_invites_to_shared_configuration_files", verbose_name=ugettext_lazy('member from'), on_delete=models.CASCADE)
    member_to = models.ForeignKey(Member, related_name="invites_to_shared_configuration_files_to", verbose_name=ugettext_lazy('member to'), on_delete=models.CASCADE)
    shared_configuration_file = models.ForeignKey(SharedConfigurationFile,
                                                  verbose_name=ugettext_lazy('shared configuration file'),
                                                  on_delete=models.CASCADE)
    notes = models.TextField(blank=True, default='', verbose_name=ugettext_lazy('notes'))

    status = models.IntegerField(default=SENT, choices=STATUS_CHOICES)
