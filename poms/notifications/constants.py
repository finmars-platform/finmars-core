from django.contrib import messages
from django.utils.translation import gettext_lazy

DEBUG = messages.DEBUG
INFO = messages.INFO
SUCCESS = messages.SUCCESS
WARNING = messages.WARNING
ERROR = messages.ERROR

LEVELS = (
    (DEBUG, gettext_lazy("debug")),
    (INFO, gettext_lazy("info")),
    (SUCCESS, gettext_lazy("success")),
    (WARNING, gettext_lazy("warning")),
    (ERROR, gettext_lazy("error")),
)
