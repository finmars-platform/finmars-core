from __future__ import unicode_literals

import binascii
import os

import pytz
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy

from poms.users.models import MasterUser, Member

LANGUAGE_MAX_LENGTH = 5
TIMEZONE_MAX_LENGTH = 20
TIMEZONE_CHOICES = sorted(list((k, k) for k in pytz.all_timezones))
TIMEZONE_COMMON_CHOICES = sorted(list((k, k) for k in pytz.common_timezones))

import logging

_l = logging.getLogger('poms.auth_tokens')


class AuthToken(models.Model):
    key = models.CharField("Key", max_length=40, db_index=True, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="authentication_token",
        on_delete=models.CASCADE,
        verbose_name="User",
    )

    current_master_user = models.ForeignKey(MasterUser, null=True, blank=True, verbose_name=gettext_lazy('master user'),
                                            on_delete=models.SET_NULL)
    current_member = models.ForeignKey(Member, null=True, blank=True, verbose_name=gettext_lazy('member'),
                                       on_delete=models.SET_NULL)

    created = models.DateTimeField("Created", auto_now_add=True)

    class Meta:
        verbose_name = "Token"
        verbose_name_plural = "Tokens"

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_key()
        return super(AuthToken, self).save(*args, **kwargs)

    def generate_key(self):
        return binascii.hexlify(os.urandom(20)).decode()
