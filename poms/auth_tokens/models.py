from __future__ import unicode_literals

import binascii
import os

import pytz
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy
from django.utils import timezone

from poms.common.models import NamedModel
from poms.users.models import MasterUser, Member

LANGUAGE_MAX_LENGTH = 5
TIMEZONE_MAX_LENGTH = 20
TIMEZONE_CHOICES = sorted(list((k, k) for k in pytz.all_timezones))
TIMEZONE_COMMON_CHOICES = sorted(list((k, k) for k in pytz.common_timezones))

import logging

_l = logging.getLogger('poms.auth_tokens')


class AuthToken(models.Model):
    '''
        Probably Deprecated
        Since Keycloak integration now in no use

    '''
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


class AccessLevel(models.TextChoices):
    READ = 'read', 'Read Only'
    WRITE = 'write', 'Write Access'
    ADMIN = 'admin', 'Admin Access'


class PersonalAccessToken(NamedModel):
    master_user = models.ForeignKey(MasterUser, null=True, blank=True, verbose_name=gettext_lazy('master user'),
                      on_delete=models.CASCADE)
    member = models.ForeignKey(Member, null=True, blank=True, verbose_name=gettext_lazy('member'),
                      related_name='personal_access_tokens',
                      on_delete=models.SET_NULL)

    token = models.TextField()  # Storing the token; consider encrypting this field in production
    access_level = models.CharField(max_length=10, choices=AccessLevel.choices, default=AccessLevel.READ)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Token for {self.member.username} (Expires: {self.expires_at})"


class FinmarsRefreshToken:
    def __init__(self, jwt_token):
        self.access_token = jwt_token
