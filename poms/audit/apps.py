from __future__ import unicode_literals

from django.apps import AppConfig
from django.utils.translation import gettext_lazy


class AuditConfig(AppConfig):
    name = 'poms.audit'
    # label = 'poms_audit'
    verbose_name = gettext_lazy('Audit')

    def ready(self):
        # noinspection PyUnresolvedReferences
        import poms.audit.handlers
        # noinspection PyUnresolvedReferences
        import poms.audit.history
