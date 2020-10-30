from django.db import models
from django.utils.translation import ugettext_lazy


class SystemMessage(models.Model):

    LEVEL_INFO = 1
    LEVEL_WARNING = 2
    LEVEL_ERROR = 3

    LEVELS_CHOICES = (
        (LEVEL_INFO, ugettext_lazy('Info')),
        (LEVEL_WARNING, ugettext_lazy('Warning')),
        (LEVEL_ERROR, ugettext_lazy('Error')),
    )

    STATUS_NEW = 1
    STATUS_SOLVED = 2
    STATUS_VIEWED = 3
    STATUS_MARKED = 4
    STATUS_ABANDONED = 5

    STATUS_CHOICES = (
        (LEVEL_INFO, ugettext_lazy('New')),
        (STATUS_SOLVED, ugettext_lazy('Solved')),
        (STATUS_VIEWED, ugettext_lazy('Viewed')),
        (STATUS_MARKED, ugettext_lazy('Marked')),
        (STATUS_ABANDONED, ugettext_lazy('Abandoned')),
    )

    master_user = models.ForeignKey('users.MasterUser', verbose_name=ugettext_lazy('master user') , on_delete=models.CASCADE)

    level = models.PositiveSmallIntegerField(default=LEVEL_INFO, choices=LEVELS_CHOICES,
                                             verbose_name=ugettext_lazy('level'))
    status = models.PositiveSmallIntegerField(default=STATUS_NEW, choices=STATUS_CHOICES,
                                              verbose_name=ugettext_lazy('status'))
    text = models.TextField(null=True, blank=True, verbose_name=ugettext_lazy('text'))

    created = models.DateTimeField(auto_now_add=True, editable=False, db_index=True,
                                   verbose_name=ugettext_lazy('created'))

    source = models.CharField(max_length=255, null=True, blank=True, verbose_name=ugettext_lazy('source'))

    # TODO attachments
    # TODO channels
    # TODO actions
