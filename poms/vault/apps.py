import logging

from django.apps import AppConfig

_l = logging.getLogger("poms.vault")


class VaultConfig(AppConfig):
    name = "poms.vault"
