import logging

from django.apps import AppConfig

_l = logging.getLogger('poms.explorer')


class ExplorerConfig(AppConfig):
    name = 'poms.explorer'
