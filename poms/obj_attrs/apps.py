from __future__ import unicode_literals

from django.apps import AppConfig
from django.utils.translation import gettext_lazy


class ObjAttrsConfig(AppConfig):
    name = "poms.obj_attrs"
    verbose_name = gettext_lazy("Attributes")
